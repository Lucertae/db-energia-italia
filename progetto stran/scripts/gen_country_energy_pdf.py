#!/usr/bin/env python3
"""PDF A4 — produzione energetica paese per paese (OWID energy-data, dati completi)."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
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
OWID_CSV = ROOT / "cache" / "owid" / "owid-energy-data.csv"
OWID_CODEBOOK = ROOT / "cache" / "owid" / "owid-energy-codebook.csv"
OWID_GITHUB = "https://github.com/owid/energy-data"
TRADE_CSV = ROOT / "cache" / "eurostat" / "electricity_trade_bilateral.csv"
OUT = WORKSPACE / "produzione-energetica-paesi.pdf"

MARGIN_L = 1.8 * cm
MARGIN_R = 1.8 * cm
MARGIN_T = 1.4 * cm
MARGIN_B = 1.8 * cm
COL_GAP = 4 * mm
PAGE_USABLE_H = A4[1] - MARGIN_T - MARGIN_B

_UNICODE_MAP = str.maketrans({
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
    "\u00b0": " gr", "\u00b7": " - ", "\u2212": "-", "\u00d7": "x",
    "\u2013": "-", "\u2014": "-", "\u2192": "->", "\u25a0": "*",
    "\u2219": "-", "\u2022": "-",
})

AGGREGATE_ISO = {
    "EUU", "EUN", "SSF", "SSA", "SAS", "NAC", "LCN", "MEA",
    "HIC", "LIC", "LMC", "UMC", "INX", "WLD",
}

ELEC_FUELS = [
    ("solar_electricity", "solar_share_elec", "SOL", "Solare", "#DCDC78"),
    ("wind_electricity", "wind_share_elec", "WIN", "Eolico", "#B4DCFF"),
    ("hydro_electricity", "hydro_share_elec", "HYD", "Idroelettrico", "#64A0DC"),
    ("nuclear_electricity", "nuclear_share_elec", "NUC", "Nucleare", "#C8B4FF"),
    ("gas_electricity", "gas_share_elec", "GAS", "Gas", "#FFC878"),
    ("coal_electricity", "coal_share_elec", "COAL", "Carbone", "#8C8C8C"),
    ("oil_electricity", "oil_share_elec", "OIL", "Petrolio", "#B4A08C"),
    ("biofuel_electricity", "biofuel_share_elec", "BIO", "Biomassa", "#A0C8A0"),
    ("__other_renewable__", "", "OTH", "Altro rinnov.", "#787878"),
]

OTHER_RENEW_EXC = ("other_renewable_exc_biofuel_electricity", "other_renewables_share_elec_exc_biofuel")
OTHER_RENEW_ALL = ("other_renewable_electricity", "other_renewables_share_elec")

PRI_FUELS = [
    ("coal_consumption", "coal_share_energy", "Carbone"),
    ("oil_consumption", "oil_share_energy", "Petrolio"),
    ("gas_consumption", "gas_share_energy", "Gas"),
    ("nuclear_consumption", "nuclear_share_energy", "Nucleare"),
    ("hydro_consumption", "hydro_share_energy", "Idroelettrico"),
    ("solar_consumption", "solar_share_energy", "Solare"),
    ("wind_consumption", "wind_share_energy", "Eolico"),
    ("biofuel_consumption", "biofuel_share_energy", "Biocarburanti"),
    ("other_renewable_consumption", "other_renewables_share_energy", "Altro rinnov."),
]

FOSSIL_PROD = [
    ("coal_production", "coal_prod_change_pct", "Carbone"),
    ("gas_production", "gas_prod_change_pct", "Gas"),
    ("oil_production", "oil_prod_change_pct", "Petrolio"),
]

ISO2_TO_ISO3 = {
    "AL": "ALB", "AT": "AUT", "BA": "BIH", "BE": "BEL", "BG": "BGR", "CZ": "CZE", "DE": "DEU",
    "DK": "DNK", "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN", "FR": "FRA", "GE": "GEO",
    "HR": "HRV", "HU": "HUN", "IE": "IRL", "IT": "ITA", "LI": "LIE", "LT": "LTU", "LU": "LUX",
    "LV": "LVA", "MD": "MDA", "ME": "MNE", "MK": "MKD", "MT": "MLT", "NL": "NLD", "NO": "NOR",
    "PL": "POL", "PT": "PRT", "RO": "ROU", "RS": "SRB", "SE": "SWE", "SI": "SVN", "SK": "SVK",
    "TR": "TUR", "UA": "UKR", "UK": "GBR", "XK": "XKX",
}

TRADE_AGG_PARTNERS = {
    "EU27_2020", "EU28", "EA20", "EA21", "E27_2020", "EXT_EA", "EXT_EU", "EXT_EEA",
    "EXT_OTH", "EXT_REG", "WORLD", "TOT", "TOTAL",
}

NAME_ALIASES = {
    "czechia": "czech republic",
    "türkiye": "turkey",
    "turkiye": "turkey",
    "united states": "united states of america",
}

_style_seq = 0


def sanitize(text: str) -> str:
    return str(text).translate(_UNICODE_MAP)


def sty(name: str, *, size: float, color: str = "#1a1a1a", bold: bool = False, align=TA_LEFT, leading: float | None = None) -> ParagraphStyle:
    global _style_seq
    _style_seq += 1
    return ParagraphStyle(
        name=f"{name}_{_style_seq}",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading or size + 1.2,
        textColor=colors.HexColor(color),
        alignment=align,
    )


def P(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text).replace("\n", "<br/>"), style)


def usable_width() -> float:
    return A4[0] - MARGIN_L - MARGIN_R


def col_widths() -> tuple[float, float]:
    w = usable_width()
    half = (w - COL_GAP) / 2
    return half, half


def fval(row: dict | None, key: str) -> float:
    if not row:
        return 0.0
    try:
        return float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def has_val(row: dict, key: str) -> bool:
    raw = (row.get(key) or "").strip()
    if not raw:
        return False
    try:
        return float(raw) != 0.0
    except ValueError:
        return False


def other_renewable_twh(row: dict) -> float:
    exc = fval(row, OTHER_RENEW_EXC[0])
    if exc > 0:
        return exc
    oth = fval(row, OTHER_RENEW_ALL[0])
    bio = fval(row, "biofuel_electricity")
    if oth > 0 and bio > 0:
        return max(0.0, oth - bio)
    return oth


def fuel_twh(row: dict | None, val_key: str) -> float:
    if not row:
        return 0.0
    if val_key == "__other_renewable__":
        return other_renewable_twh(row)
    return fval(row, val_key)


def is_country_row(row: dict) -> bool:
    iso = (row.get("iso_code") or "").strip()
    name = row.get("country") or ""
    if len(iso) != 3 or not iso.isalpha() or not iso.isupper():
        return False
    if iso in AGGREGATE_ISO or "(" in name:
        return False
    return True


def latest_row_with(rows: list[dict], predicate) -> tuple[dict | None, int]:
    candidates = [(int(r["year"]), r) for r in rows if predicate(r)]
    if not candidates:
        return None, 0
    year, row = max(candidates, key=lambda x: x[0])
    return row, year


@dataclass
class YearPoint:
    year: int
    elec_twh: float = 0.0
    primary_twh: float = 0.0
    solar_twh: float = 0.0
    wind_twh: float = 0.0
    rest_twh: float = 0.0
    ren_pct: float = 0.0
    fossil_pct: float = 0.0
    low_carbon_pct: float = 0.0
    ghg_mt: float = 0.0
    demand_twh: float = 0.0


@dataclass
class CountryProfile:
    name: str
    iso: str
    rows: list[dict] = field(default_factory=list)
    history: list[YearPoint] = field(default_factory=list)
    elec_row: dict | None = None
    elec_year: int = 0
    pri_row: dict | None = None
    pri_year: int = 0
    prod_row: dict | None = None
    prod_year: int = 0
    meta_row: dict | None = None
    meta_year: int = 0

    def elec_total(self) -> float:
        if not self.elec_row:
            return 0.0
        total = fval(self.elec_row, "electricity_generation")
        if total > 0:
            return total
        return sum(fuel_twh(self.elec_row, k) for k, _, _, _, _ in ELEC_FUELS)

    def production_fuel_rows(self) -> list[tuple[str, str, str, float, float, str]]:
        """Ordine fisso terminale PROD: SOL WIN HYD NUC GAS COAL OIL BIO OTH."""
        if not self.elec_row:
            return []
        total = self.elec_total()
        out: list[tuple[str, str, str, float, float, str]] = []
        for val_key, _share_key, tag, label, color in ELEC_FUELS:
            v = fuel_twh(self.elec_row, val_key)
            pct = (v / total * 100) if total > 0 and v > 0 else 0.0
            out.append((tag, label, color, v, pct, val_key))
        return out

    def elec_fuel_rows(self) -> list[tuple[str, float, float, str]]:
        return [
            (label, v, pct, color)
            for _tag, label, color, v, pct, _ in self.production_fuel_rows()
            if v > 0
        ]

    def solar_twh(self) -> float:
        return fuel_twh(self.elec_row, "solar_electricity") if self.elec_row else 0.0

    def wind_twh(self) -> float:
        return fuel_twh(self.elec_row, "wind_electricity") if self.elec_row else 0.0

    def rest_twh(self) -> float:
        elec = self.elec_total()
        rest = elec - self.solar_twh() - self.wind_twh()
        return rest if rest > 0 else 0.0

    def hydro_twh(self) -> float:
        return fuel_twh(self.elec_row, "hydro_electricity") if self.elec_row else 0.0

    def fossil_twh(self) -> float:
        if not self.elec_row:
            return 0.0
        fos = fval(self.elec_row, "fossil_electricity")
        if fos > 0:
            return fos
        return sum(
            fuel_twh(self.elec_row, k)
            for k, _, _, _, _ in ELEC_FUELS
            if k in ("gas_electricity", "coal_electricity", "oil_electricity")
        )

    def fuel_residual_twh(self) -> float:
        if not self.elec_row:
            return 0.0
        total = self.elec_total()
        summed = sum(fuel_twh(self.elec_row, k) for k, _, _, _, _ in ELEC_FUELS)
        return max(0.0, total - summed)

    def pri_fuel_sum(self) -> float:
        if not self.pri_row:
            return 0.0
        return sum(fval(self.pri_row, k) for k, _, _ in PRI_FUELS)

    def data_notes(self) -> list[str]:
        notes: list[str] = []
        er = self.elec_row or {}
        gen = self.elec_total()
        demand = fval(er, "electricity_demand")
        net = fval(er, "net_elec_imports")
        fos = self.fossil_twh()
        pri = fval(self.pri_row, "primary_energy_consumption")
        pri_sum = self.pri_fuel_sum()
        residual = self.fuel_residual_twh()

        notes.append(
            "Il mix e la tabella PROD misurano la generazione elettrica domestica (Ember/OWID), "
            "non il consumo finale ne l'energia primaria (gas da riscaldamento, trasporti, industria)."
        )
        if fos <= 0 and gen > 0:
            notes.append(
                "Nessuna generazione da gas/carbone/petrolio nell'anno: e plausibile per paesi "
                "quasi tutti idroelettrici (es. Albania). Il metano puo essere usato fuori dal settore elettrico."
            )
        if demand > 0 and gen > 0:
            notes.append(
                f"Bilancio elettrico {self.elec_year}: generazione {fmt_num(gen, 1)} TWh, "
                f"domanda {fmt_num(demand, 1)} TWh, import netti {fmt_num(net, 2)} TWh."
            )
        if residual > 0.05:
            notes.append(
                f"Quota non assegnata a singola fonte: {fmt_num(residual, 2)} TWh (arrotondamenti o dati incompleti OWID)."
            )
        if pri > 0 and pri_sum <= 0:
            notes.append(
                f"Energia primaria {fmt_num(pri, 1)} TWh ({self.pri_year}) senza dettaglio per fonte nel dataset."
            )
        return notes

    def pri_fuel_rows(self) -> list[tuple[str, float, float]]:
        if not self.pri_row:
            return []
        total = fval(self.pri_row, "primary_energy_consumption")
        out: list[tuple[str, float, float]] = []
        for val_key, share_key, label in PRI_FUELS:
            v = fval(self.pri_row, val_key)
            if v <= 0:
                continue
            share = fval(self.pri_row, share_key)
            if share <= 0 and total > 0:
                share = v / total * 100
            out.append((label, v, share))
        out.sort(key=lambda x: -x[1])
        return out

    def fossil_prod_rows(self) -> list[tuple[str, float, float]]:
        row = self.prod_row or self.pri_row
        if not row:
            return []
        out: list[tuple[str, float, float]] = []
        for val_key, chg_key, label in FOSSIL_PROD:
            v = fval(row, val_key)
            if v <= 0:
                continue
            chg = fval(row, chg_key)
            out.append((label, v, chg))
        return out

    def year_badges(self) -> str:
        parts = []
        if self.elec_year:
            parts.append(f"Elettr. {self.elec_year}")
        if self.pri_year:
            parts.append(f"Prim. {self.pri_year}")
        if self.prod_year and self.fossil_prod_rows():
            parts.append(f"Prod. {self.prod_year}")
        return "  ·  ".join(parts) if parts else "-"


@dataclass
class TradeFlows:
    year: int = 0
    reporter: str = ""
    imports: list[tuple[str, float]] = field(default_factory=list)
    exports: list[tuple[str, float]] = field(default_factory=list)
    import_total_twh: float = 0.0
    export_total_twh: float = 0.0

    @property
    def has_bilateral(self) -> bool:
        return bool(self.imports or self.exports)


def norm_name(name: str) -> str:
    s = sanitize(name).lower().strip()
    return NAME_ALIASES.get(s, s)


def is_trade_partner(partner: str, partner_name: str) -> bool:
    if partner in TRADE_AGG_PARTNERS:
        return False
    if partner_name.strip().lower() in {"total", "world", "extra-eu", "extra-ea"}:
        return False
    if len(partner) == 2 and partner.isalpha():
        return True
    return partner in ISO2_TO_ISO3


def load_trade_by_iso() -> dict[str, dict[int, TradeFlows]]:
    if not TRADE_CSV.exists():
        return {}

    buckets: dict[str, dict[str, dict[int, list[tuple[str, float]]]]] = {}
    with TRADE_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            reporter = row["reporter"].strip()
            iso3 = ISO2_TO_ISO3.get(reporter)
            if not iso3:
                continue
            partner = row["partner"].strip()
            partner_name = row["partner_name"].strip()
            if not is_trade_partner(partner, partner_name):
                continue
            year = int(row["year"])
            twh = float(row["twh"])
            if twh <= 0:
                continue
            direction = row["direction"]
            buckets.setdefault(iso3, {}).setdefault(direction, {}).setdefault(year, []).append(
                (partner_name, twh),
            )

    out: dict[str, dict[int, TradeFlows]] = {}
    for iso3, by_dir in buckets.items():
        years = set()
        for direction in by_dir.values():
            years.update(direction.keys())
        out[iso3] = {}
        for year in years:
            imports = sorted(by_dir.get("import", {}).get(year, []), key=lambda x: -x[1])
            exports = sorted(by_dir.get("export", {}).get(year, []), key=lambda x: -x[1])
            out[iso3][year] = TradeFlows(
                year=year,
                reporter=next((k for k, v in ISO2_TO_ISO3.items() if v == iso3), ""),
                imports=imports,
                exports=exports,
                import_total_twh=sum(v for _, v in imports),
                export_total_twh=sum(v for _, v in exports),
            )
    return out


def trade_for_country(iso3: str, prefer_year: int, trade_index: dict[str, dict[int, TradeFlows]]) -> TradeFlows:
    by_year = trade_index.get(iso3)
    if not by_year:
        return TradeFlows()
    if prefer_year in by_year:
        return by_year[prefer_year]
    year = max(y for y in by_year if y <= prefer_year) if any(y <= prefer_year for y in by_year) else max(by_year)
    return by_year[year]


def build_history(rows: list[dict]) -> list[YearPoint]:
    history: list[YearPoint] = []
    for r in sorted(rows, key=lambda x: int(x["year"])):
        yr = int(r["year"])
        elec = fval(r, "electricity_generation")
        pri = fval(r, "primary_energy_consumption")
        if elec <= 0 and pri <= 0:
            continue
        history.append(YearPoint(
            year=yr,
            elec_twh=elec,
            primary_twh=pri,
            solar_twh=fuel_twh(r, "solar_electricity"),
            wind_twh=fuel_twh(r, "wind_electricity"),
            rest_twh=max(0.0, elec - fuel_twh(r, "solar_electricity") - fuel_twh(r, "wind_electricity")),
            ren_pct=fval(r, "renewables_share_elec"),
            fossil_pct=fval(r, "fossil_share_elec"),
            low_carbon_pct=fval(r, "low_carbon_share_elec"),
            ghg_mt=fval(r, "greenhouse_gas_emissions"),
            demand_twh=fval(r, "electricity_demand"),
        ))
    return history


def load_countries() -> list[CountryProfile]:
    if not OWID_CSV.exists():
        raise FileNotFoundError(f"OWID CSV mancante: {OWID_CSV}")

    by_iso: dict[str, list[dict]] = {}
    with OWID_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not is_country_row(row):
                continue
            iso = row["iso_code"].strip()
            by_iso.setdefault(iso, []).append(row)

    profiles: list[CountryProfile] = []
    for iso, rows in by_iso.items():
        has_elec = any(fval(r, "electricity_generation") > 0 for r in rows)
        has_pri = any(fval(r, "primary_energy_consumption") > 0 for r in rows)
        if not has_elec and not has_pri:
            continue

        elec_row, elec_year = latest_row_with(rows, lambda r: fval(r, "electricity_generation") > 0)
        pri_row, pri_year = latest_row_with(rows, lambda r: fval(r, "primary_energy_consumption") > 0)
        prod_row, prod_year = latest_row_with(
            rows,
            lambda r: any(fval(r, k) > 0 for k, _, _ in FOSSIL_PROD),
        )
        meta_row, meta_year = latest_row_with(
            rows,
            lambda r: fval(r, "population") > 0 or fval(r, "gdp") > 0,
        )

        name = (elec_row or pri_row or meta_row or rows[-1])["country"]
        history = build_history(rows)
        if not history:
            continue

        profiles.append(CountryProfile(
            name=name,
            iso=iso,
            rows=rows,
            history=history,
            elec_row=elec_row,
            elec_year=elec_year,
            pri_row=pri_row,
            pri_year=pri_year,
            prod_row=prod_row,
            prod_year=prod_year,
            meta_row=meta_row or elec_row or pri_row,
            meta_year=meta_year or elec_year or pri_year,
        ))

    profiles.sort(key=lambda c: c.name.upper())
    return profiles


def tbl_style(header_bg: str = "#374151") -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#FFFFFF")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])


class FuelMixBar(Flowable):
    """Barra mix con legenda compatta sotto."""

    GAP_COLOR = "#E2E8F0"

    def __init__(self, fuels: list[tuple[str, float, float, str]], total: float, width: float):
        super().__init__()
        self.fuels = fuels
        self.total = total
        self.width = width
        self.bar_h = 10
        self.legend_lines = self._estimate_legend_lines()
        self.legend_h = max(8, self.legend_lines * 5 + 2)
        self.height = self.bar_h + 4 + self.legend_h

    def _estimate_legend_lines(self) -> int:
        if not self.fuels:
            return 0
        lx = 2.0
        lines = 1
        max_w = self.width - 4
        for label, _, pct, _ in self.fuels:
            txt = f"{label} {pct:.1f}%"
            tw = len(txt) * 3.1 + 12
            if lx + tw > max_w:
                lines += 1
                lx = 2.0
            lx += tw
        return lines

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        bar_total = self.total or sum(v for _, v, _, _ in self.fuels)
        if bar_total <= 0 or not self.fuels:
            return

        bar_y = self.legend_h + 4
        inner_x = 2.0
        inner_w = self.width - 4

        c.setFillColor(colors.HexColor("#F8FAFC"))
        c.roundRect(0, bar_y, self.width, self.bar_h, 2, fill=1, stroke=0)

        drawn = 0.0
        fuel_sum = sum(v for _, v, _, _ in self.fuels)
        scale_total = bar_total if fuel_sum <= bar_total * 1.01 else fuel_sum

        for i, (_, v, _, color) in enumerate(self.fuels):
            if i == len(self.fuels) - 1 and fuel_sum <= bar_total * 1.01:
                seg_w = inner_w - drawn
            else:
                seg_w = inner_w * v / scale_total
            seg_w = max(0.0, min(seg_w, inner_w - drawn))
            if seg_w <= 0:
                continue
            c.setFillColor(colors.HexColor(color))
            c.rect(inner_x + drawn, bar_y + 2, seg_w, self.bar_h - 4, fill=1, stroke=0)
            drawn += seg_w

        gap = inner_w - drawn
        if gap > 0.5:
            c.setFillColor(colors.HexColor(self.GAP_COLOR))
            c.rect(inner_x + drawn, bar_y + 2, gap, self.bar_h - 4, fill=1, stroke=0)

        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(0.4)
        c.roundRect(0, bar_y, self.width, self.bar_h, 2, fill=0, stroke=1)

        c.setFont("Helvetica", 4.8)
        lx, ly = 2.0, self.legend_lines * 6 - 2
        max_w = self.width - 4
        for label, _, pct, color in self.fuels:
            txt = f"{label} {pct:.1f}%"
            tw = c.stringWidth(txt, "Helvetica", 4.8) + 10
            if lx + tw > max_w:
                lx = 2.0
                ly -= 6
            c.setFillColor(colors.HexColor(color))
            c.circle(lx + 2, ly + 1.5, 2.0, fill=1, stroke=0)
            c.setFillColor(colors.HexColor("#475569"))
            c.drawString(lx + 6, ly, sanitize(txt))
            lx += tw


def chart_points_for_display(
    points: list[tuple[int, float]],
    *,
    trim_zeros: bool = False,
    max_years: int = 0,
) -> list[tuple[int, float]]:
    if not points:
        return []
    pts = sorted(points, key=lambda x: x[0])
    if trim_zeros:
        for i, (_y, v) in enumerate(pts):
            if v > 0:
                pts = pts[i:]
                break
    if max_years > 0 and len(pts) > max_years:
        pts = pts[-max_years:]
    return pts


class TrendChart(Flowable):
    """Serie temporale — header blu con testo bianco, area grafico scura."""

    HEADER_H = 18
    PLOT_BG = "#0c1f35"
    HEADER_BG = "#1e3a5f"
    GRID_COLOR = "#2d4a6b"
    AXIS_COLOR = "#E2E8F0"
    BORDER_COLOR = "#1e3a5f"

    def __init__(
        self,
        title: str,
        points: list[tuple[int, float]],
        width: float,
        height: float,
        *,
        color: str = "#60A5FA",
        fill_color: str | None = None,
        unit: str = "",
        pct_axis: bool = False,
    ):
        super().__init__()
        self.title = title
        self.points = sorted(points, key=lambda x: x[0])
        self.width = width
        self.height = height
        self.color = color
        self.fill_color = fill_color or color
        self.unit = unit
        self.pct_axis = pct_axis

    def wrap(self, aw, ah):
        return self.width, self.height

    def _fmt_val(self, val: float) -> str:
        if self.pct_axis:
            return f"{val:.0f}%"
        if val >= 10000:
            return f"{val/1000:.0f}k"
        if val >= 1000:
            return f"{val:.0f}"
        if val >= 100:
            return f"{val:.0f}"
        if val >= 10:
            return f"{val:.1f}"
        return f"{val:.2f}"

    def draw(self):
        c = self.canv
        h = self.height
        w = self.width
        hdr = self.HEADER_H

        c.setFillColor(colors.HexColor(self.PLOT_BG))
        c.setStrokeColor(colors.HexColor(self.BORDER_COLOR))
        c.setLineWidth(0.5)
        c.roundRect(0, 0, w, h, 3, fill=1, stroke=1)

        c.setFillColor(colors.HexColor(self.HEADER_BG))
        c.roundRect(0, h - hdr, w, hdr, 3, fill=1, stroke=0)
        c.rect(0, h - hdr, w, 4, fill=1, stroke=0)

        c.setFillColor(colors.white)

        if len(self.points) < 2:
            c.setFont("Helvetica", 6)
            c.setFillColor(colors.HexColor("#94A3B8"))
            c.drawCentredString(w / 2, (h - hdr) / 2, "Dati insufficienti")
            return

        last_y, last_v = self.points[-1]
        badge = f"{last_y}: {self._fmt_val(last_v)}"
        c.setFont("Helvetica-Bold", 5.5)
        title_txt = sanitize(self.title)
        title_w = c.stringWidth(title_txt, "Helvetica-Bold", 6)
        badge_w = c.stringWidth(badge, "Helvetica-Bold", 5.5)
        if title_w + badge_w > w - 14:
            badge = self._fmt_val(last_v)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(6, h - hdr + 5, title_txt)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawRightString(w - 6, h - hdr + 5, badge)

        years = [p[0] for p in self.points]
        vals = [p[1] for p in self.points]
        y_min = 0.0
        y_max = max(vals) * 1.15 or 1.0
        if self.pct_axis:
            y_max = min(100.0, max(vals) + 8)
            y_min = max(0.0, min(vals) - 8)
            if y_max - y_min < 15:
                y_min = max(0.0, y_max - 25)
            if y_max <= y_min:
                y_max = min(100.0, y_min + 20)
        x_min, x_max = years[0], years[-1]
        if x_max == x_min:
            x_max += 1

        c.setFont("Helvetica", 4.8)
        y_ticks = [y_min + (y_max - y_min) * i / 3 for i in range(4)]
        y_lbl_w = max(c.stringWidth(self._fmt_val(v), "Helvetica", 4.8) for v in y_ticks)
        pad_l = max(34.0, y_lbl_w + 10.0)
        pad_r = 8.0
        pad_b = 22.0
        plot_top = h - hdr - 8
        plot_w = w - pad_l - pad_r
        plot_h = plot_top - pad_b

        def px(year: int) -> float:
            return pad_l + (year - x_min) / (x_max - x_min) * plot_w

        def py(val: float) -> float:
            span = y_max - y_min or 1.0
            return pad_b + (val - y_min) / span * plot_h

        c.setStrokeColor(colors.HexColor(self.GRID_COLOR))
        c.setLineWidth(0.35)
        c.setFont("Helvetica", 4.8)
        for i in range(4):
            gy = pad_b + plot_h * i / 3
            c.line(pad_l, gy, pad_l + plot_w, gy)
            tick_val = y_ticks[i]
            lbl = self._fmt_val(tick_val)
            c.setFillColor(colors.HexColor(self.AXIS_COLOR))
            c.drawRightString(pad_l - 4, gy - 1.5, lbl)

        fill = colors.HexColor(self.fill_color)
        c.setFillColor(colors.Color(fill.red, fill.green, fill.blue, alpha=0.22))
        area = c.beginPath()
        area.moveTo(px(years[0]), pad_b)
        area.lineTo(px(years[0]), py(vals[0]))
        for i in range(1, len(years)):
            area.lineTo(px(years[i]), py(vals[i]))
        area.lineTo(px(years[-1]), pad_b)
        area.close()
        c.drawPath(area, fill=1, stroke=0)

        c.setStrokeColor(colors.HexColor(self.color))
        c.setLineWidth(1.4)
        path = c.beginPath()
        path.moveTo(px(years[0]), py(vals[0]))
        for i in range(1, len(years)):
            path.lineTo(px(years[i]), py(vals[i]))
        c.drawPath(path, fill=0, stroke=1)

        c.setFillColor(colors.HexColor(self.color))
        mark_step = max(1, len(years) // 10)
        for i, (year, val) in enumerate(zip(years, vals)):
            if i not in (0, len(years) - 1) and i % mark_step != 0:
                continue
            c.circle(px(year), py(val), 1.6, fill=1, stroke=0)

        span = x_max - x_min
        if span > 40:
            step = 10
        elif span > 20:
            step = 5
        elif span > 10:
            step = 2
        else:
            step = 0
        if step:
            first = ((x_min + step - 1) // step) * step
            x_ticks = list(range(first, x_max + 1, step))
            if years[0] not in x_ticks:
                x_ticks = [years[0]] + [t for t in x_ticks if t > years[0]]
            if years[-1] not in x_ticks:
                x_ticks.append(years[-1])
        else:
            x_ticks = [years[0]]
            if span > 8:
                x_ticks.append(years[len(years) // 2])
            x_ticks.append(years[-1])

        min_tick_px = 24.0
        filtered: list[int] = []
        for tick in x_ticks:
            if not filtered or px(tick) - px(filtered[-1]) >= min_tick_px:
                filtered.append(tick)
            elif tick == years[-1]:
                if px(tick) - px(filtered[-1]) < min_tick_px and len(filtered) > 1:
                    filtered[-1] = tick
                elif tick not in filtered:
                    filtered.append(tick)
        x_ticks = filtered

        c.setFillColor(colors.HexColor(self.AXIS_COLOR))
        c.setFont("Helvetica", 4.8)
        for tick in x_ticks:
            c.drawCentredString(px(tick), 7, str(tick))


class ChartGrid(Flowable):
    """Griglia 2x2 di grafici con gutter uniforme."""

    def __init__(self, specs: list[tuple], width: float, chart_h: float):
        super().__init__()
        cw = (width - COL_GAP) / 2
        self.charts = [
            TrendChart(title, points, cw, chart_h, color=color, fill_color=fill, unit=unit, pct_axis=pct)
            for title, points, color, fill, unit, pct in specs
        ]
        self.width = width
        self.chart_h = chart_h
        self.gap = COL_GAP
        self.height = chart_h * 2 + self.gap + 4

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        cw = (self.width - self.gap) / 2
        positions = [
            (0, self.chart_h + self.gap),
            (cw + self.gap, self.chart_h + self.gap),
            (0, 0),
            (cw + self.gap, 0),
        ]
        for chart, (x, y) in zip(self.charts, positions):
            self.canv.saveState()
            self.canv.translate(x, y)
            chart.canv = self.canv
            chart.draw()
            self.canv.restoreState()


class SectionHeader(Flowable):
    def __init__(self, title: str, width: float, subtitle: str = ""):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.width = width
        self.height = 16 if not subtitle else 20

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#1e3a5f"))
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(7, self.height - 12, sanitize(self.title))
        if self.subtitle:
            c.setFillColor(colors.HexColor("#CBD5E1"))
            c.setFont("Helvetica", 5.5)
            c.drawRightString(self.width - 7, self.height - 12, sanitize(self.subtitle))


PAGE_LABELS: dict[int, str] = {1: "Copertina"}


class CountryPageMarker(Flowable):
    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def wrap(self, avail_width, avail_height):
        return 0, 0

    def draw(self):
        pass


def register_page_label(flowable, doc):
    if isinstance(flowable, CountryPageMarker):
        PAGE_LABELS[doc.page] = flowable.label


def draw_footer(canvas, doc):
    label = PAGE_LABELS.get(doc.page, "Produzione per paese")
    canvas.saveState()
    canvas.setFont("Helvetica", 6)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawString(MARGIN_L, 1.0 * cm, f"STRAN OPS DESK  ·  {label}")
    canvas.drawRightString(A4[0] - MARGIN_R, 1.0 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def fmt_num(v: float, decimals: int = 1) -> str:
    if v <= 0:
        return "-"
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 100:
        return f"{v:.0f}"
    return f"{v:.{decimals}f}"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%" if v > 0 else "-"


def fmt_chg(v: float) -> str:
    if v == 0:
        return "-"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def hdr_cell(text: str, *, align=TA_LEFT, size: float = 6) -> Paragraph:
    return P(text, sty("th", size=size, bold=True, color="#FFFFFF", align=align))


def make_data_table(rows: list[list], col_widths: list[float], header_bg: str = "#374151") -> Table:
    t = Table(rows, colWidths=col_widths)
    t.setStyle(tbl_style(header_bg))
    return t


def build_fossil_prod_table(profile: CountryProfile, half: float) -> Table:
    fossil_prod = profile.fossil_prod_rows()
    rows = [[
        P("<b>Fonte</b>", sty("fp_h", size=6, bold=True)),
        P("<b>TWh</b>", sty("fp_h", size=6, bold=True, align=TA_RIGHT)),
        P("<b>Var.%</b>", sty("fp_h", size=6, bold=True, align=TA_RIGHT)),
    ]]
    if fossil_prod:
        for label, val, chg in fossil_prod:
            rows.append([
                P(label, sty("fp_r", size=5.8)),
                P(fmt_num(val, 1), sty("fp_v", size=5.8, align=TA_RIGHT)),
                P(fmt_chg(chg), sty("fp_c", size=5.8, align=TA_RIGHT)),
            ])
    else:
        rows.append([
            P("<i>Nessuna produzione fossile</i>", sty("fp_n", size=5.8)),
            P("-", sty("fp_e", size=5.8, align=TA_RIGHT)),
            P("-", sty("fp_e2", size=5.8, align=TA_RIGHT)),
        ])
    return make_data_table(rows, [half * 0.52, half * 0.24, half * 0.24], "#374151")


def build_pri_meta_table(profile: CountryProfile, width: float) -> Table:
    pr = profile.pri_row or {}
    rows = [[
        P("<b>Quote e aggregati primari</b>", sty("pm_h", size=6, bold=True)),
        P(f"<b>{profile.pri_year}</b>", sty("pm_y", size=6, bold=True, align=TA_RIGHT)),
    ]]
    for lbl, val, fmt in [
        ("Fossili % energia", fval(pr, "fossil_share_energy"), "pct"),
        ("Rinnovabili % energia", fval(pr, "renewables_share_energy"), "pct"),
        ("Low-carbon % energia", fval(pr, "low_carbon_share_energy"), "pct"),
        ("Elettricita su primaria", fval(pr, "electricity_share_energy"), "pct"),
        ("Fossili TWh", fval(pr, "fossil_fuel_consumption"), "num"),
        ("Rinnovabili TWh", fval(pr, "renewables_consumption"), "num"),
        ("Low-carbon TWh", fval(pr, "low_carbon_consumption"), "num"),
        ("Var. primaria YoY", fval(pr, "energy_cons_change_pct"), "chg"),
    ]:
        if val == 0 and fmt != "chg":
            continue
        if fmt == "pct":
            val_s = fmt_pct(val)
        elif fmt == "chg":
            val_s = fmt_chg(val)
        else:
            val_s = fmt_num(val, 1)
        rows.append([P(lbl, sty("pm_r", size=5.8)), P(val_s, sty("pm_v", size=5.8, align=TA_RIGHT))])
    return make_data_table(rows, [width * 0.55, width * 0.45], "#1e3a5f")


def build_production_kpi(profile: CountryProfile, width: float) -> Table:
    solar = profile.solar_twh()
    wind = profile.wind_twh()
    hydro = profile.hydro_twh()
    fossil = profile.fossil_twh()
    elec = profile.elec_total()

    def share(v: float) -> str:
        return fmt_pct((v / elec * 100) if elec > 0 else 0.0)

    cells = [
        (f"<font color='#B8860B'><b>SOL</b></font><br/><b>{fmt_num(solar, 2)}</b> TWh<br/>{share(solar)}", "#FFFBEB"),
        (f"<font color='#2563EB'><b>WIN</b></font><br/><b>{fmt_num(wind, 2)}</b> TWh<br/>{share(wind)}", "#EFF6FF"),
        (f"<font color='#0369A1'><b>HYD</b></font><br/><b>{fmt_num(hydro, 2)}</b> TWh<br/>{share(hydro)}", "#ECFEFF"),
        (
            f"<font color='#C2410C'><b>FOSSILI</b></font><br/>"
            f"<b>{fmt_num(fossil, 2) if fossil > 0 else '0'}</b> TWh<br/>{share(fossil) if fossil > 0 else '0.0%'}",
            "#FFF7ED",
        ),
    ]
    return Table(
        [[P(txt, sty(f"pk{i}", size=6.5, align=TA_CENTER)) for i, (txt, _) in enumerate(cells)]],
        colWidths=[width / 4] * 4,
        style=TableStyle([
            *[("BACKGROUND", (i, 0), (i, 0), colors.HexColor(bg)) for i, (_, bg) in enumerate(cells)],
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]),
    )


def build_terminal_prod_table(profile: CountryProfile, width: float) -> Table:
    """Tabella orizzontale stile terminale PROD: SOL WIN HYD NUC GAS COAL OIL BIO OTH + TOT."""
    fuels = profile.production_fuel_rows()
    elec = profile.elec_total()
    if not fuels:
        return Table([[P("-", sty("tp_e", size=6))]], colWidths=[width])

    ncol = len(fuels) + 1
    cw = width / ncol
    header = [hdr_cell(f"<b>{tag}</b>", align=TA_CENTER, size=5.5) for tag, _l, _c, _v, _p, _ in fuels]
    header.append(hdr_cell("<b>TOT</b>", align=TA_CENTER, size=5.5))
    values = [
        P(fmt_num(v, 1) if v > 0 else "-", sty("tp_v", size=6, align=TA_CENTER))
        for _tag, _label, _color, v, _pct, _ in fuels
    ]
    values.append(P(f"<b>{fmt_num(elec, 1)}</b>", sty("tp_t", size=6, bold=True, align=TA_CENTER)))
    labels = [
        P(label, sty("tp_l", size=4.8, color="#64748B", align=TA_CENTER))
        for _tag, label, _color, _v, _pct, _ in fuels
    ]
    labels.append(P("TWh", sty("tp_l", size=4.8, color="#64748B", align=TA_CENTER)))

    return Table([header, values, labels], colWidths=[cw] * ncol, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#FFFFFF")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F8FAFC")),
        ("BACKGROUND", (-1, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("BACKGROUND", (-1, 1), (-1, 1), colors.HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))


def build_production_detail_table(profile: CountryProfile, half: float) -> Table:
    """Dettaglio 9 fonti in ordine terminale con TWh e %."""
    fuels = profile.production_fuel_rows()
    rows_tbl = [[
        P("<b>Tag</b>", sty("pd_h", size=6, bold=True, align=TA_CENTER)),
        P("<b>Fonte</b>", sty("pd_h", size=6, bold=True)),
        P("<b>TWh</b>", sty("pd_h", size=6, bold=True, align=TA_RIGHT)),
        P("<b>%</b>", sty("pd_h", size=6, bold=True, align=TA_RIGHT)),
    ]]
    for tag, label, color, val, pct, _ in fuels:
        rows_tbl.append([
            P(f"<font color='{color}'><b>{tag}</b></font>", sty("pd_t", size=5.8, align=TA_CENTER)),
            P(label, sty("pd_l", size=5.8)),
            P(fmt_num(val, 2) if val > 0 else "-", sty("pd_v", size=5.8, align=TA_RIGHT)),
            P(fmt_pct(pct) if val > 0 else "-", sty("pd_p", size=5.8, align=TA_RIGHT)),
        ])
    elec = profile.elec_total()
    rows_tbl.append([
        P("<b>TOT</b>", sty("pd_tot", size=6, bold=True, align=TA_CENTER)),
        P("<b>Totale generazione</b>", sty("pd_tot", size=6, bold=True)),
        P(f"<b>{fmt_num(elec, 2)}</b>", sty("pd_totv", size=6, bold=True, align=TA_RIGHT)),
        P("<b>100%</b>", sty("pd_totp", size=6, bold=True, align=TA_RIGHT)),
    ])
    return make_data_table(rows_tbl, [half * 0.12, half * 0.38, half * 0.26, half * 0.24], "#1e3a5f")


def build_elec_balance_table(profile: CountryProfile, half: float) -> Table:
    er = profile.elec_row or {}
    gen = profile.elec_total()
    demand = fval(er, "electricity_demand")
    net = fval(er, "net_elec_imports")
    fos = profile.fossil_twh()
    ren = fval(er, "renewables_electricity")
    ghg = fval(er, "greenhouse_gas_emissions")
    ci = fval(er, "carbon_intensity_elec")
    pri = fval(profile.pri_row, "primary_energy_consumption")

    rows = [[
        hdr_cell("<b>Bilancio elettrico</b>"),
        hdr_cell(f"<b>{profile.elec_year}</b>", align=TA_RIGHT),
    ]]
    for lbl, val, unit in [
        ("Generazione domestica", gen, "TWh"),
        ("Domanda", demand, "TWh"),
        ("Import netti (+ = entra)", net, "TWh"),
        ("Fossili in generazione", fos, "TWh"),
        ("Rinnovabili in generazione", ren, "TWh"),
        ("Intensita carbonica", ci, "g"),
        ("Emissioni GHG settore", ghg, "Mt"),
        ("Energia primaria (tot.)", pri, "TWh"),
    ]:
        if val > 0 or lbl in ("Generazione domestica", "Domanda", "Fossili in generazione", "Emissioni GHG settore"):
            if unit == "g":
                val_s = f"{val:.0f} gCO2/kWh" if val > 0 else "-"
            elif unit == "Mt":
                val_s = fmt_num(val, 2)
            elif lbl == "Fossili in generazione" and val <= 0:
                val_s = "0"
            else:
                val_s = fmt_num(val, 2 if unit == "TWh" and val < 100 else 1)
            rows.append([P(lbl, sty("eb_r", size=5.6)), P(val_s, sty("eb_v", size=5.6, align=TA_RIGHT))])
    return make_data_table(rows, [half * 0.62, half * 0.38], "#374151")


def build_compact_trade_column(profile: CountryProfile, trade: TradeFlows, half: float) -> Table:
    er = profile.elec_row or {}
    net = fval(er, "net_elec_imports")
    rows = [[
        hdr_cell("<b>Scambi elettrici</b>"),
        hdr_cell(f"<b>{trade.year or profile.elec_year}</b>", align=TA_RIGHT),
    ]]
    if net > 0:
        rows.append([P("Saldo netto OWID", sty("ct_r", size=5.6)), P(f"+{fmt_num(net, 2)} TWh", sty("ct_v", size=5.6, align=TA_RIGHT))])
    elif net < 0:
        rows.append([P("Saldo netto OWID", sty("ct_r", size=5.6)), P(f"{fmt_num(net, 2)} TWh", sty("ct_v", size=5.6, align=TA_RIGHT))])
    else:
        rows.append([P("Saldo netto OWID", sty("ct_r", size=5.6)), P("-", sty("ct_v", size=5.6, align=TA_RIGHT))])

    if trade.has_bilateral:
        rows.append([
            P(f"<i>Import top ({fmt_num(trade.import_total_twh, 1)} TWh)</i>", sty("ct_s", size=5.4)),
            P("", sty("ct_e", size=5.4)),
        ])
        for name, val in trade.imports[:5]:
            rows.append([P(f"  {sanitize(name)}", sty("ct_r", size=5.4)), P(fmt_num(val, 2), sty("ct_v", size=5.4, align=TA_RIGHT))])
        rows.append([
            P(f"<i>Export top ({fmt_num(trade.export_total_twh, 1)} TWh)</i>", sty("ct_s", size=5.4)),
            P("", sty("ct_e2", size=5.4)),
        ])
        for name, val in trade.exports[:5]:
            rows.append([P(f"  {sanitize(name)}", sty("ct_r", size=5.4)), P(fmt_num(val, 2), sty("ct_v", size=5.4, align=TA_RIGHT))])
    else:
        rows.append([
            P("<i>Flussi bilaterali non in fonte aperta per questo paese (solo saldo netto OWID).</i>", sty("ct_na", size=5.4)),
            P("", sty("ct_e3", size=5.4)),
        ])
    return make_data_table(rows, [half * 0.62, half * 0.38], "#0f766e")


def build_compact_history_table(profile: CountryProfile, width: float, max_rows: int = 8) -> Table:
    hist = profile.history
    if len(hist) > max_rows:
        hist = hist[-max_rows:]
    rows_tbl = [[
        hdr_cell("<b>Anno</b>", align=TA_CENTER, size=5.2),
        hdr_cell("<b>Gen.</b>", align=TA_RIGHT, size=5.2),
        hdr_cell("<b>SOL</b>", align=TA_RIGHT, size=5.2),
        hdr_cell("<b>WIN</b>", align=TA_RIGHT, size=5.2),
        hdr_cell("<b>HYD</b>", align=TA_RIGHT, size=5.2),
        hdr_cell("<b>GAS</b>", align=TA_RIGHT, size=5.2),
        hdr_cell("<b>Foss.%</b>", align=TA_RIGHT, size=5.2),
    ]]
    for p in hist:
        er = next((r for r in profile.rows if int(float(r["year"])) == p.year), None)
        gas = fuel_twh(er, "gas_electricity") if er else 0.0
        hyd = fuel_twh(er, "hydro_electricity") if er else 0.0
        rows_tbl.append([
            P(str(p.year), sty("ch_r", size=5.0, align=TA_CENTER)),
            P(fmt_num(p.elec_twh, 1), sty("ch_r", size=5.0, align=TA_RIGHT)),
            P(fmt_num(p.solar_twh, 2) if p.solar_twh > 0 else "-", sty("ch_r", size=5.0, align=TA_RIGHT)),
            P(fmt_num(p.wind_twh, 2) if p.wind_twh > 0 else "-", sty("ch_r", size=5.0, align=TA_RIGHT)),
            P(fmt_num(hyd, 1) if hyd > 0 else "-", sty("ch_r", size=5.0, align=TA_RIGHT)),
            P(fmt_num(gas, 2) if gas > 0 else "-", sty("ch_r", size=5.0, align=TA_RIGHT)),
            P(fmt_pct(p.fossil_pct), sty("ch_r", size=5.0, align=TA_RIGHT)),
        ])
    cw = [width * 0.08, width * 0.14, width * 0.12, width * 0.12, width * 0.14, width * 0.12, width * 0.14]
    return make_data_table(rows_tbl, cw, "#1e3a5f")


def two_col_table(left: Table, right: Table) -> Table:
    half_l, half_r = col_widths()
    return Table(
        [[left, right]],
        colWidths=[half_l, half_r],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), COL_GAP / 2),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )


def mini_header(profile: CountryProfile, index: int, total: int) -> Table:
    w = usable_width()
    return Table([
        [P(f"<b>{sanitize(profile.name)}</b>  <font color='#64748B'>({profile.iso})</font>", sty("mh", size=9, bold=True)),
         P(f"{index}/{total}  ·  {profile.year_badges()}", sty("mh_r", size=6.5, color="#555", align=TA_RIGHT))],
    ], colWidths=[w * 0.68, w * 0.32], style=TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#CBD5E1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))


def cover_story(countries: list[CountryProfile], built: str, trade_index: dict) -> list:
    w = usable_width()
    elec_years = [c.elec_year for c in countries if c.elec_year]
    pri_years = [c.pri_year for c in countries if c.pri_year]
    trade_cov = sum(1 for c in countries if trade_for_country(c.iso, c.elec_year or c.pri_year, trade_index).has_bilateral)
    return [
        P("<b>Produzione energetica per paese</b>", sty("cv_t", size=15, color="#111", bold=True)),
        Spacer(1, 3 * mm),
        P(
            f"{len(countries)} paesi · OWID energy-data completo · aggiornato {built}",
            sty("cv_s", size=8.5, color="#444"),
        ),
        Spacer(1, 4 * mm),
        P(
            "Dati reali per paese: mix elettrico per fonte (TWh e % OWID), consumo primario per fonte, "
            "produzione fossile, domanda e import netti, intensita carbonica, emissioni GHG, "
            "indicatori per capita e serie storiche fino all'ultimo anno disponibile per ogni metrica.",
            sty("cv_b", size=7, color="#333"),
        ),
        Spacer(1, 4 * mm),
        Table([
            [P("<b>Copertura</b>", sty("cv_h", size=7.5, bold=True)), P("<b>Valore</b>", sty("cv_h2", size=7.5, bold=True))],
            [P("Paesi nel documento", sty("cv_r", size=7)), P(f"<b>{len(countries)}</b>", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Anno elettricita (max)", sty("cv_r", size=7)), P(f"<b>{max(elec_years) if elec_years else '-'}</b>", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Anno primaria (max)", sty("cv_r", size=7)), P(f"<b>{max(pri_years) if pri_years else '-'}</b>", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Colonne OWID usate", sty("cv_r", size=7)), P("122 metriche (mix, consumi, produzione, quote, storico)", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Scambi bilaterali (Eurostat)", sty("cv_r", size=7)), P(f"<b>{trade_cov}</b> paesi con import/export per partner", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Dataset OWID", sty("cv_r", size=7)), P(f"github.com/owid/energy-data", sty("cv_v", size=7, align=TA_RIGHT))],
            [P("Fonti", sty("cv_r", size=7)), P("Ember · Energy Institute · EIA · OWID · Eurostat", sty("cv_v", size=7, align=TA_RIGHT))],
        ], colWidths=[w * 0.55, w * 0.45], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])),
        Spacer(1, 5 * mm),
        P("<b>Legenda mix elettrico</b>", sty("cv_l", size=7.5, color="#111", bold=True)),
        Spacer(1, 1.5 * mm),
        Table(
            [[P(f"<font color='{color}'><b>■</b></font> <b>{tag}</b> {label}", sty("lg", size=6))
              for _vk, _sk, tag, label, color in ELEC_FUELS[i:i + 3]]
             for i in range(0, len(ELEC_FUELS), 3)],
            colWidths=[w / 3] * 3,
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]),
        ),
        Spacer(1, 4 * mm),
        P(
            "Una pagina per paese: generazione elettrica per fonte (stile terminale PROD), "
            "bilancio gen/domanda/import, scambi, storico e grafici. Fonti: Ember, Energy Institute, OWID, Eurostat.",
            sty("cv_n", size=6, color="#777", align=TA_CENTER),
        ),
    ]


def build_trade_table(
    title: str,
    flows: list[tuple[str, float]],
    half: float,
    *,
    empty_msg: str,
) -> Table:
    rows = [[
        P(f"<b>{title}</b>", sty("tr_h", size=6, bold=True)),
        P("<b>TWh</b>", sty("tr_h", size=6, bold=True, align=TA_RIGHT)),
        P("<b>%</b>", sty("tr_h", size=6, bold=True, align=TA_RIGHT)),
    ]]
    total = sum(v for _, v in flows)
    if flows:
        for name, val in flows[:12]:
            pct = (val / total * 100) if total > 0 else 0
            rows.append([
                P(sanitize(name), sty("tr_r", size=5.8)),
                P(fmt_num(val, 2), sty("tr_v", size=5.8, align=TA_RIGHT)),
                P(fmt_pct(pct), sty("tr_p", size=5.8, align=TA_RIGHT)),
            ])
        rows.append([
            P("<b>Totale</b>", sty("tr_t", size=6, bold=True)),
            P(f"<b>{fmt_num(total, 2)}</b>", sty("tr_tv", size=6, bold=True, align=TA_RIGHT)),
            P("<b>100%</b>", sty("tr_tp", size=6, bold=True, align=TA_RIGHT)),
        ])
    else:
        rows.append([
            P(f"<i>{empty_msg}</i>", sty("tr_n", size=5.8)),
            P("-", sty("tr_e", size=5.8, align=TA_RIGHT)),
            P("-", sty("tr_e2", size=5.8, align=TA_RIGHT)),
        ])
    return make_data_table(rows, [half * 0.56, half * 0.22, half * 0.22], "#0f766e")


def trade_story_block(
    profile: CountryProfile,
    trade: TradeFlows,
    w: float,
    half: float,
) -> list:
    er = profile.elec_row or {}
    net = fval(er, "net_elec_imports")
    net_note = ""
    if net > 0:
        net_note = f"Saldo netto OWID {profile.elec_year}: +{fmt_num(net, 2)} TWh (import nette)"
    elif net < 0:
        net_note = f"Saldo netto OWID {profile.elec_year}: {fmt_num(net, 2)} TWh (export nette)"

    if trade.has_bilateral:
        subtitle = (
            f"Anno {trade.year}  ·  Eurostat NRG_TI_EH/NRG_TE_EH  ·  "
            f"In {fmt_num(trade.import_total_twh, 2)} TWh  ·  Out {fmt_num(trade.export_total_twh, 2)} TWh"
        )
        imp_tbl = build_trade_table(
            "Import (da paese)",
            trade.imports,
            half,
            empty_msg="Nessun import registrato",
        )
        exp_tbl = build_trade_table(
            "Export (verso paese)",
            trade.exports,
            half,
            empty_msg="Nessun export registrato",
        )
        body = [
            SectionHeader("Scambi elettrici bilaterali", w, subtitle),
            Spacer(1, 1 * mm),
            two_col_table(imp_tbl, exp_tbl),
        ]
        if net_note:
            body += [
                Spacer(1, 2 * mm),
                P(net_note, sty("tr_net", size=6, color="#555")),
            ]
        body += [
            Spacer(1, 1 * mm),
            P(
                "Entrata = elettricita importata dal partner. Uscita = elettricita esportata verso il partner. "
                "Fonte Eurostat (GWh -> TWh). Copertura: ~42 paesi europei reporter.",
                sty("tr_note", size=5.5, color="#888"),
            ),
        ]
        return body

    lines = [
        SectionHeader("Scambi elettrici", w, f"Anno {profile.elec_year}"),
        Spacer(1, 1 * mm),
    ]
    if net_note:
        lines.append(P(net_note, sty("tr_net2", size=6.5, color="#333")))
    else:
        lines.append(P(
            "<i>Dati bilaterali partner-paese non disponibili in fonte aperta per questo territorio.</i>",
            sty("tr_na", size=6.5, color="#666"),
        ))
    lines += [
        Spacer(1, 1 * mm),
        P(
            "OWID riporta solo import/export netti aggregati. I flussi bilaterali (da/verso singolo paese) "
            "sono da Eurostat per l'Europa. Per altri continenti servirebbe IEA Electricity Information (a pagamento).",
            sty("tr_note2", size=5.5, color="#888"),
        ),
    ]
    return lines


def country_story(profile: CountryProfile, index: int, total: int, trade_index: dict) -> list:
    w = usable_width()
    half_l, _half_r = col_widths()
    half = half_l
    meta = profile.meta_row or {}
    pop = fval(meta, "population")
    pop_s = f"{pop / 1e6:.1f}M" if pop >= 1e6 else (f"{pop / 1e3:.0f}k" if pop > 0 else "-")
    elec = profile.elec_total()
    pri = fval(profile.pri_row, "primary_energy_consumption")
    page_label = f"{profile.name} ({profile.iso})  ·  {index}/{total}"
    trade = trade_for_country(profile.iso, profile.elec_year or profile.pri_year, trade_index)
    hist = profile.history
    hist_start = hist[0].year if hist else 0
    hist_end = hist[-1].year if hist else 0

    hdr = Table([
        [P(f"<b>{sanitize(profile.name)}</b>", sty("ch", size=12, color="#111", bold=True)),
         P(f"<b>{profile.iso}</b>  ·  {index}/{total}<br/>{profile.year_badges()}", sty("ch_r", size=6.5, color="#333", align=TA_RIGHT))],
        [P(f"Pop. {pop_s}  ·  Gen. {fmt_num(elec)} TWh  ·  Prim. {fmt_num(pri)} TWh", sty("ch_s", size=6, color="#555")),
         P("OWID energy-data · github.com/owid/energy-data", sty("ch_o", size=5.5, color="#888", align=TA_RIGHT))],
    ], colWidths=[w * 0.72, w * 0.28], style=TableStyle([
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#1e3a5f")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elec_fuels = [
        (label, v, pct, color)
        for _tag, label, color, v, pct, _ in profile.production_fuel_rows()
        if v > 0
    ]

    elec_pts = chart_points_for_display([(p.year, p.elec_twh) for p in hist if p.elec_twh > 0], max_years=40)
    solar_pts = chart_points_for_display([(p.year, p.solar_twh) for p in hist if p.solar_twh > 0], trim_zeros=True)
    wind_pts = chart_points_for_display([(p.year, p.wind_twh) for p in hist if p.wind_twh > 0], trim_zeros=True)
    gas_pts = chart_points_for_display([
        (int(float(r["year"])), fuel_twh(r, "gas_electricity"))
        for r in profile.rows
        if fuel_twh(r, "gas_electricity") > 0
    ], trim_zeros=True)

    chart_h = 2.65 * cm
    charts = ChartGrid([
        ("Generazione TWh", elec_pts, "#93C5FD", "#3B82F6", "TWh", False),
        ("Solare TWh", solar_pts, "#FDE68A", "#EAB308", "TWh", False),
        ("Eolico TWh", wind_pts, "#7DD3FC", "#38BDF8", "TWh", False),
        ("Gas TWh", gas_pts, "#FDBA74", "#F97316", "TWh", False),
    ], w, chart_h)

    notes = profile.data_notes()
    note_block = [
        P(" · ".join(notes[:2]), sty("dn1", size=5.2, color="#64748B")),
    ]
    if len(notes) > 2:
        note_block.append(P(" · ".join(notes[2:]), sty("dn2", size=5.2, color="#64748B")))

    mix_bar_block: list = []
    if elec_fuels:
        mix_bar_block = [FuelMixBar(elec_fuels, elec, w), Spacer(1, 1.5 * mm)]

    return [
        PageBreak(),
        CountryPageMarker(page_label),
        hdr,
        Spacer(1, 1.5 * mm),
        SectionHeader(
            "Generazione elettrica domestica per fonte",
            w,
            f"Anno {profile.elec_year}  ·  PROD: SOL WIN HYD NUC GAS COAL OIL BIO OTH",
        ),
        Spacer(1, 1 * mm),
        build_production_kpi(profile, w),
        Spacer(1, 1.5 * mm),
        build_terminal_prod_table(profile, w),
        Spacer(1, 1.5 * mm),
        *mix_bar_block,
        two_col_table(
            build_elec_balance_table(profile, half),
            build_compact_trade_column(profile, trade, half),
        ),
        Spacer(1, 2 * mm),
        SectionHeader("Storico", w, f"{hist_start}-{hist_end}"),
        Spacer(1, 1 * mm),
        charts,
        Spacer(1, 2 * mm),
        build_compact_history_table(profile, w, max_rows=6),
        Spacer(1, 1 * mm),
        *note_block,
    ]


def build_pdf(countries: list[CountryProfile], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    PAGE_LABELS.clear()
    PAGE_LABELS[1] = "Copertina"
    built = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    trade_index = load_trade_by_iso()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title="Produzione energetica per paese",
        author="STRAN OPS DESK",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.pageTemplates = []
    doc.addPageTemplates([
        PageTemplate(id="First", frames=[frame], onPageEnd=draw_footer, pagesize=A4),
        PageTemplate(id="Later", frames=[frame], onPageEnd=draw_footer, pagesize=A4),
    ])
    doc.afterFlowable = lambda f: register_page_label(f, doc)

    story = cover_story(countries, built, trade_index)
    total = len(countries)
    for i, c in enumerate(countries, start=1):
        story.extend(country_story(c, i, total, trade_index))

    BaseDocTemplate.build(doc, story)
    return doc.page


def main() -> int:
    countries = load_countries()
    if not countries:
        print("ERRORE: nessun paese caricato da OWID")
        return 1
    pages = build_pdf(countries, OUT)
    print(f"OK {OUT} ({len(countries)} paesi, {pages} pagine A4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
