import json
import unittest
from unittest.mock import patch

from app import app


class _FakeJsonResponse:
    def __init__(self, content: str, status_code: int = 200):
        self.status_code = status_code
        self._content = content

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": self._content,
                    }
                }
            ]
        }


class HealthReportRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _post_report(self, model_output: str):
        payloads = []

        def fake_post(_url, headers=None, json=None, timeout=None):
            payloads.append({"headers": headers, "json": json, "timeout": timeout})
            return _FakeJsonResponse(model_output)

        with patch("app.requests.post", side_effect=fake_post):
            response = self.client.post(
                "/report/health",
                json={
                    "chapter_text": "第一章示例正文",
                    "api_key": "user-key",
                },
            )
        return response, payloads

    def test_health_report_returns_structured_json(self):
        model_output = json.dumps(
            {
                "title": "Pieris 作品体检报告",
                "genre_guess": "都市成长",
                "tone": "克制压抑",
                "core_hook": "人物关系有立即追看的张力",
                "scores": {
                    "structure": 8.2,
                    "character": 7.5,
                    "pacing": 6.9,
                    "language": 7.8,
                    "readability": 8.1,
                },
                "highlights": ["人物开场利落", "关系冲突明确", "句子有压迫感"],
                "risks": ["中段信息解释偏多", "配角面目偏模糊", "情绪峰值出现太早"],
                "priority_actions": ["收紧第二段说明", "补一处配角动作", "把冲突再前置半段"],
                "suitable_editors": ["余墨", "铁板"],
                "summary": "这篇最值得保的是人物关系张力，最先要修的是节奏和说明。",
            },
            ensure_ascii=False,
        )

        response, payloads = self._post_report(model_output)
        data = response.get_json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("Bearer user-key", payloads[0]["headers"]["Authorization"])
        self.assertEqual("都市成长", data["report"]["genre_guess"])
        self.assertEqual(5, len(data["report"]["scores"]))
        self.assertEqual(["余墨", "铁板"], data["report"]["suitable_editors"])

    def test_health_report_fills_missing_fields_and_clamps_values(self):
        model_output = json.dumps(
            {
                "scores": {
                    "structure": 12,
                    "character": -3,
                },
                "highlights": ["亮点1"],
                "suitable_editors": ["不存在的角色", "余墨", "铁板"],
            },
            ensure_ascii=False,
        )

        response, _ = self._post_report(model_output)
        data = response.get_json()["report"]

        self.assertEqual(10, data["scores"]["structure"])
        self.assertEqual(1, data["scores"]["character"])
        self.assertEqual(3, len(data["highlights"]))
        self.assertEqual(3, len(data["risks"]))
        self.assertEqual(3, len(data["priority_actions"]))
        self.assertEqual(["余墨", "铁板"], data["suitable_editors"])
        self.assertTrue(data["summary"])

    def test_health_report_returns_error_when_model_output_is_not_json(self):
        response, _ = self._post_report("这不是 JSON")
        data = response.get_json()

        self.assertEqual(502, response.status_code)
        self.assertIn("体检报告解析失败", data["error"])


if __name__ == "__main__":
    unittest.main()
