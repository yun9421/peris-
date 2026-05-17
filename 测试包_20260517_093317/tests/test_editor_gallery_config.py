import re
import unittest
from pathlib import Path

import app as app_module


ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT_DIR / "index.html"


class EditorGalleryConfigTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_gallery_asset_route_serves_priority_images(self):
        for filename in ["丰川祥子.jpg", "克莱恩.jpg", "贴吧哥.jpg"]:
            response = self.client.get(f"/gallery-assets/{filename}")
            self.assertEqual(
                200,
                response.status_code,
                f"{filename} 应可通过 gallery-assets 路由访问",
            )
            response.close()

    def test_index_registers_extended_character_fields(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        array_match = re.search(r"const CHARACTERS = \[(.*?)\];", text, re.S)
        self.assertIsNotNone(array_match, "前端必须保留 CHARACTERS 数组")
        array_text = array_match.group(1)

        for field_name in ["tagline", "fullDesc", "tags", "mysteryLine", "image"]:
            self.assertIn(field_name, array_text, f"角色卡扩展字段缺失: {field_name}")

    def test_index_loads_local_gallery_vendor_assets(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('/vendor/swiper-bundle.min.css', text)
        self.assertIn('/vendor/swiper-bundle.min.js', text)
        self.assertIn('/vendor/floating-ui.core.min.js', text)
        self.assertIn('/vendor/floating-ui.dom.min.js', text)
        self.assertLess(
            text.index('/vendor/floating-ui.core.min.js'),
            text.index('/vendor/floating-ui.dom.min.js'),
            "Floating UI core 必须先于 DOM 包加载，否则悬浮卡片会在运行时报错",
        )

    def test_index_declares_gallery_image_map(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("const GALLERY_IMAGE_MAP = {", text)
        self.assertIn("'丰川祥子': '/gallery-assets/丰川祥子.jpg'", text)
        self.assertIn("'克莱恩': '/gallery-assets/克莱恩.jpg'", text)
        self.assertIn("'贴吧哥': '/gallery-assets/贴吧哥.jpg'", text)

    def test_index_contains_gallery_and_parallax_hooks(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="editor-gallery"', text)
        self.assertIn('id="editor-hover-card"', text)
        self.assertIn("initEditorGalleryParallax()", text)

    def test_index_contains_parallax_background_layers(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="editorial-bg"', text)
        self.assertIn('class="editorial-bg-layer', text)
        self.assertIn("initEditorGalleryParallax()", text)

    def test_index_contains_gallery_structure(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="editor-gallery"', text)
        self.assertIn('id="editor-gallery-track"', text)
        self.assertIn('id="editor-hover-card"', text)
        self.assertIn('id="editor-selection-summary"', text)

    def test_index_contains_hover_card_logic(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("renderEditorHoverCard", text)
        self.assertIn("hideEditorHoverCard", text)
        self.assertIn("if (isLockedCard(id)) return;", text)

    def test_index_renders_card_images_from_gallery_data(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("const imageSrc = c.thumb || c.image || GALLERY_IMAGE_MAP[c.name] || \"\";", text)
        self.assertIn('<div class="char-media">', text)
        self.assertIn("<img src=\"${escapeHtml(imageSrc)}\"", text)

    def test_index_keeps_hover_available_before_runtime_ready(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("function isSelectionBlocked()", text)
        self.assertIn("if (isSelectionBlocked()) {", text)
        self.assertIn("if (isLockedCard(id)) return;", text)
        self.assertNotIn("return !(hasFile && hasChapter && hasRuntimeAccess());", text)

    def test_index_contains_swiper_gallery_hooks(self):
        text = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn("initEditorGallery()", text)
        self.assertIn("editorGallerySwiper", text)
        self.assertIn("resumeGalleryAutoplay", text)


if __name__ == "__main__":
    unittest.main()
