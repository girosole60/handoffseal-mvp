import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from handoff_seal import inspect_package, run_check


MANIFEST = {
    "package": {"filename_tokens": ["ACME", "2026-08", "v1"]},
    "files": [
        {"path": "ACME_2026-08_v1_summary.csv", "kind": "csv", "required_columns": ["metric", "value"], "unique_key": "metric"},
        {"path": "ACME_2026-08_v1_detail.csv", "kind": "csv", "required_columns": ["record_id", "amount"], "unique_key": "record_id"},
    ],
}


def write_minimal_xlsx(path: Path) -> None:
    workbook = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Summary" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
        '</Relationships>'
    )
    sheet = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        '<row r="1"><c r="A1" t="inlineStr"><is><t>record_id</t></is></c>'
        '<c r="B1" t="inlineStr"><is><t>value</t></is></c></row>'
        '<row r="2"><c r="A2" t="inlineStr"><is><t>R-001</t></is></c>'
        '<c r="B2"><v>100</v></c></row></sheetData></worksheet>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


class HandoffSealTests(unittest.TestCase):
    def test_passes_clean_zip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ACME_2026-08_v1_summary.csv").write_text("metric,value\norders,2\n", encoding="utf-8")
            (root / "ACME_2026-08_v1_detail.csv").write_text("record_id,amount\nR-001,100\nR-002,80\n", encoding="utf-8")
            archive = root / "delivery.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                for file in root.glob("*.csv"):
                    zipped.write(file, file.name)
            output = root / "evidence"
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
            evidence = run_check(manifest, archive, output)
            self.assertEqual(evidence["status"], "PASS")
            self.assertTrue((output / "report.html").is_file())

    def test_finds_identity_column_and_duplicate_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ACME_2026-08_v1_summary.csv").write_text("metric,value\norders,2\n", encoding="utf-8")
            (root / "ACME_2026-08_v1_detail.csv").write_text("record_id,wrong\nR-001,100\nR-001,80\n", encoding="utf-8")
            evidence = inspect_package(root, MANIFEST, str(root))
            codes = {item["code"] for item in evidence["findings"]}
            self.assertEqual(evidence["status"], "FAIL")
            self.assertIn("COLUMN_MISSING", codes)
            self.assertIn("KEY_DUPLICATE", codes)

    def test_rejects_zip_slip_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as zipped:
                zipped.writestr("../outside.txt", "unsafe")
            output = root / "evidence"
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
            with self.assertRaises(Exception):
                run_check(manifest, archive, output)

    def test_reads_xlsx_headers_and_unique_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workbook = root / "ACME_2026-08_v1_data.xlsx"
            write_minimal_xlsx(workbook)
            manifest = {
                "package": {"filename_tokens": ["ACME", "2026-08", "v1"]},
                "files": [
                    {
                        "path": workbook.name,
                        "kind": "xlsx",
                        "sheet": "Summary",
                        "required_columns": ["record_id", "value"],
                        "unique_key": "record_id",
                    }
                ],
            }
            evidence = inspect_package(root, manifest, str(root))
            self.assertEqual(evidence["status"], "PASS")

    def test_cross_file_key_and_count_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "ACME_2026-08_v1_summary.csv").write_text(
                "metric,value\norders,2\ndetail_rows,3\n", encoding="utf-8"
            )
            (root / "ACME_2026-08_v1_detail.csv").write_text(
                "record_id,amount\nR-001,100\nR-002,80\n", encoding="utf-8"
            )
            (root / "ACME_2026-08_v1_expected.csv").write_text(
                "record_id,label\nR-001,ok\nR-003,ok\n", encoding="utf-8"
            )
            manifest = {
                "package": {"filename_tokens": ["ACME", "2026-08", "v1"]},
                "files": [
                    {"path": "ACME_2026-08_v1_summary.csv", "kind": "csv", "required_columns": ["metric", "value"]},
                    {"path": "ACME_2026-08_v1_detail.csv", "kind": "csv", "required_columns": ["record_id", "amount"]},
                    {"path": "ACME_2026-08_v1_expected.csv", "kind": "csv", "required_columns": ["record_id", "label"]},
                ],
                "cross_checks": [
                    {
                        "type": "key_set_equal",
                        "left": {"path": "ACME_2026-08_v1_detail.csv", "key": "record_id"},
                        "right": {"path": "ACME_2026-08_v1_expected.csv", "key": "record_id"},
                    },
                    {
                        "type": "row_count_matches",
                        "data_path": "ACME_2026-08_v1_detail.csv",
                        "expected": {
                            "path": "ACME_2026-08_v1_summary.csv",
                            "match_column": "metric",
                            "match_value": "detail_rows",
                            "value_column": "value",
                        },
                    },
                ],
            }
            evidence = inspect_package(root, manifest, str(root))
            codes = {item["code"] for item in evidence["findings"]}
            self.assertEqual(evidence["status"], "FAIL")
            self.assertIn("CROSS_KEY_MISSING_IN_RIGHT", codes)
            self.assertIn("CROSS_KEY_MISSING_IN_LEFT", codes)
            self.assertIn("ROW_COUNT_MISMATCH", codes)


if __name__ == "__main__":
    unittest.main()
