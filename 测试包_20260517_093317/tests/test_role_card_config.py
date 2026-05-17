import re
import unittest
from pathlib import Path

from app import (
    CHARACTER_SETTINGS,
    CHARACTER_TYPES,
    EDITOR_AVATARS,
    EDITOR_CHAT_PERSONAS,
    GROUP_CHAT_ROUND_TEMPLATE,
    _build_round_config,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT_DIR / "index.html"
README_MD = ROOT_DIR / "README.md"

LONG_REVIEW_SECTIONS = [
    "## 角色身份",
    "## 说话风格",
    "## 例句模板",
    "## 判断维度",
    "## 输出格式",
    "## 禁止事项",
]

GROUP_CHAT_SECTIONS = [
    "## 群聊定位",
    "## 开口方式",
    "## 回应钩子",
    "## 群聊关注点",
    "## 禁止事项",
]

EXPECTED_CHARACTER_TYPES = {
    "余墨": "professional_editor",
    "墨天平": "professional_editor",
    "铁板": "professional_editor",
    "贴吧哥": "reader_editor",
    "知苑": "reader_editor",
    "李星云": "reader_editor",
    "丰川祥子": "reader_editor",
    "克莱恩": "reader_editor",
}

LONG_REVIEW_ANCHORS = [
    "整体框架",
    "题材",
    "文风",
    "完成度",
]


class RoleCardConfigTest(unittest.TestCase):
    @staticmethod
    def _read_text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_frontend_character_block(index_text: str, role_name: str) -> str | None:
        array_match = re.search(r"const CHARACTERS = \[(.*?)\];", index_text, re.S)
        if not array_match:
            return None
        array_text = array_match.group(1)
        block_pattern = rf'\{{[^{{}}]*id:\s*"{re.escape(role_name)}"[^{{}}]*\}}'
        block_match = re.search(block_pattern, array_text, re.S)
        return block_match.group(0) if block_match else None

    def test_all_long_review_roles_use_strong_section_structure(self):
        for role_name, prompt in CHARACTER_SETTINGS.items():
            for section in LONG_REVIEW_SECTIONS:
                self.assertIn(
                    section,
                    prompt,
                    f"{role_name} 缺少长评强约束结构分节: {section}",
                )

    def test_all_group_chat_roles_use_response_hook_structure(self):
        for role_name, prompt in EDITOR_CHAT_PERSONAS.items():
            for section in GROUP_CHAT_SECTIONS:
                self.assertIn(
                    section,
                    prompt,
                    f"{role_name} 缺少群聊回应钩子分节: {section}",
                )

    def test_character_registry_matches_expected_editor_tiering(self):
        self.assertEqual(
            EXPECTED_CHARACTER_TYPES,
            CHARACTER_TYPES,
            "角色分层必须明确区分专业编辑与读者型编辑，并包含两位新增角色",
        )
        self.assertEqual(
            set(EXPECTED_CHARACTER_TYPES),
            set(CHARACTER_SETTINGS),
            "长评角色卡必须与角色类型注册同步",
        )
        self.assertEqual(
            set(EXPECTED_CHARACTER_TYPES),
            set(EDITOR_CHAT_PERSONAS),
            "群聊角色卡必须与角色类型注册同步",
        )
        self.assertEqual(
            set(EXPECTED_CHARACTER_TYPES),
            set(EDITOR_AVATARS),
            "头像映射必须与角色类型注册同步",
        )

    def test_all_long_review_roles_include_global_evaluation_anchors(self):
        for role_name, prompt in CHARACTER_SETTINGS.items():
            for anchor in LONG_REVIEW_ANCHORS:
                self.assertIn(
                    anchor,
                    prompt,
                    f"{role_name} 的长评角色卡需要覆盖整体评价锚点: {anchor}",
                )

    def test_reader_and_professional_roles_are_explicitly_labeled(self):
        for role_name, role_type in EXPECTED_CHARACTER_TYPES.items():
            prompt = CHARACTER_SETTINGS[role_name]
            label = "专业编辑" if role_type == "professional_editor" else "读者型编辑"
            self.assertIn(label, prompt, f"{role_name} 需要在长评角色卡中标明 {label} 定位")
            self.assertIn(label, EDITOR_CHAT_PERSONAS[role_name], f"{role_name} 需要在群聊角色卡中标明 {label} 定位")

    def test_group_round_prompt_injects_round_specific_instructions(self):
        speakers = ["余墨", "知苑", "克莱恩"]
        round_config = _build_round_config(speakers)
        second_round = round_config[2]
        prompt = GROUP_CHAT_ROUND_TEMPLATE.format(
            count=len(speakers),
            history_section="和以下已有的讨论记录\n\n余墨：我卡在人物转折过急。",
            personas="\n\n".join(EDITOR_CHAT_PERSONAS[name] for name in speakers),
            speaker_list=second_round["instructions"],
            respond_rule=second_round["respond_rule"],
            chapter_text="第一章示例文本",
        )
        self.assertIn(
            second_round["instructions"],
            prompt,
            "每轮的具体发言任务必须真正注入群聊提示词，而不是只生成后丢弃",
        )

    def test_index_html_does_not_force_abort_group_chat_after_review(self):
        index_text = self._read_text(INDEX_HTML)
        self.assertIn(
            "stopGroupChatWithEllipsis(sessionId)",
            index_text,
            "长评结束时应显式收束群聊并补全省略号占位",
        )
        self.assertIn(
            "activeGroupAbort.abort()",
            index_text,
            "前端应在长评结束后主动中断群聊请求",
        )
        self.assertIn(
            'fillRemainingChatSlots(sessionId)',
            index_text,
            "长评结束时应补上未发完成员的省略号占位",
        )

    def test_sakiko_and_klein_prompts_prioritize_in_character_reaction(self):
        sakiko = CHARACTER_SETTINGS["丰川祥子"]
        klein = CHARACTER_SETTINGS["克莱恩"]

        self.assertIn("ですわ", sakiko)
        self.assertIn("人間になりたいですわ", sakiko)
        self.assertIn("自然分成 3-5 段", sakiko)
        self.assertNotIn("必须依次输出以下 6 个模块", sakiko)

        self.assertIn("先别急着下结论", klein)
        self.assertIn("保留一点观察", klein)
        self.assertIn("自然分成 3-5 段", klein)
        self.assertNotIn(
            "必须依次输出以下 6 个模块",
            klein,
            "克莱恩不应再被约束成过度正经的固定点评模板",
        )

    def test_group_template_prioritizes_character_voice(self):
        self.assertIn(
            "后面的编辑尽量接前面人的话",
            GROUP_CHAT_ROUND_TEMPLATE,
            "群聊总模板应要求基本接话，避免彻底各说各话",
        )
        self.assertIn(
            '格式为"编辑名：消息内容"',
            GROUP_CHAT_ROUND_TEMPLATE,
            "群聊总模板必须保留原版的宽松多行输出格式",
        )

    def test_group_personas_keep_sakiko_and_klein_as_roleplay_first(self):
        sakiko = EDITOR_CHAT_PERSONAS["丰川祥子"]
        klein = EDITOR_CHAT_PERSONAS["克莱恩"]

        self.assertIn("大小姐敬语", sakiko)
        self.assertIn("语气要像真的祥子", sakiko)
        self.assertIn("不是专业审稿人", sakiko)

        self.assertIn("先保留判断", klein)
        self.assertIn("不像主持会议", klein)
        self.assertIn("不是专业审稿人", klein)

    def test_frontend_and_readme_register_all_characters(self):
        index_text = self._read_text(INDEX_HTML)
        readme_text = self._read_text(README_MD)

        array_match = re.search(r"const CHARACTERS = \[(.*?)\];", index_text, re.S)
        self.assertIsNotNone(array_match, "前端必须保留角色数组配置")
        frontend_ids = set(re.findall(r'id:\s*"([^"]+)"', array_match.group(1)))

        self.assertEqual(
            set(EXPECTED_CHARACTER_TYPES),
            frontend_ids,
            "前端角色数组必须与后端角色注册完全一致",
        )

        for role_name in EXPECTED_CHARACTER_TYPES:
            self.assertIn(role_name, readme_text, f"README 需要说明角色 {role_name}")

    def test_frontend_gallery_fields_exist_for_all_characters(self):
        index_text = self._read_text(INDEX_HTML)

        for role_name in EXPECTED_CHARACTER_TYPES:
            block = self._extract_frontend_character_block(index_text, role_name)
            self.assertIsNotNone(block, f"{role_name} 必须存在于前端 CHARACTERS 配置中")

            for field_name in ["tagline", "fullDesc", "tags", "mysteryLine", "image"]:
                self.assertIn(
                    f"{field_name}:",
                    block,
                    f"{role_name} 的前端角色卡缺少字段 {field_name}",
                )

    def test_priority_roles_use_local_gallery_images(self):
        index_text = self._read_text(INDEX_HTML)
        expected_local_images = {
            "丰川祥子": "/gallery-assets/丰川祥子.jpg",
            "克莱恩": "/gallery-assets/克莱恩.jpg",
            "贴吧哥": "/gallery-assets/贴吧哥.jpg",
        }

        for role_name, image_path in expected_local_images.items():
            block = self._extract_frontend_character_block(index_text, role_name)
            self.assertIsNotNone(block, f"{role_name} 必须存在于前端 CHARACTERS 配置中")
            self.assertIn(
                f'image: "{image_path}"',
                block,
                f"{role_name} 的 image 必须使用本地 gallery-assets 图片",
            )
            self.assertIn(
                f'thumb: "{image_path}"',
                block,
                f"{role_name} 的 thumb 必须使用本地 gallery-assets 图片",
            )


if __name__ == "__main__":
    unittest.main()
