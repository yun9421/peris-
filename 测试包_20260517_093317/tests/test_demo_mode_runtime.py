import json
import unittest
from unittest.mock import patch

import app as app_module


class _FakeStreamingResponse:
    def __init__(self, status_code=200, json_body=None, iter_lines=None):
        self.status_code = status_code
        self._json_body = json_body or {}
        self._iter_lines_data = iter_lines or []

    def json(self):
        return self._json_body

    def iter_lines(self, decode_unicode=False):
        for line in self._iter_lines_data:
            yield line if decode_unicode else line.encode("utf-8")


class DemoModeRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        app_module.DEMO_USAGE["total"] = 0
        app_module.DEMO_USAGE["per_ip"].clear()

    def test_chat_stream_uses_demo_key_when_request_key_missing(self):
        captured_headers = {}

        def fake_post(_url, headers=None, json=None, stream=None, timeout=None):
            captured_headers.update(headers or {})
            return _FakeStreamingResponse(
                iter_lines=[
                    'data: {"choices":[{"delta":{"content":"测试"}}]}',
                    "data: [DONE]",
                ]
            )

        with patch.dict(
            "os.environ",
            {
                "DEMO_MODE_ENABLED": "true",
                "DEMO_API_KEY": "demo-secret",
                "DEMO_MAX_REQUESTS_PER_IP": "8",
                "DEMO_MAX_REQUESTS_TOTAL": "80",
            },
            clear=False,
        ), patch("app.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/chat/stream",
                json={"character_id": "余墨", "chapter_text": "第一章示例正文", "api_key": ""},
            )
            body = b"".join(response.response).decode("utf-8")

        self.assertEqual("Bearer demo-secret", captured_headers.get("Authorization"))
        self.assertIn("测试", body)
        self.assertIn("[DONE]", body)

    def test_demo_status_reports_enabled_and_quota_remaining(self):
        with patch.dict(
            "os.environ",
            {
                "DEMO_MODE_ENABLED": "true",
                "DEMO_API_KEY": "demo-secret",
                "DEMO_MAX_REQUESTS_PER_IP": "2",
                "DEMO_MAX_REQUESTS_TOTAL": "3",
            },
            clear=False,
        ):
            response = self.client.get("/demo-status")
            data = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertTrue(data["enabled"])
        self.assertTrue(data["available"])
        self.assertFalse(data["requires_api_key"])

    def test_chat_stream_blocks_when_demo_quota_is_exhausted(self):
        app_module.DEMO_USAGE["total"] = 1
        app_module.DEMO_USAGE["per_ip"]["127.0.0.1"] = 1

        with patch.dict(
            "os.environ",
            {
                "DEMO_MODE_ENABLED": "true",
                "DEMO_API_KEY": "demo-secret",
                "DEMO_MAX_REQUESTS_PER_IP": "1",
                "DEMO_MAX_REQUESTS_TOTAL": "1",
            },
            clear=False,
        ):
            response = self.client.post(
                "/chat/stream",
                json={"character_id": "余墨", "chapter_text": "第一章示例正文", "api_key": ""},
            )
            body = b"".join(response.response).decode("utf-8")

        self.assertEqual(200, response.status_code)
        self.assertIn("演示额度已用完", body)


if __name__ == "__main__":
    unittest.main()
