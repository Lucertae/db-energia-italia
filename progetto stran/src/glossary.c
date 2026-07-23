#include "glossary.h"
#include "pages.h"

typedef struct {
    const wchar_t *k;
    const wchar_t *v;
} GlossKV;

typedef struct {
    const wchar_t *title;
    const GlossKV *kv;
    int n_kv;
    const wchar_t *refs;
} GlossBlock;

static void gloss_line(HDC dc, int x, int y, const wchar_t *k, const wchar_t *v, int w) {
    RECT kr = { x, y, x + 88, y + 13 };
    RECT vr = { x + 90, y, x + w, y + 13 };

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_ACC);
    DrawTextW(dc, (wchar_t *)k, -1, &kr, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);
    SetTextColor(dc, CLR_DIM);
    DrawTextW(dc, (wchar_t *)v, -1, &vr, DT_LEFT | DT_WORDBREAK | DT_NOPREFIX);
}

static int gloss_block(HDC dc, int x, int y, int w, const GlossBlock *b) {
    int i, dy = 0;

    if (!b || w < 120) return y;
    ui_subheading(dc, &(RECT){ x, y, x + w, y + 12 }, b->title);
    y += 14;
    for (i = 0; i < b->n_kv; i++) {
        gloss_line(dc, x, y, b->kv[i].k, b->kv[i].v, w);
        y += 26;
        dy += 26;
    }
    if (b->refs && b->refs[0]) {
        RECT rr = { x, y, x + w, y + 36 };
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        DrawTextW(dc, (wchar_t *)b->refs, -1, &rr, DT_LEFT | DT_WORDBREAK);
        y += 38;
    }
    return y;
}

static const GlossKV FX_KV[] = {
    { L"RV30%", L"Vol realizzata ann. su log-rend. 30gg x sqrt(252)" },
    { L"\x03C1 USD", L"Pearson 90d log-rend. vs EUR/USD" },
    { L"CIP FWD", L"F=S*exp((r_US-r_EA)*T); SOFR vs ECB DFR" },
    { L"2s10s", L"U10-U2 in bp; <0 = curva invertita" },
};

static const GlossKV NRG_KV[] = {
    { L"BRT-WTI", L"Arb fisico Atlantic; mean-revert ~$3-5" },
    { L"TTF/HH", L"Bridge gas EU-US; LNG arb proxy" },
    { L"COAL/TTF", L"Dark spread power; segnale margini" },
    { L"TTF/PDE", L"Spark spread gas-power DE (EUR/MWh)" },
    { L"\x03C1 90d", L"Correlazione rendimenti log giornalieri" },
};

static const GlossKV COR_KV[] = {
    { L"\x03C1", L"Correlazione Pearson su log-rend. allineati" },
    { L"\x03B2", L"Cov(r_a,r_b)/Var(r_b); hedge ratio OLS 90d" },
    { L"spillover", L"|rho| medio BTC vs energia; FinR 2026" },
    { L"stress", L"Mix VIX z, GPR, HY, curva, BTC-energy" },
};

static const GlossKV RSK_KV[] = {
    { L"GPR", L"Geopolitical Risk Index (Caldara-Iacoviello)" },
    { L"CPU", L"Climate Policy Uncertainty (Gavriilidis)" },
    { L"CVI", L"Crypto vol indice; RV BTC 30d ann." },
    { L"GRN/DIR", L"ICLN/XLE clean vs dirty energy ETF" },
    { L"VaR95", L"5o pctile rend. log 252d; perdita positiva %" },
    { L"RV", L"Vol realizzata log-ann su finestra 30d" },
};

static const GlossKV CRY_KV[] = {
    { L"basis", L"(Binance-Kraken)/mid in bp; arb >25bp" },
    { L"funding", L"Perp 8h; longs pagano se positivo" },
    { L"ETH/BTC", L"Beta alt; risk-on vs BTC" },
    { L"CBE", L"Cambridge Bitcoin Electricity Index GWh" },
};

