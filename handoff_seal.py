#!/usr/bin/env python3
"""HandoffSeal: local delivery-package identity and structure checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import posixpath
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from xml.etree import ElementTree as ET


VERSION = "0.2.0"
XLSX_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XLSX_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


class GateError(Exception):
    pass


def finding(severity: str, code: str, message: str, location: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if location:
        item["location"] = location
    return item


def normal(value: Any) -> str:
    return str(value or "").strip()


def norm_header(value: Any) -> str:
    return normal(value).casefold()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


@contextmanager
def package_root(package: Path) -> Iterator[Path]:
    if package.is_dir():
        yield package
        return
    if not package.is_file() or package.suffix.casefold() != ".zip":
        raise GateError("package 必须是目录或 .zip 文件")

    with tempfile.TemporaryDirectory(prefix="handoff-seal-") as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(package) as archive:
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                if name.is_absolute() or ".." in name.parts:
                    raise GateError(f"ZIP 路径不安全: {info.filename}")
                target = extracted.joinpath(*name.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(info))

        visible = [path for path in extracted.iterdir() if path.name not in {"__MACOSX", ".DS_Store"}]
        if len(visible) == 1 and visible[0].is_dir():
            yield visible[0]
        else:
            yield extracted


def read_csv_table(path: Path) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            headers = next(reader)
        except StopIteration:
            return [], []

        rows: list[tuple[int, dict[str, str]]] = []
        for line_number, values in enumerate(reader, start=2):
            row = {headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))}
            rows.append((line_number, row))
    return headers, rows


def column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha()).upper()
    result = 0
    for character in letters:
        result = result * 26 + ord(character) - ord("A") + 1
    return max(result - 1, 0)


def xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.text or "" for node in item.iter(f"{{{XLSX_MAIN}}}t")) for item in root.findall(f".//{{{XLSX_MAIN}}}si")]


def xlsx_sheets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relation_map = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall(f"{{{PKG_REL}}}Relationship")
    }
    sheets: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{XLSX_MAIN}}}sheet"):
        relation_id = sheet.attrib.get(f"{{{XLSX_REL}}}id")
        target = relation_map.get(relation_id or "")
        if not target:
            continue
        sheets[sheet.attrib["name"]] = posixpath.normpath(posixpath.join("xl", target))
    return sheets


def read_xlsx_table(path: Path, requested_sheet: str | None) -> tuple[str, list[str], list[tuple[int, dict[str, str]]], bool]:
    with zipfile.ZipFile(path) as archive:
        sheets = xlsx_sheets(archive)
        if not sheets:
            raise GateError(f"XLSX 没有可读取的工作表: {path.name}")
        sheet_name = requested_sheet or next(iter(sheets))
        sheet_path = sheets.get(sheet_name)
        if not sheet_path:
            raise GateError(f"找不到工作表 {requested_sheet!r}: {path.name}")

        root = ET.fromstring(archive.read(sheet_path))
        shared = xlsx_shared_strings(archive)
        raw_rows: list[tuple[int, dict[int, str]]] = []
        max_column = 0
        has_formula = False
        for row in root.findall(f".//{{{XLSX_MAIN}}}row"):
            row_number = int(row.attrib.get("r", len(raw_rows) + 1))
            values: dict[int, str] = {}
            for cell in row.findall(f"{{{XLSX_MAIN}}}c"):
                index = column_index(cell.attrib.get("r", "A1"))
                max_column = max(max_column, index)
                formula = cell.find(f"{{{XLSX_MAIN}}}f")
                if formula is not None:
                    has_formula = True
                    value = "[FORMULA]"
                else:
                    value_node = cell.find(f"{{{XLSX_MAIN}}}v")
                    value = value_node.text if value_node is not None and value_node.text else ""
                    if cell.attrib.get("t") == "s" and value:
                        value = shared[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter(f"{{{XLSX_MAIN}}}t"))
                values[index] = value
            raw_rows.append((row_number, values))

    if not raw_rows:
        return sheet_name, [], [], has_formula
    headers = [normal(raw_rows[0][1].get(index, "")) for index in range(max_column + 1)]
    rows = []
    for row_number, values in raw_rows[1:]:
        rows.append((row_number, {headers[index]: values.get(index, "") for index in range(len(headers)) if headers[index]}))
    return sheet_name, headers, rows, has_formula


def inspect_table(
    findings: list[dict[str, Any]],
    relative_path: str,
    headers: list[str],
    rows: list[tuple[int, dict[str, str]]],
    rule: dict[str, Any],
) -> None:
    header_map = {norm_header(header): header for header in headers if normal(header)}
    for required in rule.get("required_columns", []):
        if norm_header(required) not in header_map:
            findings.append(finding("FAIL", "COLUMN_MISSING", f"缺少列 {required!r}", relative_path))

    unique_key = rule.get("unique_key")
    if unique_key and norm_header(unique_key) in header_map:
        actual_key = header_map[norm_header(unique_key)]
        seen: dict[str, int] = {}
        for line_number, row in rows:
            value = normal(row.get(actual_key))
            if not value:
                findings.append(finding("FAIL", "KEY_EMPTY", f"主键 {unique_key!r} 为空", f"{relative_path}:line {line_number}"))
                continue
            if value in seen:
                findings.append(
                    finding(
                        "FAIL",
                        "KEY_DUPLICATE",
                        f"主键 {unique_key!r} 重复，首次出现于第 {seen[value]} 行",
                        f"{relative_path}:line {line_number}",
                    )
                )
            else:
                seen[value] = line_number


def inspect_cross_checks(
    findings: list[dict[str, Any]],
    checks: list[dict[str, Any]],
    tables: dict[str, tuple[list[str], list[tuple[int, dict[str, str]]], str]],
) -> None:
    for check in checks:
        check_type = normal(check.get("type"))
        if check_type == "key_set_equal":
            left = check.get("left") or {}
            right = check.get("right") or {}
            left_path = normal(left.get("path"))
            right_path = normal(right.get("path"))
            left_table = tables.get(left_path)
            right_table = tables.get(right_path)
            if not left_table or not right_table:
                missing = left_path if not left_table else right_path
                findings.append(finding("FAIL", "CROSS_TABLE_MISSING", "跨文件检查引用的表不存在", missing))
                continue

            left_headers, left_rows, left_location = left_table
            right_headers, right_rows, right_location = right_table
            left_key = normal(left.get("key"))
            right_key = normal(right.get("key") or left_key)
            left_map = {norm_header(header): header for header in left_headers if normal(header)}
            right_map = {norm_header(header): header for header in right_headers if normal(header)}
            if norm_header(left_key) not in left_map:
                findings.append(finding("FAIL", "CROSS_COLUMN_MISSING", f"左表缺少对账列 {left_key!r}", left_location))
                continue
            if norm_header(right_key) not in right_map:
                findings.append(finding("FAIL", "CROSS_COLUMN_MISSING", f"右表缺少对账列 {right_key!r}", right_location))
                continue

            left_actual = left_map[norm_header(left_key)]
            right_actual = right_map[norm_header(right_key)]
            left_values: dict[str, int] = {}
            right_values: dict[str, int] = {}
            for line_number, row in left_rows:
                value = normal(row.get(left_actual))
                if value and value not in left_values:
                    left_values[value] = line_number
            for line_number, row in right_rows:
                value = normal(row.get(right_actual))
                if value and value not in right_values:
                    right_values[value] = line_number

            for value in sorted(set(left_values) - set(right_values)):
                findings.append(
                    finding(
                        "FAIL",
                        "CROSS_KEY_MISSING_IN_RIGHT",
                        f"键 {value!r} 在左表存在，但右表不存在",
                        f"{left_location}:line {left_values[value]}",
                    )
                )
            for value in sorted(set(right_values) - set(left_values)):
                findings.append(
                    finding(
                        "FAIL",
                        "CROSS_KEY_MISSING_IN_LEFT",
                        f"键 {value!r} 在右表存在，但左表不存在",
                        f"{right_location}:line {right_values[value]}",
                    )
                )
        elif check_type == "row_count_matches":
            data_path = normal(check.get("data_path"))
            expected = check.get("expected") or {}
            expected_path = normal(expected.get("path"))
            data_table = tables.get(data_path)
            expected_table = tables.get(expected_path)
            if not data_table or not expected_table:
                missing = data_path if not data_table else expected_path
                findings.append(finding("FAIL", "CROSS_TABLE_MISSING", "行数检查引用的表不存在", missing))
                continue

            data_headers, data_rows, data_location = data_table
            expected_headers, expected_rows, expected_location = expected_table
            match_column = normal(expected.get("match_column"))
            match_value = normal(expected.get("match_value"))
            value_column = normal(expected.get("value_column"))
            expected_map = {norm_header(header): header for header in expected_headers if normal(header)}
            if norm_header(match_column) not in expected_map or norm_header(value_column) not in expected_map:
                findings.append(finding("FAIL", "CROSS_COLUMN_MISSING", "行数检查缺少匹配列或数值列", expected_location))
                continue

            match_actual = expected_map[norm_header(match_column)]
            value_actual = expected_map[norm_header(value_column)]
            matched = [
                (line_number, row)
                for line_number, row in expected_rows
                if normal(row.get(match_actual)) == match_value
            ]
            if not matched:
                findings.append(
                    finding(
                        "FAIL",
                        "CROSS_EXPECTATION_MISSING",
                        f"找不到 {match_column!r}={match_value!r} 对应的期望行数",
                        expected_location,
                    )
                )
                continue

            expected_line, expected_row = matched[0]
            try:
                expected_count = int(normal(expected_row.get(value_actual)))
            except ValueError:
                findings.append(
                    finding(
                        "FAIL",
                        "CROSS_COUNT_NOT_NUMERIC",
                        f"期望行数不是整数：{expected_row.get(value_actual)!r}",
                        f"{expected_location}:line {expected_line}",
                    )
                )
                continue

            actual_count = len(data_rows)
            if actual_count != expected_count:
                findings.append(
                    finding(
                        "FAIL",
                        "ROW_COUNT_MISMATCH",
                        f"实际数据行数为 {actual_count}，期望为 {expected_count}",
                        f"{data_location} 与 {expected_location}:line {expected_line}",
                    )
                )
        else:
            raise GateError(f"不支持的 cross_checks.type: {check_type!r}")


def inspect_package(root: Path, manifest: dict[str, Any], source: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    package_config = manifest.get("package") or {}
    file_rules = manifest.get("files") or []
    if not isinstance(file_rules, list) or not file_rules:
        raise GateError("manifest.files 必须是非空数组")

    required_tokens = package_config.get("filename_tokens")
    if required_tokens is None:
        required_tokens = [package_config.get(key) for key in ("customer", "period", "version") if package_config.get(key)]

    visible_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {".DS_Store"} and "__MACOSX" not in path.parts
    )
    configured_paths = set()
    tables: dict[str, tuple[list[str], list[tuple[int, dict[str, str]]], str]] = {}

    for rule in file_rules:
        relative_path = normal(rule.get("path"))
        if not relative_path:
            raise GateError("每个 manifest.files 项都需要 path")
        configured_paths.add(relative_path)
        path = root / relative_path
        if not path.is_file():
            findings.append(finding("FAIL", "FILE_MISSING", "必需文件不存在", relative_path))
            continue

        filename = path.name.casefold()
        for token in required_tokens:
            if normal(token).casefold() not in filename:
                findings.append(finding("FAIL", "IDENTITY_TOKEN_MISSING", f"文件名缺少身份标记 {token!r}", relative_path))

        kind = normal(rule.get("kind") or path.suffix.lstrip(".")).casefold()
        if kind == "csv":
            headers, rows = read_csv_table(path)
            inspect_table(findings, relative_path, headers, rows, rule)
            tables[relative_path] = (headers, rows, relative_path)
        elif kind == "xlsx":
            try:
                sheet_name, headers, rows, has_formula = read_xlsx_table(path, rule.get("sheet"))
            except (KeyError, ET.ParseError, ValueError, zipfile.BadZipFile, GateError) as error:
                findings.append(finding("FAIL", "XLSX_READ_ERROR", str(error), relative_path))
                continue
            inspect_table(findings, f"{relative_path}#sheet={sheet_name}", headers, rows, rule)
            tables[relative_path] = (headers, rows, f"{relative_path}#sheet={sheet_name}")
            if has_formula:
                findings.append(finding("REVIEW", "FORMULA_NOT_EVALUATED", "发现公式；HandoffSeal 不重算公式，请人工复核", relative_path))

    cross_checks = manifest.get("cross_checks") or []
    if not isinstance(cross_checks, list):
        raise GateError("manifest.cross_checks 必须是数组")
    inspect_cross_checks(findings, cross_checks, tables)

    for extra in visible_files:
        if extra not in configured_paths:
            findings.append(finding("REVIEW", "UNLISTED_FILE", "文件未列入 manifest，请确认是否应随包交付", extra))

    status = "FAIL" if any(item["severity"] == "FAIL" for item in findings) else "REVIEW" if findings else "PASS"
    return {
        "tool": "HandoffSeal",
        "version": VERSION,
        "source": source,
        "status": status,
        "passed": status == "PASS",
        "summary": {
            "failures": sum(item["severity"] == "FAIL" for item in findings),
            "reviews": sum(item["severity"] == "REVIEW" for item in findings),
            "files_seen": len(visible_files),
            "files_declared": len(configured_paths),
        },
        "package_sha256": package_sha256(root),
        "files": [
            {"path": relative, "bytes": (root / relative).stat().st_size, "sha256": file_sha256(root / relative)}
            for relative in visible_files
        ],
        "findings": findings,
    }


def render_report(evidence: dict[str, Any]) -> str:
    status = evidence["status"]
    colors = {"PASS": "#176b45", "FAIL": "#a52727", "REVIEW": "#8a5a00"}
    rows = []
    for item in evidence["findings"]:
        rows.append(
            "<tr>"
            f"<td><span class='badge {html.escape(item['severity'])}'>{html.escape(item['severity'])}</span></td>"
            f"<td>{html.escape(item['code'])}</td>"
            f"<td>{html.escape(item['message'])}</td>"
            f"<td>{html.escape(item.get('location', ''))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append("<tr><td colspan='4'>没有发现问题。</td></tr>")
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>HandoffSeal report</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#1f2937;background:#fafafa}}
header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ddd;padding-bottom:18px}}
h1{{margin:0;font-size:28px}} .status{{font-size:22px;font-weight:700;color:{colors[status]}}}
.meta{{color:#6b7280;font-size:13px;margin:18px 0}} table{{width:100%;border-collapse:collapse;background:white}}
th,td{{padding:11px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:top}} th{{background:#f3f4f6}}
.badge{{font-weight:700;font-size:12px;padding:3px 7px;border-radius:999px}} .FAIL{{background:#fee2e2;color:#991b1b}} .REVIEW{{background:#fef3c7;color:#92400e}} .PASS{{background:#dcfce7;color:#166534}}
.note{{background:#fff;border:1px solid #e5e7eb;padding:14px;border-radius:8px;line-height:1.6}}
</style></head><body>
<header><h1>HandoffSeal</h1><div class="status">{html.escape(status)}</div></header>
<div class="meta">输入：{html.escape(evidence['source'])} · 文件：{evidence['summary']['files_seen']} · SHA-256：{evidence['package_sha256'][:16]}…</div>
<div class="note">本报告只验证交付包的身份、结构和可复核的一致性，不判断业务数据是否正确，也不证明客户系统已经接收文件。</div>
<h2>发现</h2><table><thead><tr><th>级别</th><th>代码</th><th>说明</th><th>位置</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""


def run_check(manifest_path: Path, package_path: Path, output_dir: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GateError(f"无法读取 manifest JSON: {error}") from error
    output_dir.mkdir(parents=True, exist_ok=True)
    with package_root(package_path) as root:
        evidence = inspect_package(root, manifest, str(package_path))
    (output_dir / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "report.html").write_text(render_report(evidence), encoding="utf-8")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="HandoffSeal local delivery-package gate")
    parser.add_argument("--manifest", required=True, type=Path, help="规则 JSON")
    parser.add_argument("--package", required=True, type=Path, help="交付目录或 ZIP")
    parser.add_argument("--output", required=True, type=Path, help="证据输出目录")
    args = parser.parse_args()
    try:
        evidence = run_check(args.manifest, args.package, args.output)
    except GateError as error:
        print(f"ERROR: {error}")
        return 2
    print(f"{evidence['status']}: {args.output / 'report.html'}")
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
