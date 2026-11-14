"""Local stdio MCP transport over the read-only registry, with synthetic owners only."""
import io
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.ml_engine.management.commands import alfred_mcp
from apps.ml_engine.services import assistant_tools as tools
from apps.ml_engine.services.hybrid_intelligence import _read_source_context
from apps.mobility.models import TravelPreferenceProfile


def stdio(*messages):
    raw = ''.join((m if isinstance(m, str) else json.dumps(m)) + '\n' for m in messages)
    return io.TextIOWrapper(io.BytesIO(raw.encode()), encoding='utf-8')


class AlfredMcpTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='synthetic-mcp-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-mcp-other')

    def run_server(self, *messages, user='synthetic-mcp-owner'):
        out = io.StringIO()
        with patch('sys.stdin', stdio(*messages)), patch('sys.stdout', out), \
                patch('socket.socket.connect', side_effect=AssertionError('No network')), \
                patch('socket.socket.bind', side_effect=AssertionError('No listener')):
            call_command('alfred_mcp', user=user)
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def call(self, name, arguments=None, request_id=1):
        params = {'name': name} if arguments is None else {'name': name, 'arguments': arguments}
        return alfred_mcp.handle_message(self.owner, dict(jsonrpc='2.0', id=request_id, method='tools/call', params=params))

    def test_handshake_list_and_call_over_stdio_answer_only_requests(self):
        TravelPreferenceProfile.objects.create(user=self.owner, preferences={'terrain': 'mountain'})
        TravelPreferenceProfile.objects.create(user=self.other, preferences={'private': 'SYNTHETIC-OTHER'})
        responses = self.run_server(
            dict(jsonrpc='2.0', id=1, method='initialize', params=dict(protocolVersion='2025-06-18', capabilities={},
                                                                          clientInfo=dict(name='test', version='0'))),
            dict(jsonrpc='2.0', method='notifications/initialized'),
            dict(jsonrpc='2.0', id=2, method='tools/list'),
            dict(jsonrpc='2.0', id=3, method='tools/call', params=dict(name='travel_preferences', arguments={})),
            dict(jsonrpc='2.0', id=4, method='resources/list'),
            dict(jsonrpc='2.0', id=5, method='tools/call', params='bad'),
            'not json',
        )
        self.assertEqual([r['id'] for r in responses], [1, 2, 3, 4, 5, None])
        self.assertEqual(responses[0]['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(responses[0]['result']['capabilities'], {'tools': {}})
        listed = responses[1]['result']['tools']
        self.assertEqual([t['name'] for t in listed], [t['name'].replace('.', '_') for t in tools.tool_catalog()])
        self.assertEqual(listed[1]['inputSchema'], tools.tool_catalog()[1]['input_schema'])
        self.assertTrue(all(t['annotations']['readOnlyHint'] for t in listed))
        result = responses[2]['result']
        self.assertFalse(result['isError'])
        self.assertEqual(json.loads(result['content'][0]['text']), _read_source_context(self.owner, 'travel'))
        self.assertNotIn('SYNTHETIC-OTHER', result['content'][0]['text'])
        self.assertEqual(responses[3]['error']['code'], -32601)
        self.assertEqual(responses[4]['error']['code'], -32600)
        self.assertEqual(responses[5]['error']['code'], -32700)

    def test_unknown_protocol_version_gets_the_newest_supported(self):
        response = alfred_mcp.handle_message(self.owner, dict(jsonrpc='2.0', id=1, method='initialize',
                                                              params=dict(protocolVersion='1999-01-01')))
        self.assertEqual(response['result']['protocolVersion'], alfred_mcp.PROTOCOL_VERSIONS[0])

    def test_unknown_or_write_tools_are_refused_before_any_read(self):
        with patch('apps.ml_engine.services.hybrid_intelligence._read_source_context') as adapter:
            for name in ('run_shell', 'create_savings_goal', 'finance.baseline', ['travel_preferences'], None):
                with self.subTest(name=name):
                    self.assertEqual(self.call(name, {})['error']['code'], -32602)
            self.assertEqual(self.call('travel_preferences', ['x'])['error']['code'], -32602)
            bad_input = self.call('finance_record', {'record_type': 'expense', 'record_id': '1'})['result']
            self.assertTrue(bad_input['isError'])
            adapter.assert_not_called()

    def test_missing_or_inactive_owner_is_refused(self):
        for user in ('synthetic-nobody', ''):
            with self.subTest(user=user), self.assertRaises(CommandError):
                self.run_server(dict(jsonrpc='2.0', id=1, method='tools/list'), user=user)
        self.owner.is_active = False
        self.owner.save(update_fields=['is_active'])
        with self.assertRaises(CommandError):
            self.run_server(dict(jsonrpc='2.0', id=1, method='tools/list'))
        # A server started before deactivation is refused on its next call by the registry's owner check.
        result = self.call('travel_preferences', {})['result']
        self.assertTrue(result['isError'])
        self.assertIn('active owner', result['content'][0]['text'])

    def test_oversized_result_is_refused_by_the_registry_cap(self):
        oversized = [dict(ref='r', classification='c', url='/mobility/', data={'value': 'x' * tools.MAX_RESULT_BYTES})]
        with patch('apps.ml_engine.services.hybrid_intelligence._read_source_context', return_value=oversized):
            result = self.call('travel_preferences', {})['result']
        self.assertTrue(result['isError'])
        self.assertNotIn('xxxx', result['content'][0]['text'])

    def test_unexpected_domain_errors_do_not_leak_details(self):
        with patch('apps.ml_engine.services.hybrid_intelligence._read_source_context',
                   side_effect=RuntimeError('SYNTHETIC-SECRET-PATH')):
            result = self.call('travel_preferences', {})['result']
        self.assertTrue(result['isError'])
        self.assertNotIn('SYNTHETIC', json.dumps(result))
