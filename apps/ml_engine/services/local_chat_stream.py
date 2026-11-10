"""Bounded transient page chat; final answers still pass the existing hybrid guards."""
from http.client import HTTPConnection, HTTPException
import json
import re
from queue import Queue, Empty, Full
import socket
from threading import BoundedSemaphore, Event, Lock, Thread
import time
from unicodedata import category

from django.db import close_old_connections

from .local_embeddings import EmbeddingUnavailable

_slots = BoundedSemaphore(2)
_NUMBER_WORDS = re.compile(r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|lakh|crore)\b',re.I)


class GenerationCancelled(RuntimeError):
    pass


class GenerationIncomplete(EmbeddingUnavailable):
    pass


class GenerationTimedOut(GenerationIncomplete):
    pass


class GenerationLimitReached(GenerationIncomplete):
    pass


class LocalChatStream:
    def __init__(self, run, error, check_session):
        self.deadline = time.monotonic()+30
        self.cancelled = Event()
        self.queue = Queue(maxsize=8)
        self.lock = Lock()
        self.connection = None
        self.allow_preview = True
        self.run, self.error, self.check_session = run, error, check_session

    def check(self):
        if self.cancelled.is_set(): raise GenerationCancelled('Local generation cancelled.')
        if time.monotonic() >= self.deadline: raise GenerationTimedOut('Local generation deadline exceeded.')

    def attach(self, connection):
        with self.lock:
            self.check()
            self.connection = connection

    def detach(self, connection):
        with self.lock:
            if self.connection is connection: self.connection = None

    def close(self):
        with self.lock:
            self.cancelled.set()
            if self.connection is not None:
                if self.connection.sock is not None:
                    try: self.connection.sock.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                self.connection.close()
                self.connection = None

    def offer(self, event):
        while True:
            self.check()
            try:
                self.queue.put(event,timeout=.1)
                return
            except Full: pass

    def start(self):
        if not _slots.acquire(blocking=False): return False
        def work():
            close_old_connections()
            try:
                self.check()
                result = self.run(self)
                self.check()
                self.offer(dict(type='final',result=result))
            except GenerationCancelled:
                pass
            except Exception as exc:
                if not self.cancelled.is_set():
                    try: self.offer(dict(type='error',**self.error(exc)))
                    except (GenerationCancelled, GenerationIncomplete): pass
            finally:
                close_old_connections()
                _slots.release()
        self.worker = Thread(target=work,name='alfred-local-chat-stream',daemon=True)
        try: self.worker.start()
        except BaseException:
            _slots.release()
            raise
        return True

    def __iter__(self):
        try:
            yield self.encode(dict(type='started'))
            while True:
                self.check_session()
                self.check()
                try: event = self.queue.get(timeout=.2)
                except Empty: event = dict(type='heartbeat')
                yield self.encode(event)
                if event['type'] in ('final','error'): return
        except Exception as exc:
            if not self.cancelled.is_set(): yield self.encode(dict(type='error',**self.error(exc)))
        finally:
            self.close()

    @staticmethod
    def encode(event):
        return (json.dumps(event,ensure_ascii=False,allow_nan=False)+'\n').encode()

    def chat(self, body, *, deadline):
        """Ollama NDJSON is bounded before any fragment can become a preview."""
        from .hybrid_intelligence import present_answer, FINANCIAL_LANGUAGE, CURRENCY_LANGUAGE
        self.check()
        deadline = min(deadline,self.deadline)
        connection = HTTPConnection('127.0.0.1',11434,timeout=max(.001,deadline-time.monotonic()))
        answer, pending, received, frames, final = '', b'', 0, 0, None
        context = json.loads(body['messages'][1]['content'])
        dialogue = context.get('query','')+' '+' '.join(turn['content'] for turn in context.get('history',[]))
        preview = self.allow_preview and not context.get('sources') and not FINANCIAL_LANGUAGE.search(dialogue)
        try:
            connection.connect()
            connection.auto_open = 0
            self.attach(connection)
            connection.request('POST','/api/chat',body=json.dumps(body|{'stream':True},allow_nan=False).encode(),
                headers={'Content-Type':'application/json','Accept-Encoding':'identity'})
            response = connection.getresponse()
            if (response.status != 200 or response.getheader('Content-Encoding','identity') != 'identity'
                    or response.getheader('Content-Type','').split(';')[0] != 'application/x-ndjson'):
                raise GenerationIncomplete('Invalid local stream response.')
            while True:
                self.check()
                if response.isclosed(): break
                left = deadline-time.monotonic()
                if left <= 0: raise GenerationTimedOut('Local generation deadline exceeded.')
                sock = connection.sock or response.fp.raw._sock
                sock.settimeout(left)
                chunk = response.read1(8192)
                if not chunk: break
                received += len(chunk); pending += chunk
                if received > 256*1024: raise GenerationIncomplete('Local stream exceeds its limit.')
                while b'\n' in pending:
                    raw,pending = pending.split(b'\n',1)
                    frames += 1
                    if not raw or len(raw)>16384 or frames>2048 or final is not None:
                        raise GenerationIncomplete('Invalid local stream frame.')
                    item = json.loads(raw); message = item.get('message',{}) if isinstance(item,dict) else {}
                    if (not isinstance(item,dict) or item.get('model') != body['model'] or type(item.get('done')) is not bool
                            or not isinstance(message,dict) or message.get('role') != 'assistant'
                            or message.get('tool_calls') or not isinstance(message.get('content'),str)):
                        raise GenerationIncomplete('Invalid local stream frame.')
                    text = message['content']; answer += text
                    if len(answer.encode())>8192: raise GenerationIncomplete('Local answer exceeds its limit.')
                    if preview:
                        safe = not any(c.isnumeric() or category(c)=='Sc' for c in answer)
                        safe = safe and not (_NUMBER_WORDS.search(answer) or CURRENCY_LANGUAGE.search(answer))
                        safe = safe and not present_answer(dict(answer=answer),'general')['narrative_withheld']
                        if safe and text: self.offer(dict(type='delta',text=text))
                        elif not safe:
                            preview = False
                            self.offer(dict(type='buffering'))
                    if item['done']:
                        if item.get('done_reason') == 'length':
                            raise GenerationLimitReached('Local answer reached its output limit.')
                        if item.get('done_reason') not in (None,'stop'):
                            raise GenerationIncomplete('Local answer reached its limit before completion.')
                        final = item
                if len(pending)>16384: raise GenerationIncomplete('Local stream frame exceeds its limit.')
            if pending or final is None: raise GenerationIncomplete('Local stream ended before completion.')
            return final|{'message':dict(role='assistant',content=answer)}
        except (OSError,HTTPException,ValueError,KeyError,TypeError,UnicodeError):
            self.check()
            raise GenerationIncomplete('Local stream ended before completion.') from None
        finally:
            self.detach(connection)
            connection.close()
