"""Export TXT / CSV / JSON."""
from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from models import Company


def write_outputs(companies: list[Company], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = output_dir / "aziende_energia_crisi.txt"
    csv_path = output_dir / "aziende_energia_crisi.csv"
    json_path = output_dir / "aziende_energia_crisi.json"

    by_fonte = Counter()
    by_stato = Counter()
    for c in companies:
        for f in (c.fonte or "").split("|"):
            if f:
                by_fonte[f.strip()] += 1
        by_stato[c.stato or "(vuoto)"] += 1

    header_lines = [
        f"# Run: {datetime.now().isoformat(timespec='seconds')}",
        f"# Totale aziende: {len(companies)}",
        f"# Per fonte: {dict(by_fonte)}",
        f"# Per stato: {dict(by_stato)}",
        "# Formato: RAGIONE SOCIALE | P.IVA/CF | ATECO | PROVINCIA | STATO | FONTE | NOTE",
        "#" + "=" * 78,
    ]

    lines = list(header_lines)
    for c in companies:
        id_code = c.piva or c.cf or ""
        row = " | ".join(
            [
                (c.denominazione or "").replace("|", "/"),
                id_code,
                c.ateco or "",
                c.provincia or "",
                c.stato or "",
                c.fonte or "",
                (c.note or "").replace("|", "/").replace("\n", " "),
            ]
        )
        lines.append(row)
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fieldnames = [
        "denominazione",
        "piva",
        "cf",
        "ateco",
        "provincia",
        "stato",
        "fonte",
        "url",
        "note",
        "data_rilevazione",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for c in companies:
            writer.writerow(c.to_dict())

    json_path.write_text(
        json.dumps([c.to_dict() for c in companies], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"txt": txt_path, "csv": csv_path, "json": json_path}
