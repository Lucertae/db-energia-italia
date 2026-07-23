"""FX rate graph + Bellman-Ford negative cycle detection in -log space."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT, build_eur_cross_rates, load_fx_manifest


def _build_edges(rates: dict[str, float], fee: float) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    currencies = sorted(rates.keys())
    for base in currencies:
        for quote in currencies:
            if base == quote:
                continue
            rb = rates.get(base)
            rq = rates.get(quote)
            if not rb or not rq or rb <= 0 or rq <= 0:
                continue
            # Convert EUR-base quotes to cross: 1 BASE -> QUOTE
            if base == "EUR":
                cross = rq
            elif quote == "EUR":
                cross = 1.0 / rb
            else:
                cross = rq / rb
            eff = cross * (1.0 - fee)
            if eff <= 0:
                continue
            w = -math.log(eff)
            edges.append({
                "from": base,
                "to": quote,
                "rate": round(cross, 8),
                "weight": round(w, 8),
            })
    return edges


def _bellman_ford(
    nodes: list[str], edges: list[dict[str, Any]], source: str
) -> tuple[dict[str, float], dict[str, str | None], str | None]:
    dist: dict[str, float] = {n: float("inf") for n in nodes}
    prev: dict[str, str | None] = {n: None for n in nodes}
    dist[source] = 0.0

    for _ in range(len(nodes) - 1):
        updated = False
        for e in edges:
            u, v, w = e["from"], e["to"], e["weight"]
            if dist[u] + w < dist[v] - 1e-12:
                dist[v] = dist[u] + w
                prev[v] = u
                updated = True
        if not updated:
            break

    cycle_node: str | None = None
    for e in edges:
        u, v, w = e["from"], e["to"], e["weight"]
        if dist[u] + w < dist[v] - 1e-12:
            cycle_node = v
            break

    return dist, prev, cycle_node


def _extract_cycle(prev: dict[str, str | None], start: str) -> list[str]:
    # Walk back len(nodes) steps to guarantee we're inside the cycle
    node = start
    for _ in range(len(prev)):
        nxt = prev.get(node)
        if nxt is None:
            return []
        node = nxt

    cycle: list[str] = [node]
    cur = prev[node]
    while cur is not None and cur != node:
        cycle.append(cur)
        cur = prev[cur]
    cycle.reverse()
    return cycle


def _cycle_profit(cycle: list[str], rates: dict[str, float], fee: float) -> float | None:
    if len(cycle) < 2:
        return None
    prod = 1.0
    for i, base in enumerate(cycle):
        quote = cycle[(i + 1) % len(cycle)]
        rb, rq = rates.get(base), rates.get(quote)
        if not rb or not rq:
            return None
        if base == "EUR":
            cross = rq
        elif quote == "EUR":
            cross = 1.0 / rb
        else:
            cross = rq / rb
        prod *= cross * (1.0 - fee)
    return prod


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_fx_manifest(base)
    fee = float(manifest.get("fee_bps", 2)) / 10000.0
    rates = build_eur_cross_rates(base)

    if len(rates) < 3:
        out = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ok": False,
            "message": "insufficient FX rates",
            "rates": rates,
            "cycles": [],
        }
        out_path = base / "cache" / "spine" / "modules" / "fx_graph.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        return {
            "ok": False,
            "module": "fx_graph",
            "message": out["message"],
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    nodes = sorted(rates.keys())
    edges = _build_edges(rates, fee)
    cycles: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()

    for src in nodes:
        _, prev, cyc = _bellman_ford(nodes, edges, src)
        if not cyc:
            continue
        cycle = _extract_cycle(prev, cyc)
        if len(cycle) < 3:
            continue
        key = tuple(sorted(cycle))
        if key in seen:
            continue
        seen.add(key)
        profit = _cycle_profit(cycle, rates, fee)
        if profit is None:
            continue
        cycles.append({
            "nodes": cycle,
            "profit_mult": round(profit, 8),
            "profit_bps": round((profit - 1.0) * 10000.0, 2),
            "actionable": profit > 1.0001,
        })

    cycles.sort(key=lambda c: c["profit_mult"], reverse=True)

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hub": manifest.get("hub", "EUR"),
        "fee_bps": manifest.get("fee_bps", 2),
        "nodes": nodes,
        "edge_count": len(edges),
        "rates_eur_base": {k: round(v, 6) for k, v in rates.items()},
        "cycles": cycles[:12],
        "note": "Negative cycle in -log space => profit_mult > 1. Daily ref rates; not executable arb.",
    }

    out_path = base / "cache" / "spine" / "modules" / "fx_graph.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    top = cycles[0]["profit_bps"] if cycles else 0.0
    return {
        "ok": True,
        "module": "fx_graph",
        "message": f"{len(nodes)} ccys {len(cycles)} cycles top={top:+.1f}bp",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
