#include "ingest_stooq.h"
#include "ingest_curl.h"
#include <stdlib.h>
#include <string.h>

static float stooq_atof(const char *s) {
    char tmp[32];
    int i, k = 0;

    if (!s) return 0.0f;
    for (i = 0; s[i] && k < (int)sizeof(tmp) - 1; i++) {
        if (s[i] == ',') tmp[k++] = '.';
        else if ((s[i] >= '0' && s[i] <= '9') || s[i] == '.' || s[i] == '-')
            tmp[k++] = s[i];
    }
    tmp[k] = 0;
    return (float)atof(tmp);
}

static void stooq_norm_sym(const char *in, char *out, int cap) {
    int i;

    if (!in || !out || cap < 2) {
        if (out && cap > 0) out[0] = 0;
        return;
    }
    for (i = 0; in[i] && i < cap - 1; i++) {
        char c = in[i];
        if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
        out[i] = c;
    }
    out[i] = 0;
}

static int stooq_sym_eq(const char *a, const char *b) {
    char na[24], nb[24];

    stooq_norm_sym(a, na, (int)sizeof(na));
    stooq_norm_sym(b, nb, (int)sizeof(nb));
    return lstrcmpA(na, nb) == 0;
}

static int stooq_parse_line(const char *line, char *sym, int sym_cap,
                            float *close, float *prev) {
    const char *cols[8];
    int n = 0;
    const char *p = line, *q;

    if (!line || !sym || !close) return 0;
    while (n < 8 && p && *p) {
        q = strchr(p, ',');
        if (q) {
            cols[n++] = p;
            p = q + 1;
        } else {
            cols[n++] = p;
            break;
        }
    }
    if (n < 5) return 0;
    {
        int sl = (int)strcspn(cols[0], ",\r\n");
        if (sl >= sym_cap) sl = sym_cap - 1;
        memcpy(sym, cols[0], (size_t)sl);
        sym[sl] = 0;
        stooq_norm_sym(sym, sym, sym_cap);
    }
    *close = stooq_atof(cols[4]);
    if (prev) {
        *prev = stooq_atof(cols[5]);
        if (*prev <= 0.0f) *prev = *close;
    }
    return *close > 0.0f;
}

typedef struct {
    float c, p;
    int   ok;
} StooqOneCtx;

static void stooq_one_cb(const char *sym, float c, float p, void *ctx) {
    StooqOneCtx *x = (StooqOneCtx *)ctx;
    (void)sym;
    x->c = c;
    x->p = p;
    x->ok = 1;
}

int ingest_stooq_batch(const char **symbols, int n, StooqFn fn, void *ctx) {
    wchar_t url[2048];
    char body[16384], sym[24], sym_list[1400];
    size_t len = 0;
    DWORD st = 0, err = 0;
    int i, got = 0;
    const char *line, *next;

    if (!symbols || n <= 0 || !fn) return 0;
    sym_list[0] = 0;
    for (i = 0; i < n && i < 16; i++) {
        if (i > 0) lstrcatA(sym_list, "+");
        lstrcatA(sym_list, symbols[i]);
    }
    wsprintfW(url, L"https://stooq.com/q/l/?s=%hs&i=d", sym_list);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 4)
        return 0;

    line = body;
    while (line && *line) {
        char row[280];
        float c, p;

        next = strchr(line, '\n');
        if (next) {
            int rl = (int)(next - line);
            if (rl >= (int)sizeof(row)) rl = (int)sizeof(row) - 1;
            memcpy(row, line, (size_t)rl);
            row[rl] = 0;
            line = next + 1;
        } else {
            lstrcpynA(row, line, (int)sizeof(row));
            line = NULL;
        }
        if (!stooq_parse_line(row, sym, (int)sizeof(sym), &c, &p)) continue;
        for (i = 0; i < n; i++) {
            if (stooq_sym_eq(sym, symbols[i])) {
                fn(symbols[i], c, p, ctx);
                got++;
                break;
            }
        }
    }
    return got;
}

BOOL ingest_stooq_quote(const char *symbol, float *out_close, float *out_prev) {
    StooqOneCtx ctx;
    const char *syms[1];

    if (!symbol || !out_close) return FALSE;
    syms[0] = symbol;
    ctx.ok = 0;
    ctx.c = ctx.p = 0.0f;
    if (ingest_stooq_batch(syms, 1, stooq_one_cb, &ctx) <= 0 || !ctx.ok)
        return FALSE;
    *out_close = ctx.c;
    if (out_prev) *out_prev = ctx.p;
    return TRUE;
}
