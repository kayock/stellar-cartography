"""TTS provider abstraction, cache, and Cartography /api/tts endpoints."""

from __future__ import annotations

import json
import struct
import tempfile
import threading
import unittest
from pathlib import Path
from app import tts_client
from app.server import run_server


def tiny_wav(frames: int = 32) -> bytes:
    data = b"\x00\x00" * frames
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        16000,
        32000,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data


def mock_transport(health_ok=True, speak_body=None, raise_timeout=False, speak_calls=None):
    wav = speak_body if speak_body is not None else tiny_wav()

    def send(url, method="GET", payload=None, timeout=3.0):
        if not tts_client.is_allowed_local_tts_url(url):
            raise tts_client.TTSError("unsafe", code="unsafe_endpoint")
        if url.endswith("/health"):
            if not health_ok:
                raise tts_client.TTSError("Voice service unavailable.", code="unavailable", status=503)
            return {"status": 200, "body": b'{"status":"ok"}', "mime_type": "application/json"}
        if url.endswith("/speak"):
            if speak_calls is not None:
                speak_calls.append({"url": url, "payload": payload})
            if raise_timeout:
                raise tts_client.TTSError("Voice service timed out.", code="timeout", status=504)
            return {"status": 200, "body": wav, "mime_type": "audio/wav"}
        raise tts_client.TTSError("unexpected url", code="unsafe_endpoint")

    return send


