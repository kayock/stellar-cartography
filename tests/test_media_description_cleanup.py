"""Tests for NASA public-media description HTML → plain-text cleanup."""

from __future__ import annotations

import unittest

from app import planetary_image


class TestSanitizeMediaDescription(unittest.TestCase):
    def test_anchor_read_more_removed(self):
        raw = (
            'Phobos is the larger Martian moon. '
            '<a href="https://images.nasa.gov/details/PIA123">Read more</a>'
        )
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Phobos is the larger Martian moon.")
        self.assertNotIn("Read more", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)
        self.assertNotIn("http", cleaned or "")

    def test_bold_and_italic_tags(self):
        raw = "Phobos is a <b>small</b> and <i>irregular</i> moon."
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Phobos is a small and irregular moon.")

    def test_nested_tags(self):
        raw = "<p>The <b>moon <i>Phobos</i></b> orbits Mars.</p>"
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "The moon Phobos orbits Mars.")

    def test_html_entities_decoded(self):
        raw = "Mars &amp; Phobos — &quot;close approach&quot; &#39;2020&#39; &#x26; dust"
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, 'Mars & Phobos — "close approach" \'2020\' & dust')

    def test_malformed_html(self):
        raw = "Start <b>bold without close and <i>italic Phobos still kept"
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertIsNotNone(cleaned)
        self.assertIn("Phobos still kept", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)

    def test_script_style_image_removed(self):
        raw = (
            "Visible text. "
            "<script>alert(1)</script>"
            "<style>.x{color:red}</style>"
            '<img src="https://evil.example/x.jpg" onerror="alert(1)">'
            " After."
        )
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Visible text. After.")
        self.assertNotIn("alert", cleaned)
        self.assertNotIn("color:red", cleaned)
        self.assertNotIn("evil.example", cleaned)

    def test_javascript_links_stripped(self):
        raw = 'Safe <a href="javascript:alert(1)">click me</a> text about Phobos.'
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Safe click me text about Phobos.")
        self.assertNotIn("javascript", cleaned)
        self.assertNotIn("<", cleaned)

    def test_raw_url_removed(self):
        raw = (
            "Phobos crater. See https://images.nasa.gov/details/PIA123 "
            "and www.example.com/more for details."
        )
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Phobos crater. See and for details.")
        self.assertNotIn("http", cleaned)
        self.assertNotIn("www.", cleaned)

    def test_no_angle_brackets_remain(self):
        raw = '<div class="x">Phobos <span>surface</span></div><br/><a href="x">Read more</a>'
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertIsNotNone(cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)
        self.assertIn("Phobos", cleaned)
        self.assertIn("surface", cleaned)

    def test_plain_text_unchanged(self):
        raw = "Phobos is the innermost and larger of the two natural satellites of Mars."
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, raw)

    def test_whitespace_collapsed(self):
        raw = "Phobos\n\n   has\t\tmany\r\ncraters."
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Phobos has many craters.")

    def test_bounded_length_word_boundary(self):
        words = " ".join(["Phobos"] + [f"word{i}" for i in range(80)])
        cleaned = planetary_image.sanitize_media_description(words, max_len=80)
        self.assertIsNotNone(cleaned)
        self.assertLessEqual(len(cleaned), 80)
        self.assertTrue(cleaned.endswith("…"))
        self.assertNotIn("<", cleaned)

    def test_iframe_removed(self):
        raw = 'Before <iframe src="https://evil.example"></iframe> Phobos after'
        cleaned = planetary_image.sanitize_media_description(raw)
        self.assertEqual(cleaned, "Before Phobos after")

    def test_parse_path_cleans_description(self):
        payload = {
            "collection": {
                "items": [
                    {
                        "data": [
                            {
                                "title": "Phobos",
                                "description": (
                                    "The <b>moon Phobos</b> near Mars. "
                                    '<a href="https://images.nasa.gov/details/X">Read more</a>'
                                ),
                                "keywords": ["Phobos", "Mars"],
                                "nasa_id": "PIAPHOBOS",
                            }
                        ],
                        "links": [
                            {
                                "href": "https://images-assets.nasa.gov/image/PIAPHOBOS/PIAPHOBOS~thumb.jpg",
                                "rel": "preview",
                            }
                        ],
                    }
                ]
            }
        }
        result = planetary_image.parse_nasa_images_response(payload, "phobos")
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["description"], "The moon Phobos near Mars.")
        self.assertNotIn("<", result["description"])
        self.assertNotIn("Read more", result["description"])


if __name__ == "__main__":
    unittest.main()
