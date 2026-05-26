from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import OrderedDict
from itertools import product
from pathlib import Path

from .common import AgreementRow, NOT_ARTICULATED, classify_agreement_row, merge_agreement_rows, normalize_course_text


ASSIST_API_URL = "https://prod.assistng.org/articulation/api/Agreements"


def course_code(course: dict) -> str:
    return normalize_course_text(
        f"{(course.get('prefix') or '').strip()} {(course.get('courseNumber') or '').strip()}"
    )


def formatted_course(course: dict) -> str:
    code = course_code(course)
    units = course.get("minUnits")
    if isinstance(units, (int, float)):
        return f"{code} ({units:.2f})"
    return code


def receiving_from_articulation(articulation: dict) -> tuple[str, str]:
    if articulation.get("type") == "Series":
        series = articulation.get("series", {})
        courses = sorted(series.get("courses", []), key=lambda c: c.get("position", 0))
        receiving = "; ".join(course_code(course) for course in courses)
        return receiving, f"Series({series.get('conjunction', 'Unknown')})"

    if articulation.get("type") == "Course":
        return course_code(articulation.get("course", {})), "Course"

    return normalize_course_text(articulation.get("type", "")), articulation.get("type", "Unknown")


def receiving_from_template_cell(cell: dict) -> tuple[str, str] | None:
    if cell.get("type") == "Course":
        return course_code(cell.get("course", {})), "Course"

    if cell.get("type") == "Series":
        series = cell.get("series", {})
        courses = sorted(series.get("courses", []), key=lambda c: c.get("position", 0))
        receiving = "; ".join(course_code(course) for course in courses)
        return receiving, f"Series({series.get('conjunction', 'Unknown')})"

    return None


def template_receiving_rows(template_assets: list[dict]) -> OrderedDict[str, AgreementRow]:
    rows: OrderedDict[str, AgreementRow] = OrderedDict()
    for asset in sorted(template_assets, key=lambda a: a.get("position", 0)):
        if asset.get("type") != "RequirementGroup":
            continue
        sections = sorted(asset.get("sections", []), key=lambda s: s.get("position", 0))
        for section in sections:
            section_rows = sorted(section.get("rows", []), key=lambda r: r.get("position", 0))
            for row in section_rows:
                for cell in row.get("cells", []):
                    receiving = receiving_from_template_cell(cell)
                    if not receiving:
                        continue
                    receiving_text, receiving_type = receiving
                    rows.setdefault(
                        normalize_course_text(receiving_text),
                        AgreementRow(
                            receiving=receiving_text,
                            receiving_type=receiving_type,
                            sending_options=((NOT_ARTICULATED,),),
                        ).normalized(),
                    )
    return rows


def sending_options_from_assist(sending_articulation: dict) -> tuple[tuple[str, ...], ...]:
    if sending_articulation.get("noArticulationReason"):
        return ((NOT_ARTICULATED,),)

    group_options: OrderedDict[int, list[tuple[str, ...]]] = OrderedDict()
    groups = sorted(sending_articulation.get("items", []), key=lambda g: g.get("position", 0))
    for group in groups:
        courses = [
            formatted_course(course)
            for course in sorted(group.get("items", []), key=lambda c: c.get("position", 0))
            if course.get("type") == "Course"
        ]
        if not courses:
            continue

        if group.get("courseConjunction") == "Or":
            group_options[group.get("position", 0)] = [(course,) for course in courses]
        else:
            group_options[group.get("position", 0)] = [tuple(courses)]

    options = dedupe_options(
        combine_course_group_options(
            group_options,
            sending_articulation.get("courseGroupConjunctions", []),
        )
    )
    return tuple(options) if options else ((NOT_ARTICULATED,),)


