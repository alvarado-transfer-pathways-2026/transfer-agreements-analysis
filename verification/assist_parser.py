from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path

from .common import AgreementRow, NOT_ARTICULATED, normalize_course_text


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

    options: list[tuple[str, ...]] = []
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
            options.extend((course,) for course in courses)
        else:
            options.append(tuple(courses))

    return tuple(options) if options else ((NOT_ARTICULATED,),)


def parse_assist_payload(payload: dict) -> dict[str, AgreementRow]:
    result = payload["result"]
    template_assets = json.loads(result["templateAssets"])
    articulations = json.loads(result["articulations"])

    rows = template_receiving_rows(template_assets)
    for item in articulations:
        articulation = item["articulation"]
        receiving, receiving_type = receiving_from_articulation(articulation)
        row = AgreementRow(
            receiving=receiving,
            receiving_type=receiving_type,
            sending_options=sending_options_from_assist(
                articulation.get("sendingArticulation") or {}
            ),
        ).normalized()
        rows[row.receiving] = row

    return dict(rows)


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