static const GlossKV PRD_KV[] = {
    { L"TWh", L"Generazione elettrica per fonte (OWID)" },
    { L"Mtoe", L"Primary energy / 11.63 (TWh equiv.)" },
    { L"PWR DA", L"Prezzo day-ahead ENTSO-E/SMARD EUR/MWh" },
};

static const GlossKV CO_KV[] = {
    { L"\x03C1 SPX", L"Correlazione titolo vs S&P500 90d" },
    { L"CHG%", L"Variazione vs close precedente Stooq" },
    { L"TIER", L"MAJOR/NOC/UTIL/DIST segmentazione desk" },
};

static const GlossKV MKT_KV[] = {
    { L"spark", L"Storico 5y; punto live = ultimo tick" },
    { L"\x0394 1m", L"Variazione vs ~22 sedute fa" },
    { L"kind", L"NRG/FX/RATE/MACRO/CRYPTO da catalogo" },
};

void gloss_paint_panel(HDC dc, const RECT *rc, int page_id) {
    GlossBlock b;
    RECT fill = *rc;

    if (!dc || rc->right <= rc->left + 40) return;
    ui_fill(dc, &fill, bBand);
    memset(&b, 0, sizeof(b));

    switch (page_id) {
    case PAGE_NRG:
        b.title = L"PARAMETRI ENERGIA";
        b.kv = NRG_KV;
        b.n_kv = (int)(sizeof(NRG_KV) / sizeof(NRG_KV[0]));
        b.refs = L"Ref: Kilian (2009) oil; Bastianin et al. gas-power EU";
        break;
    case PAGE_RISK:
        b.title = L"PARAMETRI RISK";
        b.kv = RSK_KV;
        b.n_kv = (int)(sizeof(RSK_KV) / sizeof(RSK_KV[0]));
        b.refs = L"Ref: Caldara GPR; Gavriilidis CPU; Celik (2025) crypto-energy; MPRA clean/dirty";
        break;
    case PAGE_GEO:
        b.title = L"PARAMETRI PRD";
        b.kv = PRD_KV;
        b.n_kv = (int)(sizeof(PRD_KV) / sizeof(PRD_KV[0]));
        b.refs = L"Fonte: OWID Energy; EIA intl (se key); SMARD/ENTSO-E power";
        break;
    case PAGE_MKT:
        b.title = L"LEGGENDA";
        b.kv = MKT_KV;
        b.n_kv = (int)(sizeof(MKT_KV) / sizeof(MKT_KV[0]));
        b.refs = L"FRED/ECB/EIA cache 5y daily + live ECB FX";
        break;
    case PAGE_OPS:
        b.title = L"OPS DESK";
        b.kv = MKT_KV;
        b.n_kv = 3;
        b.refs = L"Panel live: ECB FX + FRED storico + spread energy";
        break;
    case PAGE_LAB:
        b.title = L"LAB";
        b.kv = MKT_KV;
        b.n_kv = 2;
        b.refs = L"Backtest JSON cache/spine/modules/backtest_pwr_v2.json";
        break;
    default:
        return;
    }
    gloss_block(dc, rc->left + 6, rc->top + 4, rc->right - rc->left - 10, &b);
}

void gloss_paint_footer(HDC dc, const RECT *rc, int page_id) {
    const wchar_t *txt = NULL;
    RECT r = *rc;

    switch (page_id) {
    case PAGE_RISK:
        txt = L"\x03C1/\x03B2 = log-rendimenti giornalieri  |  Football 52w + VaR95  |  stress composito";
        break;
    case PAGE_NRG:
        txt = L"Zone tile DA proxy  |  Heatmap ora x giorno  |  Spread engine horizon + pct 1y";
        break;
    case PAGE_FX:
        txt = L"Curva = ultimo fix U2/U5/U10/U30  |  Rete FX click per hub EUR  |  carry CIP";
        break;
    case PAGE_GEO:
        txt = L"Stack = mix % generazione elettrica OWID  |  Barre = prezzi power day-ahead";
        break;
    default:
        return;
    }
    if (!txt) return;
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    DrawTextW(dc, (wchar_t *)txt, -1, &r, DT_LEFT | DT_WORDBREAK);
}
