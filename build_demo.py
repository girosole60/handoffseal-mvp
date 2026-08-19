#!/usr/bin/env python3
from pathlib import Path
import csv
import zipfile


ROOT = Path(__file__).resolve().parent


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def build(name: str, broken: bool) -> None:
    source = ROOT / f"demo-{name}"
    source.mkdir(exist_ok=True)
    prefix = "ACME_2026-08_v1"
    summary_rows = [["orders", "2"], ["amount", "180"], ["detail_rows", "3" if broken else "2"]]
    write_csv(source / f"{prefix}_summary.csv", ["metric", "value"], summary_rows)
    if broken:
        write_csv(source / f"{prefix}_detail.csv", ["record_id", "amount"], [["R-001", "100"], ["R-001", "80"]])
        write_csv(source / f"{prefix}_expected.csv", ["record_id", "label"], [["R-002", "ok"], ["R-003", "ok"]])
        (source / "ACME_2026-08_v1_README.txt").write_text("broken demo", encoding="utf-8")
        (source / "ACME_2026-07_v1_old.csv").write_text("record_id,amount\nR-OLD,1\n", encoding="utf-8")
    else:
        write_csv(source / f"{prefix}_detail.csv", ["record_id", "amount"], [["R-001", "100"], ["R-002", "80"]])
        write_csv(source / f"{prefix}_expected.csv", ["record_id", "label"], [["R-001", "ok"], ["R-002", "ok"]])
        (source / f"{prefix}_README.txt").write_text("pass demo", encoding="utf-8")

    archive_path = ROOT / f"demo-{name}.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.iterdir()):
            archive.write(path, path.name)


if __name__ == "__main__":
    build("pass", broken=False)
    build("fail", broken=True)
    print("created demo-pass.zip and demo-fail.zip")
