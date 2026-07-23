#!/usr/bin/env python3
"""Build Open Infrastructure Map vector DB for Italy."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PBF = DATA / "italy-latest.osm.pbf"
PBF_URL = "https://download.geofabrik.de/europe/italy-latest.osm.pbf"


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, **kw)


def wait_docker(timeout: int = 180) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            subprocess.check_call(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Docker ready")
            return
        except subprocess.CalledProcessError:
            time.sleep(3)
    raise SystemExit("Docker non pronto entro il timeout. Avvia Docker Desktop e riprova.")


def download_pbf() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if PBF.exists() and PBF.stat().st_size > 500_000_000:
        print(f"PBF già presente: {PBF} ({PBF.stat().st_size // 1_000_000} MB)")
        return
    print(f"Download {PBF_URL} ...")
    # curl resume-friendly
    run(
        [
            "curl",
            "-L",
            "--retry",
            "5",
            "--retry-all-errors",
            "-C",
            "-",
            "-o",
            str(PBF),
            PBF_URL,
        ]
    )
    print(f"Download OK: {PBF.stat().st_size // 1_000_000} MB")


def compose(*args: str) -> list[str]:
    return ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), *args]


def main() -> None:
    os.chdir(ROOT)
    wait_docker()
    download_pbf()

    run(compose("up", "-d", "postgis"))
    print("Attendo PostGIS healthy...")
    for _ in range(60):
        try:
            out = subprocess.check_output(
                compose("ps", "--format", "json", "postgis"),
                text=True,
            )
            if "healthy" in out.lower() or '"Health":"healthy"' in out:
                break
        except subprocess.CalledProcessError:
            pass
        # fallback pg_isready
        try:
            subprocess.check_call(
                compose("exec", "-T", "postgis", "pg_isready", "-U", "oim", "-d", "oim_italia"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            break
        except subprocess.CalledProcessError:
            time.sleep(3)
    else:
        raise SystemExit("PostGIS non diventa ready")

    run(compose("exec", "-T", "postgis", "psql", "-U", "oim", "-d", "oim_italia", "-f", "/sql/01_schema.sql"))

    print("Import osm2pgsql (Italia intera — può richiedere 30-90+ min)...")
    env = os.environ.copy()
    env["PGPASSWORD"] = "oim"
    run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "container:oim-italia-db",
            "-e",
            "PGPASSWORD=oim",
            "-v",
            f"{DATA}:/data:ro",
            "-v",
            f"{ROOT / 'lua'}:/lua:ro",
            "iboates/osm2pgsql:2.0.1",
            "osm2pgsql",
            "-d",
            "oim_italia",
            "-U",
            "oim",
            "-H",
            "127.0.0.1",
            "-P",
            "5432",
            "--create",
            "--output=flex",
            "--style=/lua/oim_italia.lua",
            "--slim",
            "--drop",
            "-C",
            "4000",
            "/data/italy-latest.osm.pbf",
        ],
        env=env,
    )

    print("Carico legenda 10+75...")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "gen_legend_sql.py")])
    run(compose("exec", "-T", "postgis", "psql", "-U", "oim", "-d", "oim_italia", "-v", "ON_ERROR_STOP=1", "-f", "/sql/02_legend.sql"))

    print("Classificazione 75 voci...")
    run(compose("exec", "-T", "postgis", "psql", "-U", "oim", "-d", "oim_italia", "-v", "ON_ERROR_STOP=1", "-f", "/sql/03_classify.sql"))

    run(
        compose(
            "exec",
            "-T",
            "postgis",
            "psql",
            "-U",
            "oim",
            "-d",
            "oim_italia",
            "-c",
            "SELECT category_id, count(*) FROM oim_feature GROUP BY 1 ORDER BY 1;"
            "SELECT count(*) AS totale FROM oim_feature;"
            "SELECT voce_id, count(*) FROM oim_feature GROUP BY 1 ORDER BY 2 DESC LIMIT 20;",
        )
    )
    print("DONE. DB: localhost:5433 / oim_italia / user=oim / pass=oim")


if __name__ == "__main__":
    main()
