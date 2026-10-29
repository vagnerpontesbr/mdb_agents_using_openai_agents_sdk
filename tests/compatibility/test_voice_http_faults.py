"""Real loopback HTTP faults with doubled providers; no external requests."""
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import re
import socket
import struct
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from scripts import serve_voice_engine_probe as probe


class DummyClient:
    def __init__(self, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


class VoiceHttpFaultTests(unittest.TestCase):
    @contextmanager
    def server(self, operation):
        ready, saved = threading.Event(), threading.Event()
        instances = []
        original = probe.ThreadingHTTPServer
        class Server(original):
            def serve_forever(self):
                instances.append(self)
                ready.set()
                super().serve_forever(poll_interval=0.01)
            def shutdown_request(self, request):
                super().shutdown_request(request)
                saved.set()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            argv = ['probe', '--allow-live', '--microphone', '--port', '0', '--output', str(output)]
            level = logging.root.manager.disable
            with patch.object(probe, 'ThreadingHTTPServer', Server), patch('sys.argv', argv), \
                 patch.dict('os.environ', {'OPENAI_API_KEY': 'synthetic'}), \
                 patch.dict('sys.modules', {'openai': types.SimpleNamespace(AsyncOpenAI=DummyClient)}), \
                 patch.object(probe.voice, 'voice_turn', operation):
                worker = threading.Thread(target=probe.main, daemon=True)
                worker.start()
                self.assertTrue(ready.wait(3))
                origin = f'http://127.0.0.1:{instances[0].server_port}'
                with urllib.request.urlopen(origin, timeout=3) as response:
                    nonce = re.search("'X-Probe-Nonce':'([^']+)'", response.read().decode()).group(1)
                def post(path, body=b''):
                    request = urllib.request.Request(origin + path, data=body,
                        headers={'Origin': origin, 'X-Probe-Nonce': nonce})
                    try:
                        with urllib.request.urlopen(request, timeout=5) as response:
                            return response.status, json.load(response)
                    except urllib.error.HTTPError as error:
                        with error:
                            return error.code, json.load(error)
                try:
                    yield post, output, origin, nonce, saved
                finally:
                    instances[0].shutdown()
                    worker.join(3)
                    self.assertFalse(worker.is_alive())
                    logging.disable(level)

    def test_input_rejection_allows_only_three_attempts(self):
        async def reject(*args):
            raise probe.voice.UnexpectedTranscript('no_speech')
        with self.server(reject) as (post, output, *_):
            for attempt in range(1, 4):
                self.assertEqual(post('/fixture')[0], 200)
                code, response = post('/voice', b'\x01\x00')
                self.assertEqual(code, 422)
                self.assertEqual(response['retryable'], attempt < 3)
            self.assertEqual(post('/fixture')[0], 409)
            self.assertEqual(json.loads(output.read_text())['calls'], [])

    def test_provider_timeout_is_terminal_without_chat_or_retry(self):
        calls = []
        async def timeout(*args):
            calls.append(True)
            raise TimeoutError('sensitive-provider-error-must-not-escape')
        with self.server(timeout) as (post, output, *_):
            post('/fixture')
            code, response = post('/voice', b'\x01\x00')
            self.assertEqual(code, 500)
            self.assertEqual(post('/chat')[0], 409)
            self.assertEqual(post('/voice', b'\x01\x00')[0], 409)
            report = output.read_text()
            self.assertNotIn('sensitive-provider', report + json.dumps(response))
            self.assertEqual(json.loads(report)['calls'], [])
            self.assertEqual(len(calls), 1)

    def test_silent_or_malformed_pcm_never_calls_provider(self):
        calls = []
        async def unexpected(*args):
            calls.append(True)
            raise RuntimeError('Provider must not be called')
        with self.server(unexpected) as (post, output, *_):
            for pcm, reason in [(b'\x00\x00' * 24000, 'no_speech'), (b'x', 'invalid_audio')]:
                post('/fixture')
                code, response = post('/voice', pcm)
                self.assertEqual(code, 422)
                self.assertEqual(response['reason'], reason)
            self.assertEqual(calls, [])
            self.assertEqual(json.loads(output.read_text())['calls'], [])

    def test_disconnect_preserves_completed_work_and_blocks_redispatch(self):
        started, release = threading.Event(), threading.Event()
        dispatched = []
        async def complete(pcm, session, calls, client):
            dispatched.append(True)
            started.set()
            if not release.wait(3):
                raise TimeoutError('test did not release operation')
            calls.append({'execution_id': 'synthetic', 'completed': True})
            return b'\x01\x00' * 24000, ['turn_started', 'turn_ended', 'session_ended']
        with self.server(complete) as (post, output, origin, nonce, saved):
            post('/fixture')
            port = int(origin.rsplit(':', 1)[1])
            connection = socket.create_connection(('127.0.0.1', port), timeout=3)
            request = (f'POST /voice HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nOrigin: {origin}\r\n'
                       f'X-Probe-Nonce: {nonce}\r\nContent-Length: 2\r\n\r\n').encode() + b'\x01\x00'
            try:
                connection.sendall(request)
                self.assertTrue(started.wait(3))
                # The active request owns the lock: a concurrent duplicate is denied.
                self.assertEqual(post('/voice', b'\x01\x00')[0], 409)
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
                connection.close()
                saved.clear()
            finally:
                release.set()
                connection.close()
            self.assertTrue(saved.wait(3))
            self.assertEqual(post('/voice', b'\x01\x00')[0], 409)
            report = json.loads(output.read_text())
            self.assertEqual(report['status'], 'voice_passed')
            self.assertTrue(report['client_delivery_lost'])
            self.assertEqual(len(report['calls']), 1)
            self.assertTrue(report['calls'][0]['completed'])
            self.assertEqual(len(dispatched), 1)
