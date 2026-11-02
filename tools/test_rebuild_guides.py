import re
import unittest

from rebuild_guides import shorten_fragment_ids


class FragmentIdsTest(unittest.TestCase):
    def test_japanese_ids_and_links_match_and_are_short(self):
        source = '<a href="#始める前の準備と費用">準備</a><h2 id="始める前の準備と費用">準備</h2>'
        result = shorten_fragment_ids(source)
        identifier = re.search(r'id="([^"]+)"', result)[1]
        self.assertTrue(identifier.isascii())
        self.assertLess(len(identifier.encode()), 127)
        self.assertIn(f'href="#{identifier}"', result)
        self.assertIn(">準備</h2>", result)
        self.assertEqual(shorten_fragment_ids(result), result)

    def test_short_ids_and_external_links_are_unchanged(self):
        source = '<section id="participant"><a href="#participant">本文</a><a href="https://example.com/#日本語">外部</a></section>'
        self.assertEqual(shorten_fragment_ids(source), source)

    def test_long_ascii_ids_and_distinct_sections(self):
        identifiers = ["a" * 150, "準備", "self-study-準備"]
        source = "".join(f'<h2 id="{value}"></h2><a href="#{value}">link</a>' for value in identifiers)
        result = shorten_fragment_ids(source)
        shortened = re.findall(r'id="([^"]+)"', result)
        self.assertEqual(len(set(shortened)), len(identifiers))
        for identifier in shortened:
            self.assertLess(len(identifier), 127)
            self.assertIn(f'href="#{identifier}"', result)


if __name__ == "__main__":
    unittest.main()
