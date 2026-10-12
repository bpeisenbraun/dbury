#!/usr/bin/env python3
"""Build the browser catalog from the comic archive."""

from __future__ import annotations

import argparse
import bisect
import html
import json
import re
import sys
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


FILENAME_RE = re.compile(r"db(?P<year>\d{2})(?P<month>\d{2})(?P<day>\d{2})\.(?:gif|png)$")
TYPE_ORDER = {"daily": 0, "sunday": 1}
ALLOWED_SPAN_CLASSES = {"doones-character", "real-person"}


class DescriptionSanitizer(HTMLParser):
    """Retain only the small markup vocabulary used by archive descriptions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "em":
            self.parts.append("<em>")
            self.open_tags.append("em")
            return

        if tag == "span":
            class_name = next((value for key, value in attrs if key == "class"), None)
            if class_name in ALLOWED_SPAN_CLASSES:
                self.parts.append(f'<span class="{class_name}">')
                self.open_tags.append("span")
                return

        self.open_tags.append(None)

    def handle_endtag(self, tag: str) -> None:
        if not self.open_tags:
            return
        retained_tag = self.open_tags.pop()
        if retained_tag == tag:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data, quote=False))

    def get_html(self) -> str:
        for retained_tag in reversed(self.open_tags):
            if retained_tag:
                self.parts.append(f"</{retained_tag}>")
        self.open_tags.clear()
        return "".join(self.parts).strip()


def sanitize_description(value: str) -> str:
    sanitizer = DescriptionSanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return sanitizer.get_html()


def parse_image_date(path: Path) -> date:
    match = FILENAME_RE.fullmatch(path.name)
    if not match:
        raise ValueError(f"unsupported image filename: {path}")

    try:
        year = int(path.parent.name)
    except ValueError as error:
        raise ValueError(f"image is not inside a four-digit year directory: {path}") from error

    if year % 100 != int(match.group("year")):
        raise ValueError(f"filename year does not match directory year: {path}")

    try:
        return date(year, int(match.group("month")), int(match.group("day")))
    except ValueError as error:
        raise ValueError(f"invalid calendar date in filename: {path}") from error


def load_metadata(strips_root: Path) -> tuple[dict[str, list[dict[str, Any]]], int]:
    metadata: dict[str, list[dict[str, Any]]] = {"daily": [], "sunday": []}
    seen: set[tuple[str, date]] = set()
    record_count = 0

    for metadata_path in sorted(strips_root.glob("*.json")):
        try:
            records = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"could not read metadata file {metadata_path}: {error}") from error

        if not isinstance(records, list):
            raise ValueError(f"metadata file must contain an array: {metadata_path}")

        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"metadata record must be an object: {metadata_path}")
            try:
                strip_type = record["type"]
                metadata_date = date.fromisoformat(record["date"])
                description = record["description"]
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"invalid metadata record in {metadata_path}: {record!r}") from error

            if strip_type not in TYPE_ORDER or not isinstance(description, str):
                raise ValueError(f"invalid metadata type or description in {metadata_path}: {record!r}")
            key = (strip_type, metadata_date)
            if key in seen:
                raise ValueError(f"duplicate metadata date and type: {strip_type} {metadata_date}")
            seen.add(key)
            record_count += 1
            metadata[strip_type].append(
                {
                    "date": metadata_date,
                    "descriptionHtml": sanitize_description(description),
                }
            )

    for records in metadata.values():
        records.sort(key=lambda record: record["date"])
    return metadata, record_count


def description_for(
    strip_type: str,
    strip_date: date,
    metadata: dict[str, list[dict[str, Any]]],
) -> dict[str, str] | None:
    records = metadata[strip_type]
    dates = [record["date"] for record in records]
    index = bisect.bisect_right(dates, strip_date) - 1
    if index < 0:
        return None

    record = records[index]
    difference = (strip_date - record["date"]).days
    if strip_type == "sunday" and difference != 0:
        return None
    if strip_type == "daily" and not 0 <= difference <= 6:
        return None

    return {
        "descriptionHtml": record["descriptionHtml"],
        "descriptionSourceDate": record["date"].isoformat(),
    }


def build_catalog(strips_root: Path) -> tuple[dict[str, Any], dict[str, int]]:
    metadata, metadata_count = load_metadata(strips_root)
    strips: list[dict[str, Any]] = []
    image_keys: set[tuple[str, date]] = set()
    weekday_anomalies = 0

    for strip_type in TYPE_ORDER:
        type_root = strips_root / strip_type
        if not type_root.is_dir():
            raise ValueError(f"missing archive directory: {type_root}")

        for path in sorted(type_root.glob("*/*")):
            if not path.is_file():
                continue
            strip_date = parse_image_date(path)
            key = (strip_type, strip_date)
            if key in image_keys:
                raise ValueError(f"duplicate strip type and date: {strip_type} {strip_date}")
            image_keys.add(key)

            if (strip_type == "daily" and strip_date.weekday() == 6) or (
                strip_type == "sunday" and strip_date.weekday() != 6
            ):
                weekday_anomalies += 1

            record: dict[str, Any] = {
                "id": f"{strip_type}-{strip_date.isoformat()}",
                "date": strip_date.isoformat(),
                "type": strip_type,
                "path": path.relative_to(strips_root.parent).as_posix(),
            }
            description = description_for(strip_type, strip_date, metadata)
            if description:
                record.update(description)
            strips.append(record)

    if not strips:
        raise ValueError("archive contains no strip images")

    strips.sort(key=lambda strip: (strip["date"], TYPE_ORDER[strip["type"]]))
    strip_ids = [strip["id"] for strip in strips]
    if len(strip_ids) != len(set(strip_ids)):
        raise ValueError("generated catalog contains duplicate strip IDs")

    years: list[dict[str, Any]] = []
    for year in sorted({int(strip["date"][:4]) for strip in strips}):
        year_strips = [strip for strip in strips if strip["date"].startswith(f"{year}-")]
        counts = Counter(strip["type"] for strip in year_strips)
        years.append(
            {
                "year": year,
                "firstStripId": year_strips[0]["id"],
                "lastStripId": year_strips[-1]["id"],
                "count": len(year_strips),
                "dailyCount": counts["daily"],
                "sundayCount": counts["sunday"],
            }
        )

    metadata_without_exact_image = sum(
        (strip_type, record["date"]) not in image_keys
        for strip_type, records in metadata.items()
        for record in records
    )
    same_date_collisions = len(strips) - len({strip["date"] for strip in strips})
    described_count = sum("descriptionHtml" in strip for strip in strips)

    catalog = {
        "version": 1,
        "archive": {
            "firstDate": strips[0]["date"],
            "lastDate": strips[-1]["date"],
            "totalCount": len(strips),
            "dailyCount": sum(strip["type"] == "daily" for strip in strips),
            "sundayCount": sum(strip["type"] == "sunday" for strip in strips),
        },
        "years": years,
        "strips": strips,
    }
    diagnostics = {
        "metadataRecords": metadata_count,
        "describedStrips": described_count,
        "metadataWithoutExactImage": metadata_without_exact_image,
        "sameDateCollisions": same_date_collisions,
        "weekdayAnomalies": weekday_anomalies,
    }
    return catalog, diagnostics


def serialize_catalog(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n"


def parse_args() -> argparse.Namespace:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strips-root", type=Path, default=repository_root / "strips")
    parser.add_argument("--output", type=Path, default=repository_root / "data" / "catalog.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify that the existing output matches a freshly generated catalog",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog, diagnostics = build_catalog(args.strips_root.resolve())
        rendered = serialize_catalog(catalog)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.check:
        try:
            existing = args.output.read_text(encoding="utf-8")
        except OSError as error:
            print(f"error: could not read {args.output}: {error}", file=sys.stderr)
            return 1
        if existing != rendered:
            print(f"error: {args.output} is stale; rebuild it without --check", file=sys.stderr)
            return 1
        action = "verified"
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        action = "wrote"

    archive = catalog["archive"]
    print(
        f"{action} {args.output}: {archive['totalCount']} strips "
        f"({archive['dailyCount']} daily, {archive['sundayCount']} Sunday), "
        f"{len(catalog['years'])} years"
    )
    print(
        "diagnostics: "
        f"{diagnostics['sameDateCollisions']} same-date collisions, "
        f"{diagnostics['weekdayAnomalies']} weekday anomalies, "
        f"{diagnostics['metadataWithoutExactImage']} metadata records without an exact image, "
        f"{diagnostics['describedStrips']} strips with descriptions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
