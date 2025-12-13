from .memory_writer import memory_writer
from .memory_retriever import memory_retriever
from .memory_cleaner import memory_cleaner
from .memory_types import MemoryType


class AlfredMemoryEngine:

    def store_event(self, text, memory_type=MemoryType.CONVERSATION, extra={}):
        return memory_writer.write(text, memory_type, extra)

    def search_memory(self, query):
        return memory_retriever.retrieve(query)

    def cleanup(self):
        return memory_cleaner.prune_low_importance()


alfred_memory = AlfredMemoryEngine()
