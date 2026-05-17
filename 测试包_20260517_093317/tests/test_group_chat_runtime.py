import unittest
import json
from unittest.mock import patch

from app import app


class _FakeChatCompletionResponse:
    def __init__(self, content: str):
        self.status_code = 200
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


class GroupChatRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def _post_group_chat(self, chapter_text: str, round_outputs: list[str], character_ids=None):
        payloads = []
        outputs = iter(round_outputs)

        def fake_post(_url, headers=None, json=None, timeout=None):
            payloads.append(json)
            return _FakeChatCompletionResponse(next(outputs))

        with patch("app.requests.post", side_effect=fake_post), patch("time.sleep", return_value=None):
            response = self.client.post(
                "/chat/group",
                json={
                    "chapter_text": chapter_text,
                    "api_key": "test-key",
                    "character_ids": character_ids or ["铁板", "余墨"],
                },
            )
            body = b"".join(response.response).decode("utf-8")

        return response, body, payloads

    def _parse_sse_events(self, body: str):
        events = []
        for chunk in body.split("\n\n"):
            if not chunk.startswith("data: "):
                continue
            data = chunk[6:]
            if data == "[DONE]":
                events.append("[DONE]")
            else:
                events.append(json.loads(data))
        return events

    def _round_outputs(self, speakers: list[str]) -> list[str]:
        outputs = []
        for round_num in range(1, 4):
            outputs.append(
                "\n".join(
                    f"{speaker}：第{round_num}轮，{speaker}的第{round_num}条消息。"
                    for speaker in speakers
                )
            )
        return outputs

    def test_group_chat_truncates_chapter_context_to_first_3000_chars(self):
        chapter_text = "第1章 开头\n" + ("甲" * 3200) + "\n这里是章节末尾标记"
        outputs = self._round_outputs(["铁板", "余墨"])

        _, _, payloads = self._post_group_chat(
            chapter_text=chapter_text,
            round_outputs=outputs,
        )

        self.assertEqual(3, len(payloads), "群聊应恢复为每轮只请求一次模型")
        first_prompt = payloads[0]["messages"][0]["content"]
        self.assertNotIn(
            "这里是章节末尾标记",
            first_prompt,
            "群聊应恢复原版做法，只取前 3000 字上下文以提高稳定性",
        )

    def test_group_chat_first_round_streams_three_messages_for_three_speakers(self):
        speakers = ["铁板", "余墨", "知苑"]
        outputs = self._round_outputs(speakers)

        _, body, _ = self._post_group_chat(
            chapter_text="第1章 示例正文",
            round_outputs=outputs,
            character_ids=speakers,
        )

        events = self._parse_sse_events(body)
        self.assertEqual(speakers * 3, events[0]["order"])
        message_events = [event for event in events[1:] if isinstance(event, dict) and "editor" in event]
        self.assertEqual(["铁板", "余墨", "知苑"], [event["editor"] for event in message_events[:3]])
        self.assertEqual(
            [
                "铁板：第1轮，铁板的第1条消息。",
                "余墨：第1轮，余墨的第1条消息。",
                "知苑：第1轮，知苑的第1条消息。",
            ],
            [f"{event['editor']}：{event['message']}" for event in message_events[:3]],
        )
        self.assertEqual("[DONE]", events[-1])

    def test_group_chat_calls_model_once_per_round(self):
        speakers = ["铁板", "余墨", "知苑"]
        outputs = self._round_outputs(speakers)

        _, _, payloads = self._post_group_chat(
            chapter_text="第1章 示例正文",
            round_outputs=outputs,
            character_ids=speakers,
        )

        self.assertEqual(3, len(payloads), "三人三轮应总共请求模型 3 次")
        self.assertEqual(
            [f"请输出第{round_num}轮的3行群聊记录。" for round_num in range(1, 4)],
            [payload["messages"][1]["content"] for payload in payloads],
            "群聊后端应恢复为每轮一次生成多人，而不是逐条调用模型",
        )

    def test_group_chat_injects_previous_round_history_into_later_requests(self):
        speakers = ["铁板", "余墨", "知苑"]
        outputs = self._round_outputs(speakers)

        _, _, payloads = self._post_group_chat(
            chapter_text="第1章 示例正文",
            round_outputs=outputs,
            character_ids=speakers,
        )

        self.assertEqual(3, len(payloads), "应只有三轮请求")
        second_request_text = "\n".join(message["content"] for message in payloads[1]["messages"])
        third_request_text = "\n".join(message["content"] for message in payloads[2]["messages"])

        self.assertIn("铁板：第1轮，铁板的第1条消息。", second_request_text)
        self.assertIn("余墨", second_request_text)
        self.assertIn("知苑", second_request_text)
        self.assertIn("铁板：第1轮，铁板的第1条消息。", third_request_text)
        self.assertIn("铁板：第2轮，铁板的第2条消息。", third_request_text)

    def test_group_chat_falls_back_to_first_speaker_when_round_output_cannot_be_parsed(self):
        raw_text = "这段有点拖，但尾巴那句还能救回来。"

        _, body, _ = self._post_group_chat(
            chapter_text="第1章 示例正文",
            round_outputs=[raw_text, "铁板：第二轮。\n余墨：第二轮。", "铁板：第三轮。\n余墨：第三轮。"],
            character_ids=["铁板", "余墨"],
        )

        events = self._parse_sse_events(body)
        message_events = [event for event in events if isinstance(event, dict) and event.get("editor")]
        self.assertEqual("铁板", message_events[0]["editor"])
        self.assertEqual(raw_text[:200], message_events[0]["message"])


if __name__ == "__main__":
    unittest.main()
