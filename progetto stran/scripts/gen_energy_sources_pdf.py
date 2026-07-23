#!/usr/bin/env python3
"""PDF A4 portrait — Parte I catalogo, Parte II schede vincoli per fonte."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
DATA = ROOT / "data" / "energy_production_sources.json"
OPERATIONAL = ROOT / "data" / "energy_operational_profile.json"
STORAGE_DATA = ROOT / "data" / "energy_storage_accumulo.json"
COOPERATION_DATA = ROOT / "data" / "energy_cooperation.json"
MAINTENANCE_DATA = ROOT / "data" / "energy_appendix_maintenance.json"
REDISTRIBUTION_DATA = ROOT / "data" / "energy_redistribution.json"
REDISTRIBUTION_OVERLAY = ROOT / "data" / "energy_redistribution_overlay.json"
CONSUMPTION_DATA = ROOT / "data" / "energy_consumption.json"
OVERVIEW_DATA = ROOT / "data" / "energy_system_overview.json"
OUT = WORKSPACE / "fonti-produzione-energetica.pdf"

sys.path.insert(0, str(ROOT / "data"))
from energy_constraints_data import CONSTRAINTS  # noqa: E402

PALETTE = {
    "fossil": {"accent": "#8B3A2A", "fill": "#FAF6F4", "line": "#E8D0C8", "tag": "#F3E8E4"},
    "renewable": {"accent": "#1F6B45", "fill": "#F0F8F3", "line": "#C2DECC", "tag": "#E2F0E8"},
    "nuclear": {"accent": "#2F4A9A", "fill": "#F0F3FA", "line": "#C5D0EA", "tag": "#E0E8F6"},
    "other": {"accent": "#5A6472", "fill": "#F5F6F8", "line": "#D5DAE2", "tag": "#ECEEF2"},
}

APPENDIX_PALETTE = {
    "storage": {"accent": "#6B4C9A", "fill": "#F6F3FA", "line": "#D8CCE8"},
    "cooperation": {"accent": "#2E6B7A", "fill": "#F0F6F8", "line": "#C5D8DE"},
    "redistribution": {"accent": "#B45309", "fill": "#FFF7ED", "line": "#FED7AA"},
    "consumption": {"accent": "#047857", "fill": "#ECFDF5", "line": "#A7F3D0"},
}

GROUP_ORDER = ["fossil", "renewable", "nuclear", "other"]
LEFT_GROUPS = ["fossil", "other"]
RIGHT_GROUPS = ["renewable", "nuclear"]

SUBGROUP_LABELS = {
    "coal": "Carbone e torba",
    "oil": "Petrolio",
    "gas": "Gas naturale e derivati",
    "hydrogen_fossil": "Idrogeno (fossile)",
    "solar": "Solare",
    "wind": "Eolico",
    "hydro": "Idroelettrico",
    "geothermal": "Geotermico",
    "biomass": "Biomassa e biocarburanti",
    "marine": "Energia marina",
    "hydrogen_renewable": "Idrogeno (rinnovabile)",
    "nuclear": "Nucleare",
    "carriers": "Vettori e combustibili sintetici",
    "recovery": "Recupero termico",
}

SUBGROUP_ORDER = {
    "fossil": ["coal", "oil", "gas", "hydrogen_fossil"],
    "renewable": ["solar", "wind", "hydro", "geothermal", "biomass", "marine", "hydrogen_renewable"],
    "nuclear": ["nuclear"],
    "other": ["carriers", "recovery"],
}

CONSTRAINT_DIMS = [
    ("meteo", "M", "Dipendenze meteo", "#1a5f8a"),
    ("legal", "L", "Vincoli legali", "#6b3a10"),
    ("ops", "G", "Manutenzione e gestione", "#3d4a3a"),
]

MARGIN_L = 2.0 * cm
MARGIN_R = 2.0 * cm
MARGIN_T = 1.7 * cm
MARGIN_B = 1.7 * cm

# Helvetica non supporta Unicode (₂, °, —, × …) → quadratini nel PDF
_UNICODE_MAP = str.maketrans({
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
    "\u00b0": " gr", "\u00b7": " - ", "\u2212": "-", "\u00d7": "x",
    "\u2013": "-", "\u2014": "-", "\u2192": "->", "\u25a0": "*",
    "\u2219": "-", "\u2022": "-",
})


def sanitize(text: str) -> str:
    return text.translate(_UNICODE_MAP)

# page registry filled during build for TOC
PAGE_MAP: dict[str, int] = {}


def load_catalog() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def load_operational() -> dict:
    return json.loads(OPERATIONAL.read_text(encoding="utf-8"))


def load_storage() -> dict:
    return json.loads(STORAGE_DATA.read_text(encoding="utf-8"))


def load_cooperation() -> dict:
    return json.loads(COOPERATION_DATA.read_text(encoding="utf-8"))


def load_appendix_maintenance() -> dict:
    return json.loads(MAINTENANCE_DATA.read_text(encoding="utf-8"))


def load_redistribution() -> dict:
    return json.loads(REDISTRIBUTION_DATA.read_text(encoding="utf-8"))


def load_redistribution_overlay() -> dict:
    return json.loads(REDISTRIBUTION_OVERLAY.read_text(encoding="utf-8"))


def load_consumption() -> dict:
    return json.loads(CONSUMPTION_DATA.read_text(encoding="utf-8"))


def load_overview() -> dict:
    return json.loads(OVERVIEW_DATA.read_text(encoding="utf-8"))


def merge_maintenance(data: dict, maintenance: dict, section: str) -> dict:
    """Arricchisce items con campi manutenzione dedicati."""
    lookup = maintenance.get(section, {})
    out = dict(data)
    items = []
    for item in data["items"]:
        m = lookup.get(item["id"], {})
        enriched = dict(item)
        if m:
            enriched["maintenance"] = m.get("maintenance", item.get("ops", "-"))
            enriched["maintenance_cadence"] = m.get("cadence", "")
            enriched["if_neglected"] = m.get("if_neglected", "")
        else:
            enriched["maintenance"] = item.get("maintenance", item.get("ops", "-"))
        items.append(enriched)
    out["items"] = items
    return out


def merge_item_overlay(data: dict, overlay: dict) -> dict:
    """Applica campi aggiuntivi (es. M/L/G) per id."""
    out = dict(data)
    items = []
    for item in data["items"]:
        enriched = dict(item)
        if item["id"] in overlay:
            enriched.update(overlay[item["id"]])
        items.append(enriched)
    out["items"] = items
    return out


def subgroup_for(source: dict) -> str:
    sid = source["id"]
    if sid.startswith("coal_") or sid == "peat":
        return "coal"
    if sid.startswith("oil_"):
        return "oil"
    if sid in {
        "natural_gas", "shale_gas", "tight_gas", "associated_gas",
        "coalbed_methane", "lng", "lpg", "gas_hydrates",
    }:
        return "gas"
    if sid in {"hydrogen_blue", "hydrogen_grey", "hydrogen_turquoise"}:
        return "hydrogen_fossil"
    if sid.startswith("solar_"):
        return "solar"
    if sid.startswith("wind_"):
        return "wind"
    if sid.startswith("hydro_"):
        return "hydro"
    if sid.startswith("geothermal"):
        return "geothermal"
    if sid.startswith("marine_"):
        return "marine"
    if sid == "hydrogen_green":
        return "hydrogen_renewable"
    if sid.startswith("nuclear_") or sid == "hydrogen_pink":
        return "nuclear"
    if sid in {"waste_heat", "ambient_heat"}:
        return "recovery"
    return "biomass" if source["group"] == "renewable" else "carriers"


def group_sources(sources: list[dict]) -> dict[str, dict[str, list[dict]]]:
    tree: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for src in sources:
        tree[src.get("group", "other")][subgroup_for(src)].append(src)
    return tree


_style_seq = 0


def sty(name: str, *, size: float, color: str = "#1a1a1a", bold: bool = False, align=TA_LEFT, leading: float | None = None) -> ParagraphStyle:
    global _style_seq
    _style_seq += 1
    return ParagraphStyle(
        name=f"{name}_{_style_seq}",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size + 1.5,
        textColor=colors.HexColor(color),
        alignment=align,
    )


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text).replace("\n", "<br/>"), style)


def title_white(text: str, size: float) -> Paragraph:
    t = sanitize(text)
    return P(f"<font color='#FFFFFF'><b>{t}</b></font>", sty("tw", size=size, color="#FFFFFF", bold=True))


def title_dark(text: str, size: float, color: str = "#1a1a1a") -> Paragraph:
    return P(f"<b>{sanitize(text)}</b>", sty("td", size=size, color=color, bold=True))


def usable_width() -> float:
    return A4[0] - MARGIN_L - MARGIN_R


CURRENT_SECTION = ["Parte I — Catalogo"]
PAGE_SECTION: dict[int, str] = {1: "Parte I — Catalogo"}


class SectionMarker(Flowable):
    """Segna la sezione corrente al render (per footer onPageEnd)."""

    def __init__(self, section: str):
        super().__init__()
        self.section = section

    def wrap(self, avail_width, avail_height):
        return avail_width, 0.5

    def draw(self):
        page = self.canv.getPageNumber()
        PAGE_SECTION[page] = self.section
        CURRENT_SECTION[0] = self.section


def section_marker(section: str) -> SectionMarker:
    return SectionMarker(section)


def section_for_page(page: int) -> str:
    section = PAGE_SECTION.get(1, "Parte I — Catalogo")
    for p in sorted(PAGE_SECTION):
        if p <= page:
            section = PAGE_SECTION[p]
    return section


def draw_footer(canvas, doc):
    section = section_for_page(doc.page)
    canvas.saveState()
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(MARGIN_L, 1.15 * cm, f"STRAN OPS DESK  ·  {section}")
    canvas.drawRightString(A4[0] - MARGIN_R, 1.15 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def doc_title_block(title: str, subtitle: str, part: str, built: str) -> Table:
    w = usable_width()
    t_style = sty("dt", size=14, color="#111111", bold=True, leading=16)
    s_style = sty("ds", size=8, color="#444444")
    p_style = sty("dp", size=7.5, color="#666666", align=TA_RIGHT)
    tbl = Table([
        [P(f"<b>{title}</b>", t_style), ""],
        [P(subtitle, s_style), P(f"{part}<br/>{built}", p_style)],
    ], colWidths=[w * 0.68, w * 0.32])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (0, 0), (-1, 0)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#222222")),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tbl


# ── Parte I ───────────────────────────────────────────────────────────

def catalog_section(group_key: str, subgroups: dict, legend: dict, width: float) -> Table:
    pal = PALETTE[group_key]
    label = legend[group_key]
    rows = [[title_white(label.upper(), 7.5)]]
    for sk in SUBGROUP_ORDER.get(group_key, subgroups.keys()):
        items = subgroups.get(sk)
        if not items:
            continue
        rows.append([title_dark(SUBGROUP_LABELS.get(sk, sk), 6.2)])
        for src in items:
            rows.append([P(f"· {src['label_it']}", sty("ci", size=6, color="#222", leading=7.2))])

    tbl = Table(rows, colWidths=[width])
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal["fill"])),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(pal["line"])),
        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(pal["accent"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal["accent"])),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
    ]
    r = 1
    for sk in SUBGROUP_ORDER.get(group_key, subgroups.keys()):
        items = subgroups.get(sk)
        if not items:
            continue
        cmds += [("TOPPADDING", (0, r), (-1, r), 2), ("BOTTOMPADDING", (0, r), (-1, r), 1)]
        r += 1
        for _ in items:
            cmds += [
                ("LEFTPADDING", (0, r), (-1, r), 10),
                ("TOPPADDING", (0, r), (-1, r), 0.3),
                ("BOTTOMPADDING", (0, r), (-1, r), 0.3),
            ]
            r += 1
    cmds += [("BOTTOMPADDING", (0, -1), (-1, -1), 3)]
    tbl.setStyle(TableStyle(cmds))
    return tbl


def toc_line(label: str, page: str, *, indent: int = 0, accent: str | None = None, size: float = 6.5) -> tuple:
    pad = "&nbsp;" * (indent * 4)
    icon = f"<font color='{accent}'>■</font> " if accent else ""
    return (
        P(f"{pad}{icon}{label}", sty("tocL", size=size, color="#333")),
        P(f"<b>{page}</b>", sty("tocR", size=size, color="#333", align=TA_RIGHT)),
    )


def toc_block(legend: dict, counts: dict) -> Table:
    w = usable_width()
    label_w = w * 0.84
    page_w = w * 0.16

    rows: list[list] = [[P("<b>Indice</b>", sty("toci", size=8, color="#FFFFFF", bold=True)), ""]]
    rows.append(toc_line("Parte I — Catalogo delle fonti", "1", size=6.5))
    rows.append(toc_line("Parte II — Vincoli operativi", "2-8", size=6.5))
    group_pages = {"fossil": "3", "renewable": "4-5", "nuclear": "6", "other": "7"}
    for g in GROUP_ORDER:
        pal = PALETTE[g]
        rows.append(toc_line(
            f"{legend[g]} ({counts[g]})",
            group_pages[g],
            indent=1,
            accent=pal["accent"],
            size=6.2,
        ))
    rows.append(toc_line(
        "Legenda: M meteo · L legale · G gestione",
        "",
        indent=1,
        size=5.8,
    ))

    tbl = Table(rows, colWidths=[label_w, page_w])
    tbl.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a2a3a")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F5F7")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 1.5),
    ]))
    return tbl


def parte1_story(catalog: dict, tree, legend: dict, counts: dict, built: str) -> list:
    w = usable_width()
    gap = 4 * mm
    col_w = (w - gap) / 2
    total = len(catalog["sources"])

    hdr = doc_title_block(
        catalog["title"],
        f"{total} fonti di produzione  ·  IEA World Energy Balances + IRENA",
        "Parte I",
        built,
    )

    def col_block(groups, width):
        rows = []
        for g in groups:
            if g in tree and tree[g]:
                rows.append([catalog_section(g, tree[g], legend, width)])
        if not rows:
            return Spacer(1, 1)
        tbl = Table(rows, colWidths=[width])
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -2), 2 * mm),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 0),
        ]))
        return tbl

    body = Table([[col_block(LEFT_GROUPS, col_w), col_block(RIGHT_GROUPS, col_w)]], colWidths=[col_w, col_w])
    body.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
        ("LEFTPADDING", (1, 0), (1, 0), gap / 2),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))

    return [
        section_marker("Parte I — Catalogo"),
        hdr,
        Spacer(1, 2 * mm),
        toc_block(legend, counts),
        Spacer(1, 2 * mm),
        body,
        Spacer(1, 1 * mm),
        P(catalog.get("note", ""), sty("fn", size=5.6, color="#777", align=TA_CENTER)),
    ]


# ── Parte II ──────────────────────────────────────────────────────────

def parte2_intro(built: str) -> list:
    w = usable_width()

    hdr = doc_title_block(
        "Vincoli operativi delle fonti",
        "Dipendenze meteo · Vincoli legali · Manutenzione e gestione",
        "Parte II",
        built,
    )

    dim_rows = [[
        title_white("Cod.", 7),
        title_white("Dimensione", 7),
        title_white("Contenuto", 7),
    ]]
    dim_desc = {
        "meteo": "Variabili climatiche che influenzano produzione, disponibilità o efficienza (vento, irradianza, idrologia, temperatura).",
        "legal": "Autorizzazioni, norme UE/nazionali, mercati regolati, emissioni, sicurezza, tracciabilità.",
        "ops": "Manutenzione programmata, disponibilità impianto, personale, logistica, cicli di vita tecnologico.",
    }
    for key, code, label, color in CONSTRAINT_DIMS:
        dim_rows.append([
            P(f"<b><font color='{color}'>{code}</font></b>", sty("dc", size=8, bold=True)),
            P(f"<b>{label}</b>", sty("dl", size=7, color="#222", bold=True)),
            P(dim_desc[key], sty("dd", size=6.5, color="#444")),
        ])

    dim_tbl = Table(dim_rows, colWidths=[w * 0.08, w * 0.28, w * 0.64])
    dim_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a2a3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    struct = P(
        "<b>Struttura pagine 3–6:</b> una sezione per macro-gruppo (Fossili, Rinnovabili, Nucleare, Altro), "
        "suddivisa in famiglie tecnologiche. Ogni fonte ha scheda con codici <b>M · L · G</b>.",
        sty("st", size=7, color="#333"),
    )

    return [PageBreak(), section_marker("Parte II — Introduzione"), hdr, Spacer(1, 4 * mm), dim_tbl, Spacer(1, 4 * mm), struct, Spacer(1, 2 * mm)]


def source_card(src: dict, group_key: str, card_w: float) -> Table:
    pal = PALETTE[group_key]
    c = CONSTRAINTS.get(src["id"], {})
    tag = sty("cv", size=5.8, color="#333", leading=7)

    rows = [[title_white(src["label_it"], 6.8)]]
    for key, code, label, color in CONSTRAINT_DIMS:
        val = c.get(key, "—")
        rows.append([P(
            f"<font color='{color}'><b>{code}</b></font>&nbsp;&nbsp;{val}",
            tag,
        )])

    tbl = Table(rows, colWidths=[card_w])
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal["accent"])),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(pal["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    tbl.setStyle(TableStyle(cmds))
    return tbl


def subgroup_heading(group_key: str, sub_key: str, width: float) -> Table:
    pal = PALETTE[group_key]
    tbl = Table(
        [[title_white(SUBGROUP_LABELS.get(sub_key, sub_key), 7.5)]],
        colWidths=[width],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal["accent"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def group_cover(group_key: str, legend: dict, count: int, width: float) -> Table:
    pal = PALETTE[group_key]
    tbl = Table([
        [title_white(legend[group_key].upper(), 11)],
        [P(f"<font color='#EEEEEE'>{count} fonti  ·  schede M / L / G</font>", sty("gs", size=7, color="#EEEEEE"))],
    ], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal["accent"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))
    return tbl


def cards_grid(sources: list[dict], group_key: str, width: float) -> list:
    gap = 3 * mm
    card_w = (width - gap) / 2
    flow: list = []
    for i in range(0, len(sources), 2):
        left = source_card(sources[i], group_key, card_w)
        right = source_card(sources[i + 1], group_key, card_w) if i + 1 < len(sources) else ""
        row = Table([[left, right]], colWidths=[card_w, card_w])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
            ("LEFTPADDING", (1, 0), (1, 0), gap / 2),
        ]))
        flow.append(row)
        flow.append(Spacer(1, 2 * mm))
    return flow


def group_constraints_story(group_key: str, subgroups: dict, legend: dict, built: str) -> list:
    w = usable_width()
    count = sum(len(v) for v in subgroups.values())
    label = legend[group_key]

    story: list = [
        PageBreak(),
        section_marker(f"Parte II — {label}"),
        group_cover(group_key, legend, count, w),
        Spacer(1, 3 * mm),
    ]

    for sk in SUBGROUP_ORDER.get(group_key, subgroups.keys()):
        items = subgroups.get(sk)
        if not items:
            continue
        story.append(subgroup_heading(group_key, sk, w))
        story.append(Spacer(1, 1.5 * mm))
        story.extend(cards_grid(items, group_key, w))

    return story


def parte2_story(catalog: dict, tree, legend: dict, built: str) -> list:
    story = parte2_intro(built)
    for g in GROUP_ORDER:
        if g in tree and tree[g]:
            story.extend(group_constraints_story(g, tree[g], legend, built))
    story.append(Spacer(1, 2 * mm))
    story.append(P(
        "Riferimenti: IEA World Energy Balances, IRENA, direttive UE (ETS, RED III, IEED, TEN-E, Seveso III).",
        sty("ref", size=5.8, color="#888", align=TA_CENTER),
    ))
    return story


# ── Parte III (appendice, pagine aggiuntive) ──────────────────────────

def parte3_principles_block(principles: list[str], width: float) -> Table:
    rows = [[title_white("Principi generali", 7.5)]]
    for p in principles:
        rows.append([P(f"- {p}", sty("p3p", size=6.5, color="#222"))])
    tbl = Table(rows, colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a2a3a")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
    ]))
    return tbl


def parte3_cycle_block(steps: list[str], width: float) -> Table:
    rows = [[title_white("Ciclo operativo", 7.5)]]
    for i, step in enumerate(steps, 1):
        rows.append([P(f"<b>{i}.</b> {step}", sty("cyc", size=6.5, color="#222"))])
    tbl = Table(rows, colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2F4A9A")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F3FA")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5D0EA")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 4),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 4),
    ]))
    return tbl


def parte3_groups_table(groups: dict, legend: dict, width: float) -> Table:
    rows = [[
        title_white("Gruppo", 7),
        title_white("Compliance (L)", 7),
        title_white("Manutenzione (G)", 7),
        title_white("Ruolo meteo (M)", 7),
    ]]
    for g in GROUP_ORDER:
        if g not in groups:
            continue
        p = groups[g]
        pal = PALETTE[g]
        rows.append([
            P(f"<b><font color='{pal['accent']}'>{legend[g]}</font></b>", sty("p3g", size=6.5, bold=True)),
            P(p["compliance"], sty("p3c", size=6, color="#444")),
            P(p["maintenance"], sty("p3m", size=6, color="#444")),
            P(p["weather_role"], sty("p3w", size=6, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.14, width * 0.30, width * 0.30, width * 0.26])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F6B45")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F8F3")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#C2DECC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def parte3_risk_table(groups: dict, legend: dict, width: float) -> Table:
    rows = [[
        title_white("Gruppo", 7),
        title_white("Se trascurato", 7),
        title_white("Cadenza tipica", 7),
    ]]
    for g in GROUP_ORDER:
        if g not in groups:
            continue
        p = groups[g]
        pal = PALETTE[g]
        rows.append([
            P(f"<b><font color='{pal['accent']}'>{legend[g]}</font></b>", sty("p3r", size=6.5, bold=True)),
            P(p["if_neglected"], sty("p3rn", size=6, color="#444")),
            P(p["cadence"], sty("p3rc", size=6, color="#555")),
        ])
    tbl = Table(rows, colWidths=[width * 0.16, width * 0.52, width * 0.32])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8B3A2A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAF6F4")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E8D0C8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def parte3_examples_table(examples: list[dict], width: float) -> Table:
    rows = [[
        title_white("Obbligo (esempio)", 7),
        title_white("Cadenza", 7),
        title_white("Ambito", 7),
    ]]
    for item in examples:
        rows.append([
            P(item["what"], sty("exw", size=6.2, color="#222")),
            P(item["cadence"], sty("exw", size=6.2, color="#333")),
            P(item["scope"], sty("exw", size=6.2, color="#555")),
        ])
    tbl = Table(rows, colWidths=[width * 0.38, width * 0.30, width * 0.32])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5A6472")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F6F8")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5DAE2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def parte3_actors_table(actors: list[dict], width: float) -> Table:
    rows = [[title_white("Attore", 7), title_white("Ruolo", 7)]]
    for actor in actors:
        rows.append([
            P(f"<b>{actor['name']}</b>", sty("act", size=6.5, color="#222", bold=True)),
            P(actor["role"], sty("actr", size=6.2, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.34, width * 0.66])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a2a3a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FAFAFA")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def parte3_story(operational: dict, legend: dict, built: str) -> list:
    w = usable_width()
    fw = operational["framework"]

    hdr = doc_title_block(
        operational["title"],
        "Compliance, manutenzione e meteo nel tempo — quadro generale",
        "Appendice A",
        built,
    )

    story = [
        PageBreak(),
        section_marker("Appendice A — Costo operativo"),
        hdr,
        Spacer(1, 3 * mm),
        P(fw["message"], sty("p3i", size=7.5, color="#222")),
        Spacer(1, 3 * mm),
        parte3_principles_block(fw["principles"], w),
        Spacer(1, 3 * mm),
        parte3_cycle_block(fw["cycle_steps"], w),
        Spacer(1, 4 * mm),
        P("<b>Profili per macro-gruppo</b>", sty("p3t", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        parte3_groups_table(operational["groups"], legend, w),
        Spacer(1, 3 * mm),
        parte3_risk_table(operational["groups"], legend, w),
        Spacer(1, 4 * mm),
        P("<b>Esempi di obblighi ricorrenti</b>", sty("p3t2", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        parte3_examples_table(operational["compliance_examples"], w),
        Spacer(1, 3 * mm),
        P("<b>Attori tipici</b>", sty("p3t3", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        parte3_actors_table(operational["actors"], w),
        Spacer(1, 2 * mm),
        P(
            "Appendice A — non sostituisce le schede M/L/G della Parte II.",
            sty("p3ref", size=5.8, color="#888", align=TA_CENTER),
        ),
    ]
    return story


# ── Appendice B/C — Accumulo e cooperazione (solo pagine aggiuntive) ───

def items_by_category(data: dict) -> dict[str, list[dict]]:
    tree: dict[str, list[dict]] = defaultdict(list)
    for item in data["items"]:
        tree[item["category"]].append(item)
    return tree


def appendix_cover(title: str, subtitle: str, count: int, pal: dict, width: float) -> Table:
    tbl = Table([
        [title_white(title.upper(), 11)],
        [P(f"<font color='#EEEEEE'>{count} voci  ·  {subtitle}</font>", sty("ac", size=7, color="#EEEEEE"))],
    ], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal["accent"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
    ]))
    return tbl


def category_heading(label: str, pal: dict, width: float) -> Table:
    tbl = Table([[title_white(label, 7.5)]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(pal["accent"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def appendix_item_card(item: dict, pal: dict, card_w: float, *, extra_lines: list[tuple[str, str]] | None = None) -> Table:
    tag = sty("acv", size=5.6, color="#333", leading=6.8)
    rows = [[title_white(item["label_it"], 6.5)]]
    if extra_lines:
        for label, val in extra_lines:
            if val:
                rows.append([P(f"<b>{label}:</b> {val}", tag)])
    for key, code, _, color in CONSTRAINT_DIMS:
        if key == "ops":
            val = item.get("maintenance", item.get("ops", "-"))
        else:
            val = item.get(key, "-")
        rows.append([P(f"<font color='{color}'><b>{code}</b></font>&nbsp;&nbsp;{val}", tag)])

    tbl = Table(rows, colWidths=[card_w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal["accent"])),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(pal["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 1.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def appendix_cards_grid(items: list[dict], pal: dict, width: float, extra_fn) -> list:
    gap = 3 * mm
    card_w = (width - gap) / 2
    flow: list = []
    for i in range(0, len(items), 2):
        left = appendix_item_card(items[i], pal, card_w, extra_lines=extra_fn(items[i]))
        right = (
            appendix_item_card(items[i + 1], pal, card_w, extra_lines=extra_fn(items[i + 1]))
            if i + 1 < len(items) else ""
        )
        row = Table([[left, right]], colWidths=[card_w, card_w])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
            ("LEFTPADDING", (1, 0), (1, 0), gap / 2),
        ]))
        flow.append(row)
        flow.append(Spacer(1, 2 * mm))
    return flow


def appendix_catalog_story(
    data: dict,
    pal_key: str,
    section_label: str,
    part_label: str,
    built: str,
    extra_fn,
) -> list:
    w = usable_width()
    pal = APPENDIX_PALETTE[pal_key]
    legend = data["category_legend"]
    order = data["category_order"]
    tree = items_by_category(data)
    count = len(data["items"])

    story: list = [
        PageBreak(),
        section_marker(section_label),
        doc_title_block(data["title"], data["subtitle"], part_label, built),
        Spacer(1, 3 * mm),
        P(data["intro"], sty("aint", size=7.2, color="#222")),
        Spacer(1, 3 * mm),
        appendix_cover(data["title"], "schede M / L / G + manutenzione", count, pal, w),
        Spacer(1, 3 * mm),
    ]

    for cat in order:
        items = tree.get(cat)
        if not items:
            continue
        story.append(category_heading(legend[cat], pal, w))
        story.append(Spacer(1, 1.5 * mm))
        story.extend(appendix_cards_grid(items, pal, w, extra_fn))

    story.append(Spacer(1, 2 * mm))
    story.append(P(
        f"{part_label} — complemento al catalogo produzione (Parte I).",
        sty("aref", size=5.8, color="#888", align=TA_CENTER),
    ))
    return story


def storage_extra(item: dict) -> list[tuple[str, str]]:
    lines = [
        ("Durata", item["timescale"]),
        ("Ruolo", item["role"]),
        ("Collegamenti", item["links"]),
    ]
    if item.get("ops") and item.get("ops") != item.get("maintenance"):
        lines.append(("Gestione", item["ops"]))
    lines += [
        ("Cadenza O&M", item.get("maintenance_cadence", "")),
        ("Se trascurato", item.get("if_neglected", "")),
    ]
    return lines


def cooperation_extra(item: dict) -> list[tuple[str, str]]:
    lines = [
        ("Descrizione", item["description"]),
        ("Attori", item["actors"]),
        ("Collegamenti", item["links"]),
    ]
    if item.get("ops") and item.get("ops") != item.get("maintenance"):
        lines.append(("Gestione", item["ops"]))
    lines += [
        ("Cadenza O&M", item.get("maintenance_cadence", "")),
        ("Se trascurato", item.get("if_neglected", "")),
    ]
    return lines


def parte4_storage_story(storage: dict, built: str) -> list:
    return appendix_catalog_story(
        storage,
        "storage",
        "Appendice B — Accumulo",
        "Appendice B",
        built,
        storage_extra,
    )


def parte5_cooperation_story(cooperation: dict, built: str) -> list:
    return appendix_catalog_story(
        cooperation,
        "cooperation",
        "Appendice C — Cooperazione",
        "Appendice C",
        built,
        cooperation_extra,
    )


# ── Appendice D/E — Schede manutenzione dedicate ──────────────────────

def maintenance_only_card(item: dict, pal: dict, card_w: float) -> Table:
    tag = sty("mcv", size=5.8, color="#333", leading=7)
    g_color = CONSTRAINT_DIMS[2][3]
    rows = [[title_white(item["label_it"], 6.5)]]
    if item.get("maintenance_cadence"):
        rows.append([P(f"<b>Cadenza:</b> {item['maintenance_cadence']}", tag)])
    rows.append([P(f"<font color='{g_color}'><b>G</b></font>&nbsp;&nbsp;{item.get('maintenance', '-')}", tag)])
    if item.get("if_neglected"):
        rows.append([P(f"<b>Se trascurato:</b> {item['if_neglected']}", tag)])
    tbl = Table(rows, colWidths=[card_w])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal["accent"])),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor(pal["fill"])),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor(pal["line"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return tbl


def maintenance_cards_grid(items: list[dict], pal: dict, width: float) -> list:
    gap = 3 * mm
    card_w = (width - gap) / 2
    flow: list = []
    for i in range(0, len(items), 2):
        left = maintenance_only_card(items[i], pal, card_w)
        right = maintenance_only_card(items[i + 1], pal, card_w) if i + 1 < len(items) else ""
        row = Table([[left, right]], colWidths=[card_w, card_w])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("RIGHTPADDING", (0, 0), (0, 0), gap / 2),
            ("LEFTPADDING", (1, 0), (1, 0), gap / 2),
        ]))
        flow.append(row)
        flow.append(Spacer(1, 2 * mm))
    return flow


def category_maintenance_table(
    profiles: dict,
    legend: dict,
    order: list[str],
    pal: dict,
    width: float,
) -> Table:
    rows = [[
        title_white("Categoria", 7),
        title_white("Manutenzione dominante", 7),
        title_white("Cadenza", 7),
        title_white("Se trascurato", 7),
    ]]
    for cat in order:
        p = profiles.get(cat)
        if not p:
            continue
        rows.append([
            P(f"<b>{legend[cat]}</b>", sty("cmt", size=6.2, color="#222", bold=True)),
            P(p["maintenance"], sty("cmv", size=6, color="#444")),
            P(p["cadence"], sty("cmc", size=6, color="#555")),
            P(p["if_neglected"], sty("cmn", size=6, color="#555")),
        ])
    tbl = Table(rows, colWidths=[width * 0.14, width * 0.36, width * 0.22, width * 0.28])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(pal["accent"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor(pal["fill"])),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor(pal["line"])),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def appendix_maintenance_story(
    data: dict,
    profiles: dict,
    pal_key: str,
    part_label: str,
    section_label: str,
    built: str,
    intro: str | None = None,
) -> list:
    w = usable_width()
    pal = APPENDIX_PALETTE[pal_key]
    legend = data["category_legend"]
    order = data["category_order"]
    tree = items_by_category(data)

    story: list = [
        PageBreak(),
        section_marker(section_label),
        doc_title_block(
            f"Manutenzione — {data['title']}",
            "O&M programmato, cadenze e conseguenze se trascurato",
            part_label,
            built,
        ),
        Spacer(1, 3 * mm),
        P(
            intro or (
                "L'accumulo e la cooperazione restano operativi solo con manutenzione continua: "
                "ispezioni, revisioni contrattuali, O&M asset fisici e piattaforme digitali."
            ),
            sty("maint_i", size=7.2, color="#222"),
        ),
        Spacer(1, 3 * mm),
        category_maintenance_table(profiles, legend, order, pal, w),
        Spacer(1, 4 * mm),
    ]

    for cat in order:
        items = tree.get(cat)
        if not items:
            continue
        story.append(category_heading(f"Manutenzione — {legend[cat]}", pal, w))
        story.append(Spacer(1, 1.5 * mm))
        story.extend(maintenance_cards_grid(items, pal, w))

    story.append(Spacer(1, 2 * mm))
    story.append(P(
        f"{part_label} — dettaglio manutenzione per voce.",
        sty("mref", size=5.8, color="#888", align=TA_CENTER),
    ))
    return story


# ── Appendice F — Redistribuzione AC vs DC ───────────────────────────

def ac_dc_summary_table(summary: dict, width: float) -> Table:
    rows = [[
        title_white("", 7),
        title_white("AC (corrente alternata)", 7),
        title_white("DC (corrente continua)", 7),
    ]]
    for key, label in [
        ("principle", "Principio"),
        ("advantages", "Vantaggi"),
        ("limits", "Limiti"),
        ("infrastructure", "Infrastruttura tipica"),
    ]:
        rows.append([
            P(f"<b>{label}</b>", sty("acd", size=6.5, color="#222", bold=True)),
            P(summary["ac"][key], sty("acv", size=6.2, color="#444")),
            P(summary["dc"][key], sty("dcv", size=6.2, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.16, width * 0.42, width * 0.42])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B45309")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFF7ED")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#FED7AA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def decision_factors_table(factors: list[dict], width: float) -> Table:
    rows = [[
        title_white("Fattore", 7),
        title_white("AC", 7),
        title_white("DC", 7),
    ]]
    for f in factors:
        rows.append([
            P(f"<b>{f['factor']}</b>", sty("df", size=6.5, color="#222", bold=True)),
            P(f["ac"], sty("dfa", size=6.2, color="#444")),
            P(f["dc"], sty("dfd", size=6.2, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.18, width * 0.41, width * 0.41])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#92400E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFBEB")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#FDE68A")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def redistribution_extra(item: dict) -> list[tuple[str, str]]:
    lines = [
        ("Tensione", item.get("voltage", "")),
        ("Ruolo", item.get("role", "")),
        ("Vantaggi", item.get("advantages", "")),
        ("Differenze", item.get("differences", "")),
        ("Infrastruttura", item.get("infrastructure", "")),
        ("Collegamenti", item.get("links", "")),
    ]
    if item.get("ops") and item.get("ops") != item.get("maintenance"):
        lines.append(("Gestione", item["ops"]))
    lines += [
        ("Cadenza O&M", item.get("maintenance_cadence", "")),
        ("Se trascurato", item.get("if_neglected", "")),
    ]
    return lines


def consumption_extra(item: dict) -> list[tuple[str, str]]:
    lines = [
        ("Vettori", item.get("vectors", "")),
        ("Profilo AC/DC", item.get("ac_dc", "")),
        ("Flessibilita", item.get("flexibility", "")),
        ("Picco", item.get("peak_driver", "")),
        ("Collegamenti", item.get("links", "")),
    ]
    if item.get("ops") and item.get("ops") != item.get("maintenance"):
        lines.append(("Gestione", item["ops"]))
    lines += [
        ("Cadenza O&M", item.get("maintenance_cadence", "")),
        ("Se trascurato", item.get("if_neglected", "")),
    ]
    return lines


def parte6_redistribution_story(redist: dict, built: str) -> list:
    w = usable_width()
    pal = APPENDIX_PALETTE["redistribution"]
    legend = redist["category_legend"]
    order = redist["category_order"]
    tree = items_by_category(redist)
    count = len(redist["items"])

    story: list = [
        PageBreak(),
        section_marker("Appendice F — Redistribuzione"),
        doc_title_block(redist["title"], redist["subtitle"], "Appendice F", built),
        Spacer(1, 3 * mm),
        P(redist["intro"], sty("rd_i", size=7.2, color="#222")),
        Spacer(1, 3 * mm),
        P("<b>Confronto AC vs DC</b>", sty("rd_t", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        ac_dc_summary_table(redist["ac_dc_summary"], w),
        Spacer(1, 3 * mm),
        P("<b>Fattori di scelta</b>", sty("rd_t2", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        decision_factors_table(redist["decision_factors"], w),
        Spacer(1, 3 * mm),
        appendix_cover(redist["title"], "schede M / L / G + manutenzione", count, pal, w),
        Spacer(1, 3 * mm),
    ]

    for cat in order:
        items = tree.get(cat)
        if not items:
            continue
        story.append(category_heading(legend[cat], pal, w))
        story.append(Spacer(1, 1.5 * mm))
        story.extend(appendix_cards_grid(items, pal, w, redistribution_extra))

    story.append(Spacer(1, 2 * mm))
    story.append(P(
        "Appendice F — redistribuzione da accumulo/cooperazione verso consumo.",
        sty("rd_ref", size=5.8, color="#888", align=TA_CENTER),
    ))
    return story


def parte7_consumption_story(consumption: dict, built: str) -> list:
    return appendix_catalog_story(
        consumption,
        "consumption",
        "Appendice H — Consumo",
        "Appendice H",
        built,
        consumption_extra,
    )


def chain_steps_table(chain: dict, width: float) -> Table:
    rows = [[
        title_white("Step", 7),
        title_white("Anello", 7),
        title_white("Riferimento", 7),
        title_white("Output", 7),
    ]]
    for s in chain["steps"]:
        rows.append([
            P(f"<b>{s['step']}</b>", sty("cs", size=6.5, bold=True)),
            P(s["name"], sty("csn", size=6.2, color="#222")),
            P(s["ref"], sty("csr", size=6.2, color="#555")),
            P(s["output"], sty("cso", size=6.2, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.08, width * 0.22, width * 0.22, width * 0.48])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0F4F8")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def losses_table(losses: list[dict], width: float) -> Table:
    rows = [[
        title_white("Stadio", 7),
        title_white("Perdite tipiche", 7),
        title_white("Driver principale", 7),
    ]]
    for L in losses:
        rows.append([
            P(f"<b>{L['stage']}</b>", sty("ls", size=6.2, color="#222", bold=True)),
            P(L["typical"], sty("lt", size=6.2, color="#444")),
            P(L["main_driver"], sty("ld", size=6.2, color="#555")),
        ])
    tbl = Table(rows, colWidths=[width * 0.24, width * 0.28, width * 0.48])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9FAFB")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


def document_map_table(sections: list[dict], width: float) -> Table:
    rows = [[
        title_white("Sezione", 7),
        title_white("Pagine", 7),
        title_white("Contenuto", 7),
    ]]
    for s in sections:
        rows.append([
            P(f"<b>{s['section']}</b>", sty("dm", size=6.5, color="#222", bold=True)),
            P(s["pages"], sty("dmp", size=6.2, color="#555")),
            P(s["content"], sty("dmc", size=6.2, color="#444")),
        ])
    tbl = Table(rows, colWidths=[width * 0.22, width * 0.12, width * 0.66])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tbl


DIAGRAM_PHASES = [
    ("1", "Produzione", "#8B3A2A"),
    ("2", "Operativita", "#3d4a3a"),
    ("3", "Integrazione", "#2E6B7A"),
    ("4", "Storage", "#6B4C9A"),
    ("5", "Reti", "#B45309"),
    ("6", "Consumo", "#047857"),
    ("7", "Output", "#111827"),
]

NODE_ORDER = [
    "production", "operativity",
    "coproduction", "cooperation", "stoccaggio",
    "accumulo",
    "distribution", "redistribution",
    "consumption", "useful",
]


class SystemDiagramFlowable(Flowable):
    """Diagramma a flusso — layout a fasi con connessioni ortogonali."""

    def __init__(self, diagram: dict, width: float, height: float):
        super().__init__()
        self.diagram = diagram
        self.width = width
        self.height = height
        self._nodes: dict[str, tuple[float, float, float, float]] = {}
        self._phase_y: dict[str, float] = {}

    def wrap(self, avail_width, avail_height):
        h = min(self.height, avail_height - 2)
        return self.width, h

    def _compute_layout(self):
        w, h = self.width, self.height
        pad_l, pad_r, pad_t, pad_b = 46, 12, 22, 54
        inner_w = w - pad_l - pad_r
        cx = pad_l + inner_w / 2
        y = h - pad_t
        gap_arrow = 16
        bh_main = 46
        bh_branch = 40
        bh_mid = 42
        bh_out = 40

        def place(nid: str, x: float, width: float, height: float):
            nonlocal y
            y -= height
            self._nodes[nid] = (x, y, width, height)
            return y

        place("production", pad_l + inner_w * 0.06, inner_w * 0.88, bh_main)
        self._phase_y["1"] = y + bh_main / 2
        y -= gap_arrow

        place("operativity", pad_l + inner_w * 0.06, inner_w * 0.88, bh_main)
        self._phase_y["2"] = y + bh_main / 2
        y -= gap_arrow

        col_w = inner_w * 0.29
        col_gap = inner_w * 0.035
        x0 = pad_l + inner_w * 0.03
        branch_y = y - bh_branch
        self._nodes["coproduction"] = (x0, branch_y, col_w, bh_branch)
        self._nodes["cooperation"] = (x0 + col_w + col_gap, branch_y, col_w, bh_branch)
        self._nodes["stoccaggio"] = (x0 + 2 * (col_w + col_gap), branch_y, col_w, bh_branch)
        self._phase_y["3"] = branch_y + bh_branch / 2
        y = branch_y - gap_arrow

        acc_w = inner_w * 0.52
        place("accumulo", cx - acc_w / 2, acc_w, bh_mid)
        self._phase_y["4"] = y + bh_mid / 2
        y -= gap_arrow

        half_w = inner_w * 0.46
        pair_y = y - bh_mid
        self._nodes["distribution"] = (pad_l + inner_w * 0.02, pair_y, half_w, bh_mid)
        self._nodes["redistribution"] = (pad_l + inner_w * 0.52, pair_y, half_w, bh_mid)
        self._phase_y["5"] = pair_y + bh_mid / 2
        y = pair_y - gap_arrow

        place("consumption", pad_l + inner_w * 0.06, inner_w * 0.88, bh_main)
        self._phase_y["6"] = y + bh_main / 2
        y -= gap_arrow

        out_w = inner_w * 0.62
        place("useful", cx - out_w / 2, out_w, bh_out)
        self._phase_y["7"] = y + bh_out / 2

    def _box(self, node_id: str) -> tuple[float, float, float, float]:
        return self._nodes[node_id]

    def _pt(self, node_id: str, side: str) -> tuple[float, float]:
        x, y, bw, bh = self._box(node_id)
        if side == "top":
            return x + bw / 2, y + bh
        if side == "bottom":
            return x + bw / 2, y
        if side == "left":
            return x, y + bh / 2
        if side == "right":
            return x + bw, y + bh / 2
        return x + bw / 2, y + bh / 2

    def _loss_badge(self, x: float, y: float, text: str):
        if not text:
            return
        c = self.canv
        c.setFont("Helvetica-Bold", 5.5)
        tw = c.stringWidth(sanitize(text), "Helvetica-Bold", 5.5)
        bw, bh = tw + 10, 11
        c.setFillColor(colors.HexColor("#FEE2E2"))
        c.setStrokeColor(colors.HexColor("#FECACA"))
        c.setLineWidth(0.4)
        c.roundRect(x - bw / 2, y - 2, bw, bh, 3, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#B91C1C"))
        c.drawCentredString(x, y + 1, sanitize(text))

    def _draw_path(self, points: list[tuple[float, float]], loss: str = ""):
        c = self.canv
        if len(points) < 2:
            return
        c.setStrokeColor(colors.HexColor("#64748B"))
        c.setLineWidth(1.0)
        path = c.beginPath()
        path.moveTo(points[0][0], points[0][1])
        for px, py in points[1:]:
            path.lineTo(px, py)
        c.drawPath(path, fill=0, stroke=1)

        x1, y1 = points[-2]
        x2, y2 = points[-1]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5 or 1.0
        dx, dy = dx / norm, dy / norm
        c.setFillColor(colors.HexColor("#64748B"))
        head = c.beginPath()
        head.moveTo(x2, y2)
        head.lineTo(x2 - dx * 6 + dy * 2.5, y2 - dy * 6 - dx * 2.5)
        head.lineTo(x2 - dx * 6 - dy * 2.5, y2 - dy * 6 + dx * 2.5)
        head.close()
        c.drawPath(head, fill=1, stroke=0)

        if loss:
            mid = len(points) // 2
            bx, by = points[mid]
            self._loss_badge(bx, by + 5, loss)

    def _connect_v(self, src: str, dst: str, loss: str = ""):
        x1, y1 = self._pt(src, "bottom")
        x2, y2 = self._pt(dst, "top")
        mid_y = (y1 + y2) / 2
        self._draw_path([(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)], loss)

    def _connect_fork(self, src: str, dst: str, loss: str = ""):
        x1, y1 = self._pt(src, "bottom")
        x2, y2 = self._pt(dst, "top")
        rail = y1 - 8
        self._draw_path([(x1, y1), (x1, rail), (x2, rail), (x2, y2)], loss)

    def _connect_merge(self, src: str, dst: str, loss: str = ""):
        x1, y1 = self._pt(src, "bottom")
        x2, y2 = self._pt(dst, "top")
        rail = y2 + 8
        self._draw_path([(x1, y1), (x1, rail), (x2, rail), (x2, y2)], loss)

    def _connect_h(self, src: str, dst: str, loss: str = ""):
        x1, y1 = self._pt(src, "right")
        x2, y2 = self._pt(dst, "left")
        mid_x = (x1 + x2) / 2
        self._draw_path([(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)], loss)

    def _connect_diag_storage(self, loss: str = ""):
        x1, y1 = self._pt("stoccaggio", "bottom")
        x2, y2 = self._pt("distribution", "top")
        mid_y = (y1 + y2) / 2
        self._draw_path([(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)], loss)

    def _draw_phase_labels(self):
        c = self.canv
        for num, label, color in DIAGRAM_PHASES:
            py = self._phase_y.get(num)
            if py is None:
                continue
            c.setFillColor(colors.HexColor(color))
            c.circle(16, py, 7, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 6)
            c.drawCentredString(16, py - 2, num)
            c.setFillColor(colors.HexColor("#475569"))
            c.setFont("Helvetica", 5.5)
            c.drawString(26, py - 2, sanitize(label))

    def _draw_node(self, node: dict, step: str):
        c = self.canv
        x, y, bw, bh = self._box(node["id"])
        accent = colors.HexColor(node["accent"])
        fill = colors.HexColor(node["fill"])

        c.setFillColor(colors.HexColor("#00000018"))
        c.roundRect(x + 1.5, y - 1.5, bw, bh, 5, fill=1, stroke=0)

        c.setFillColor(fill)
        c.setStrokeColor(accent)
        c.setLineWidth(1.0)
        c.roundRect(x, y, bw, bh, 5, fill=1, stroke=1)

        c.setFillColor(accent)
        c.rect(x, y, 5, bh, fill=1, stroke=0)
        c.rect(x, y + bh - 13, bw, 13, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + 9, y + bh - 10, sanitize(node["title"]))

        c.setFillColor(colors.HexColor("#1F2937"))
        c.setFont("Helvetica", 5.6)
        ty = y + bh - 22
        for line in node["lines"][:2]:
            c.drawString(x + 9, ty, sanitize(line))
            ty -= 7.5

        c.setFillColor(colors.HexColor("#6B7280"))
        c.setFont("Helvetica", 5)
        ref = sanitize(node.get("ref", ""))
        if ref:
            c.drawRightString(x + bw - 6, y + 4, ref)

        if node["id"] == "useful":
            c.setStrokeColor(colors.HexColor("#059669"))
            c.setLineWidth(1.8)
            c.roundRect(x - 1, y - 1, bw + 2, bh + 2, 6, fill=0, stroke=1)

    def _draw_header_footer(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#1E293B"))
        c.rect(0, self.height - 18, self.width, 18, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(10, self.height - 13, sanitize(self.diagram.get("title", "Catena energetica")))

        c.setFillColor(colors.HexColor("#F1F5F9"))
        c.rect(0, 0, self.width, 48, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(0, 48, self.width, 48)

        ly = 38
        c.setFont("Helvetica", 5.4)
        c.setFillColor(colors.HexColor("#64748B"))
        for line in self.diagram.get("loss_legend", []):
            c.drawString(10, ly, sanitize(line))
            ly -= 7

        c.setFont("Helvetica-Bold", 5.4)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawRightString(
            self.width - 10, 10,
            sanitize("Frecce rosse = perdite tipiche  ·  M/L/G su ogni anello"),
        )

    def draw(self):
        self._compute_layout()
        c = self.canv

        c.setFillColor(colors.HexColor("#FFFFFF"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=1)

        edges = {(e["from"], e["to"]): e.get("loss", "") for e in self.diagram["edges"]}
        nodes = {n["id"]: n for n in self.diagram["nodes"]}
        step_map = {nid: DIAGRAM_PHASES[i][0] for i, nid in enumerate(NODE_ORDER) if i < len(DIAGRAM_PHASES)}

        self._connect_v("production", "operativity", edges.get(("production", "operativity"), ""))
        self._connect_fork("operativity", "coproduction", edges.get(("operativity", "coproduction"), ""))
        self._connect_fork("operativity", "cooperation", edges.get(("operativity", "cooperation"), ""))
        self._connect_fork("operativity", "stoccaggio", edges.get(("operativity", "stoccaggio"), ""))
        self._connect_merge("coproduction", "accumulo", edges.get(("coproduction", "accumulo"), ""))
        self._connect_merge("cooperation", "accumulo", edges.get(("cooperation", "accumulo"), ""))
        self._connect_diag_storage(edges.get(("stoccaggio", "distribution"), ""))
        self._connect_v("accumulo", "distribution", edges.get(("accumulo", "distribution"), ""))
        self._connect_h("distribution", "redistribution", edges.get(("distribution", "redistribution"), ""))
        self._connect_v("redistribution", "consumption", edges.get(("redistribution", "consumption"), ""))
        self._connect_v("consumption", "useful", edges.get(("consumption", "useful"), ""))

        self._draw_phase_labels()
        for nid in NODE_ORDER:
            if nid in nodes:
                self._draw_node(nodes[nid], step_map.get(nid, ""))
        self._draw_header_footer()


def system_diagram_block(diagram: dict, width: float) -> SystemDiagramFlowable:
    return SystemDiagramFlowable(diagram, width, 25.0 * cm)


def parte8_overview_story(overview: dict, built: str) -> list:
    w = usable_width()
    diagram = overview.get("system_diagram", {})

    return [
        PageBreak(),
        section_marker("Appendice I — Sintesi"),
        doc_title_block(overview["title"], overview["subtitle"], "Appendice I", built),
        Spacer(1, 3 * mm),
        P(overview["chain"]["message"], sty("ov_i", size=7.5, color="#222")),
        Spacer(1, 3 * mm),
        P("<b>Catena energetica completa</b>", sty("ov_t", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        chain_steps_table(overview["chain"], w),
        Spacer(1, 4 * mm),
        P("<b>Perdite tipiche per stadio</b>", sty("ov_t2", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        losses_table(overview["losses"], w),
        Spacer(1, 4 * mm),
        P("<b>Mappa del documento</b>", sty("ov_t3", size=8, color="#111", bold=True)),
        Spacer(1, 2 * mm),
        document_map_table(overview["document_map"], w),
        PageBreak(),
        section_marker("Appendice I — Diagramma"),
        P(
            "<b>Diagramma di sintesi — sistema energetico completo</b>",
            sty("ov_dg", size=9, color="#111", bold=True),
        ),
        Spacer(1, 1 * mm),
        system_diagram_block(diagram, w),
    ]



def build_pdf(catalog: dict, out_path: Path) -> tuple[int, int]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    PAGE_SECTION.clear()
    PAGE_SECTION[1] = "Parte I — Catalogo"
    CURRENT_SECTION[0] = "Parte I — Catalogo"
    sources = catalog["sources"]
    legend = catalog.get("group_legend", {})
    tree = group_sources(sources)
    counts = {g: sum(len(v) for v in tree.get(g, {}).values()) for g in GROUP_ORDER}
    built = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title=catalog["title"],
        author="STRAN OPS DESK",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.pageTemplates = []
    doc.addPageTemplates([
        PageTemplate(id="First", frames=[frame], onPageEnd=draw_footer, pagesize=A4),
        PageTemplate(id="Later", frames=[frame], onPageEnd=draw_footer, pagesize=A4),
    ])

    story = parte1_story(catalog, tree, legend, counts, built)
    story += parte2_story(catalog, tree, legend, built)
    operational = load_operational()
    story += parte3_story(operational, legend, built)
    maint = load_appendix_maintenance()
    storage = merge_maintenance(load_storage(), maint, "storage")
    cooperation = merge_maintenance(load_cooperation(), maint, "cooperation")
    story += parte4_storage_story(storage, built)
    story += appendix_maintenance_story(
        storage,
        maint["category_profiles"]["storage"],
        "storage",
        "Appendice D",
        "Appendice D — Manutenzione accumulo",
        built,
    )
    story += parte5_cooperation_story(cooperation, built)
    story += appendix_maintenance_story(
        cooperation,
        maint["category_profiles"]["cooperation"],
        "cooperation",
        "Appendice E",
        "Appendice E — Manutenzione cooperazione",
        built,
    )
    redist = merge_maintenance(
        merge_item_overlay(load_redistribution(), load_redistribution_overlay()),
        maint,
        "redistribution",
    )
    story += parte6_redistribution_story(redist, built)
    story += appendix_maintenance_story(
        redist,
        maint["category_profiles"]["redistribution"],
        "redistribution",
        "Appendice G",
        "Appendice G — Manutenzione redistribuzione",
        built,
        intro="Reti elettriche, HVDC, bus DC e infrastruttura fluidi richiedono O&M continuo: ispezioni linee, converter, protezione arco, smart meter.",
    )
    consumption = merge_maintenance(load_consumption(), maint, "consumption")
    story += parte7_consumption_story(consumption, built)
    story += parte8_overview_story(load_overview(), built)

    BaseDocTemplate.build(doc, story)
    return len(sources), doc.page


def main() -> int:
    catalog = load_catalog()
    total, pages = build_pdf(catalog, OUT)
    print(f"OK {OUT} ({total} fonti, {pages} pagine A4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