class TestProviderValidation(unittest.TestCase):
    def test_known_providers(self):
        ids = {item["id"] for item in tts_client.list_providers()}
        self.assertEqual(ids, {"father_fox", "kayock_voice"})

    def test_invalid_provider(self):
        with self.assertRaises(tts_client.TTSError) as ctx:
            tts_client.normalize_request({"text": "Hello sky.", "provider": "cloud_tts"})
        self.assertEqual(ctx.exception.code, "invalid_provider")

    def test_excessive_length(self):
        with self.assertRaises(tts_client.TTSError) as ctx:
            tts_client.normalize_request({"text": "x" * 4000, "provider": "father_fox"})
        self.assertEqual(ctx.exception.code, "text_too_long")

    def test_rejects_arbitrary_url_proxy_fields(self):
        with self.assertRaises(tts_client.TTSError) as ctx:
            tts_client.normalize_request(
                {
                    "text": "Hello sky.",
                    "provider": "father_fox",
                    "url": "https://evil.example/speak",
                }
            )
        self.assertEqual(ctx.exception.code, "unsafe_field")

    def test_rejects_non_local_endpoint(self):
        self.assertFalse(tts_client.is_allowed_local_tts_url("https://evil.example/speak"))
        self.assertFalse(tts_client.is_allowed_local_tts_url("http://127.0.0.1:8766/speak"))
        self.assertTrue(tts_client.is_allowed_local_tts_url("https://127.0.0.1:8766/speak"))

    def test_config_rejects_arbitrary_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tts.json"
            path.write_text(
                json.dumps(
                    {
                        "providers": {
                            "father_fox": {
                                "health_url": "https://evil.example/health",
                                "tts_url": "https://evil.example/speak",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(tts_client.TTSError) as ctx:
                tts_client.load_config(path)
            self.assertEqual(ctx.exception.code, "unsafe_endpoint")


class TestSynthesisAndCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_father_fox_mock_synthesis(self):
        calls = []
        result = tts_client.synthesize(
            "Orion is a constellation.",
            "father_fox",
            cache_dir=self.cache,
            transport=mock_transport(speak_calls=calls),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "father_fox")
        self.assertEqual(result["label"], "Cartography Narration")
        self.assertFalse(result["audio_autoplay"])
        self.assertEqual(calls[0]["payload"]["text"], "Orion is a constellation.")
        self.assertEqual(calls[0]["payload"]["profile"], "father_fox")
        self.assertTrue(calls[0]["url"].endswith("/speak"))

    def test_kayock_voice_mock_synthesis(self):
        result = tts_client.synthesize(
            "Rigel is a blue-white star.",
            "kayock_voice",
            cache_dir=self.cache,
            transport=mock_transport(),
        )
        self.assertEqual(result["provider"], "kayock_voice")
        self.assertEqual(result["profile"], "eve")
        self.assertIn("RIFF", result["audio"][:4].decode("latin1"))

    def test_unavailable_provider(self):
        with self.assertRaises(tts_client.TTSError) as ctx:
            tts_client.synthesize(
                "Hello.",
                "father_fox",
                cache_dir=self.cache,
                transport=mock_transport(health_ok=False),
            )
        self.assertEqual(ctx.exception.code, "unavailable")

    def test_timeout(self):
        with self.assertRaises(tts_client.TTSError) as ctx:
            tts_client.synthesize(
                "Hello.",
                "kayock_voice",
                cache_dir=self.cache,
                transport=mock_transport(raise_timeout=True),
            )
        self.assertEqual(ctx.exception.code, "timeout")

    def test_health_payload(self):
        payload = tts_client.providers_payload(transport=mock_transport())
        self.assertTrue(all(item["available"] for item in payload["providers"]))
        down = tts_client.provider_health("father_fox", transport=mock_transport(health_ok=False))
        self.assertFalse(down["available"])
        self.assertIn("unavailable", down["status"])

    def test_cache_hit_and_miss_and_voice_separation(self):
        calls = []
        send = mock_transport(speak_calls=calls)
        first = tts_client.synthesize("Same line.", "father_fox", cache_dir=self.cache, transport=send)
        second = tts_client.synthesize("Same line.", "father_fox", cache_dir=self.cache, transport=send)
        other = tts_client.synthesize(
            "Same line.",
            "kayock_voice",
            cache_dir=self.cache,
            transport=send,
        )
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertFalse(other["cache_hit"])
        self.assertEqual(len(calls), 2)

    def test_failed_synthesis_is_not_cached(self):
        with self.assertRaises(tts_client.TTSError):
            tts_client.synthesize(
                "Hello.",
                "father_fox",
                cache_dir=self.cache,
                transport=mock_transport(health_ok=False),
            )
        self.assertEqual(list(self.cache.glob("*.wav")), [])


class TestTtsServerEndpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.httpd = run_server(
            host="127.0.0.1",
            port=0,
            stellarium_base_url="http://127.0.0.1:1",
            tts_cache_dir=self.tmp.name,
            tts_transport=mock_transport(),
        )
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def _json(self, method, path, body=None):
        import urllib.request

        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def test_providers_and_synthesize_and_stop(self):
        providers = self._json("GET", "/api/tts/providers")
        self.assertTrue(providers["ok"])
        self.assertEqual(providers["label"], "Cartography Narration")
        spoken = self._json(
            "POST",
            "/api/tts/synthesize",
            {"text": "Orion is equatorial.", "provider": "father_fox", "context": "constellation_overview"},
        )
        self.assertTrue(spoken["ok"])
        self.assertFalse(spoken["audio_autoplay"])
        self.assertTrue(spoken["audio_base64"])
        stopped = self._json("POST", "/api/tts/stop", {})
        self.assertTrue(stopped["stopped"])
        status = self._json("GET", "/api/tts/status")
        self.assertEqual(status["label"], "Cartography Narration")

    def test_invalid_provider_and_proxy_refusal(self):
        bad = self._json("POST", "/api/tts/synthesize", {"text": "Hi.", "provider": "elevenlabs"})
        self.assertFalse(bad["ok"])
        proxy = self._json(
            "POST",
            "/api/tts/synthesize",
            {"text": "Hi.", "provider": "father_fox", "url": "https://evil.example/speak"},
        )
        self.assertFalse(proxy["ok"])
        self.assertEqual(proxy["code"], "unsafe_field")


class TestNarrationLabel(unittest.TestCase):
    def test_constellation_overview_is_local_not_nasa(self):
        from app import constellation_story
        from app import experience

        story = constellation_story.get_story("orion")
        payload = experience.narration_payload(
            {"name": "Betelgeuse", "constellation": "Ori"},
            {},
            kind="constellation_overview",
            constellation=story,
        )
        self.assertEqual(payload["label"], "Cartography Narration")
        self.assertNotIn("NASA Narration", payload["text"])
        self.assertGreater(len(payload["text"]), 40)