def dedupe_options(options: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    deduped = []
    seen = set()
    for option in options:
        if option in seen:
            continue
        seen.add(option)
        deduped.append(option)
    return deduped


def cartesian_and_options(option_groups: list[list[tuple[str, ...]]]) -> list[tuple[str, ...]]:
    combined = []
    for selected_options in product(*option_groups):
        courses = []
        for option in selected_options:
            courses.extend(option)
        combined.append(tuple(courses))
    return combined


def combine_course_group_options(
    group_options: OrderedDict[int, list[tuple[str, ...]]],
    conjunctions: list[dict],
) -> list[tuple[str, ...]]:
    if not group_options:
        return []

    if not conjunctions:
        return [
            option
            for _position, options in group_options.items()
            for option in options
        ]

    segments: list[tuple[int, list[tuple[str, ...]]]] = []
    consumed: set[int] = set()

    for conjunction in sorted(conjunctions, key=lambda item: item.get("sendingCourseGroupBeginPosition", 0)):
        begin = conjunction.get("sendingCourseGroupBeginPosition", 0)
        end = conjunction.get("sendingCourseGroupEndPosition", begin)
        positions = [
            position
            for position in group_options
            if begin <= position <= end
        ]
        if not positions:
            continue

        selected = [group_options[position] for position in positions]
        if conjunction.get("groupConjunction") == "And":
            options = cartesian_and_options(selected)
        else:
            options = [
                option
                for option_group in selected
                for option in option_group
            ]

        segments.append((begin, options))
        consumed.update(positions)

    for position, options in group_options.items():
        if position not in consumed:
            segments.append((position, options))

    return [
        option
        for _position, options in sorted(segments, key=lambda segment: segment[0])
        for option in options
    ]


def parse_assist_payload(payload: dict) -> dict[str, AgreementRow]:
    result = payload["result"]
    template_assets = json.loads(result["templateAssets"])

    rows = template_receiving_rows(template_assets)
    articulated_receivings: set[str] = set()
    for row in articulation_rows_from_payload(payload):
        if row.receiving in articulated_receivings:
            rows[row.receiving] = merge_agreement_rows(rows[row.receiving], row)
            continue
        rows[row.receiving] = row
        articulated_receivings.add(row.receiving)

    return dict(rows)


def articulation_rows_from_payload(payload: dict) -> list[AgreementRow]:
    articulations = json.loads(payload["result"]["articulations"])
    rows = []
    for item in articulations:
        articulation = item["articulation"]
        receiving, receiving_type = receiving_from_articulation(articulation)
        rows.append(
            AgreementRow(
                receiving=receiving,
                receiving_type=receiving_type,
                sending_options=sending_options_from_assist(
                    articulation.get("sendingArticulation") or {}
                ),
            ).normalized()
        )
    return rows


def duplicate_receivings_from_payload(payload: dict) -> set[str]:
    counts: dict[str, int] = {}
    for row in articulation_rows_from_payload(payload):
        counts[row.receiving] = counts.get(row.receiving, 0) + 1
    return {receiving for receiving, count in counts.items() if count > 1}


def taxonomy_for_assist_payload(payload: dict) -> dict[str, tuple[str, ...]]:
    rows = parse_assist_payload(payload)
    duplicate_receivings = duplicate_receivings_from_payload(payload)
    return {
        receiving: classify_agreement_row(
            row,
            duplicate_receiving=receiving in duplicate_receivings,
        )
        for receiving, row in rows.items()
    }


def view_by_key_from_assist_url(url: str) -> str:
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    key = query.get("viewByKey", [None])[0]
    if not key:
        raise ValueError(f"Assist URL does not include viewByKey: {url}")
    return urllib.parse.unquote(key)


def fetch_assist_payload(view_by_key: str, timeout: int = 30) -> dict:
    query = urllib.parse.urlencode({"Key": view_by_key})
    request = urllib.request.Request(
        f"{ASSIST_API_URL}?{query}",
        headers={"accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def agreement_url_for_pair(project_root: Path, cc_name: str, uc_name: str) -> str:
    agreement_path = (
        project_root
        / "cc_agreements"
        / cc_name.replace(" ", "_").replace("/", "-")
        / "agreements.txt"
    )
    for line in agreement_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        campus, url = line.split(":", 1)
        if campus.strip() == uc_name:
            return url.strip()
    raise ValueError(f"No agreement URL found for {cc_name} -> {uc_name}")
