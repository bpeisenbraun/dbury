import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.build_catalog import (
    build_catalog,
    parse_image_date,
    sanitize_description,
    serialize_catalog,
)


class CatalogBuilderTests(unittest.TestCase):
    def test_parse_image_date_uses_full_directory_year(self):
        self.assertEqual(parse_image_date(Path("daily/1970/db701026.gif")), date(1970, 10, 26))
        self.assertEqual(parse_image_date(Path("sunday/2020/db200614.png")), date(2020, 6, 14))

    def test_parse_image_date_rejects_year_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_image_date(Path("daily/1971/db701026.gif"))

    def test_description_sanitizer_retains_only_archive_markup(self):
        source = (
            '<span class="doones-character" onclick="bad()">Mike</span> meets '
            '<em>B.D.</em><script>alert("no")</script>'
        )
        self.assertEqual(
            sanitize_description(source),
            '<span class="doones-character">Mike</span> meets <em>B.D.</em>alert("no")',
        )

    def test_catalog_merges_types_and_attaches_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "strips"
            (root / "daily" / "2000").mkdir(parents=True)
            (root / "sunday" / "2000").mkdir(parents=True)
            (root / "daily" / "2000" / "db000101.gif").touch()
            (root / "daily" / "2000" / "db000102.gif").touch()
            (root / "sunday" / "2000" / "db000102.png").touch()
            (root / "daily" / "2000" / "db000103.gif").touch()
            metadata = [
                {"date": "2000-01-01", "description": "A daily story", "type": "daily"},
                {"date": "2000-01-02", "description": "A Sunday story", "type": "sunday"},
            ]
            (root / "2000.json").write_text(json.dumps(metadata), encoding="utf-8")

            catalog, diagnostics = build_catalog(root)

            self.assertEqual(
                [strip["id"] for strip in catalog["strips"]],
                [
                    "daily-2000-01-01",
                    "daily-2000-01-02",
                    "sunday-2000-01-02",
                    "daily-2000-01-03",
                ],
            )
            self.assertEqual(catalog["strips"][1]["descriptionHtml"], "A daily story")
            self.assertEqual(catalog["strips"][2]["descriptionHtml"], "A Sunday story")
            self.assertEqual(catalog["years"][0]["dailyCount"], 3)
            self.assertEqual(catalog["years"][0]["sundayCount"], 1)
            self.assertEqual(diagnostics["sameDateCollisions"], 1)

    def test_serialization_is_compact_and_deterministic(self):
        catalog = {"version": 1, "years": [], "strips": []}
        self.assertEqual(serialize_catalog(catalog), '{"version":1,"years":[],"strips":[]}\n')


if __name__ == "__main__":
    unittest.main()
