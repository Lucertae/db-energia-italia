#!/usr/bin/env python3
"""Populate sslm_start_m / sslm_end_m via Open-Elevation DEM API."""
from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml")]
BATCH = 2000
API = "https://api.open-elevation.com/api/v1/lookup"
SENTINEL = -999999.0


def psql(sql: str, tuples: bool = False) -> str:
    cmd = COMPOSE + [
        "exec",
        "-T",
        "postgis",
        "psql",
        "-U",
        "oim",
        "-d",
        "oim_italia",
        "-v",
        "ON_ERROR_STOP=1",
        "-t" if tuples else "-q",
        "-A",
        "-c",
        sql,
    ]
    return subprocess.check_output(cmd, text=True)


def psql_file(path: Path) -> None:
    subprocess.check_call(
        COMPOSE
        + [
            "exec",
            "-T",
            "postgis",
            "psql",
            "-U",
            "oim",
            "-d",
            "oim_italia",
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            f"/sql/{path.name}",
        ]
    )


def fetch_elevations(pairs: list[tuple[float, float]]) -> list[float | None]:
    """pairs = [(lon, lat), ...]"""
    payload = {
        "locations": [{"longitude": lon, "latitude": lat} for lon, lat in pairs]
    }
    body = json.dumps(payload).encode()
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            req = urllib.request.Request(
                API,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "oim-italia-sslm/1.0",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode())
            results = data.get("results") or []
            if len(results) != len(pairs):
                raise RuntimeError(f"size mismatch {len(results)} != {len(pairs)}")
            out: list[float | None] = []
            for r in results:
                elev = r.get("elevation")
                out.append(None if elev is None else float(elev))
            return out
        except Exception as e:
            last_err = e
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"elevation API failed: {last_err}")


def main() -> None:
    psql_file(ROOT / "sql" / "05_sslm_columns.sql")

    psql(
        """
        INSERT INTO elevation_cache(lon_r, lat_r)
        SELECT DISTINCT round(lon_start::numeric, 4), round(lat_start::numeric, 4)
        FROM oim_feature
        WHERE lon_start IS NOT NULL AND lat_start IS NOT NULL
        ON CONFLICT DO NOTHING;
        INSERT INTO elevation_cache(lon_r, lat_r)
        SELECT DISTINCT round(lon_end::numeric, 4), round(lat_end::numeric, 4)
        FROM oim_feature
        WHERE lon_end IS NOT NULL AND lat_end IS NOT NULL
        ON CONFLICT DO NOTHING;
        """
    )

    pending = int(
        psql(
            "SELECT count(*) FROM elevation_cache WHERE elevation_m IS NULL;",
            tuples=True,
        ).strip()
        or "0"
    )
    print(f"Punti DEM da risolvere: {pending}", flush=True)

    done = 0
    t0 = time.time()
    while True:
        rows = psql(
            f"""
            SELECT lon_r::text || ' ' || lat_r::text
            FROM elevation_cache
            WHERE elevation_m IS NULL
            ORDER BY lat_r, lon_r
            LIMIT {BATCH};
            """,
            tuples=True,
        ).strip()
        if not rows:
            break
        pairs = []
        for line in rows.splitlines():
            lon_s, lat_s = line.split()
            pairs.append((float(lon_s), float(lat_s)))

        elevs = fetch_elevations(pairs)
        values = []
        for (lon, lat), elev in zip(pairs, elevs):
            elev_sql = str(SENTINEL if elev is None else float(elev))
            values.append(f"({lon:.4f}::numeric,{lat:.4f}::numeric,{elev_sql}::float8)")

        # chunk updates to keep SQL manageable
        chunk = 500
        for i in range(0, len(values), chunk):
            part = values[i : i + chunk]
            psql(
                "UPDATE elevation_cache AS c SET elevation_m = v.elevation_m "
                "FROM (VALUES "
                + ",".join(part)
                + ") AS v(lon_r, lat_r, elevation_m) "
                "WHERE c.lon_r = v.lon_r AND c.lat_r = v.lat_r;"
            )

        done += len(pairs)
        left = max(pending - done, 0)
        rate = done / max(time.time() - t0, 1)
        eta = (pending - done) / max(rate, 1)
        print(
            f"progress: {done}/{pending} ({100*done/pending:.1f}%) "
            f"rate={rate:.0f} pt/s eta~{eta/60:.1f} min",
            flush=True,
        )
        time.sleep(0.2)

    print("Aggiorno oim_feature...", flush=True)
    out = psql(
        f"""
        UPDATE oim_feature f
        SET sslm_start_m = CASE WHEN s.elevation_m <= {SENTINEL+1} THEN NULL ELSE s.elevation_m END
        FROM elevation_cache s
        WHERE s.lon_r = round(f.lon_start::numeric, 4)
          AND s.lat_r = round(f.lat_start::numeric, 4);

        UPDATE oim_feature f
        SET sslm_end_m = CASE WHEN e.elevation_m <= {SENTINEL+1} THEN NULL ELSE e.elevation_m END
        FROM elevation_cache e
        WHERE e.lon_r = round(f.lon_end::numeric, 4)
          AND e.lat_r = round(f.lat_end::numeric, 4);

        INSERT INTO meta(key, value) VALUES
          ('sslm_at', now()::text),
          ('sslm_features', (SELECT count(*)::text FROM oim_feature WHERE sslm_start_m IS NOT NULL))
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

        SELECT
          count(*) AS totale,
          count(sslm_start_m) AS con_sslm_start,
          count(sslm_end_m) AS con_sslm_end,
          round(avg(sslm_start_m)::numeric, 1) AS media_start_m
        FROM oim_feature;
        """
    )
    print(out, flush=True)
    print("DONE sslm", flush=True)


if __name__ == "__main__":
    main()
