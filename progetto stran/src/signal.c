#include "signal.h"
#include <math.h>
#include <string.h>

static int32_t zigzag(int32_t v) {
    return (v << 1) ^ (v >> 31);
}

static void sig_store(SigChannel *c, double val, uint32_t t) {
    int32_t delta_fp, prev_fp;
    int idx;
    uint32_t dt;

    if (c->n_comp > 0) {
        prev_fp = (int32_t)(c->last_emit * 1000000.0 + (val >= 0 ? 0.5 : -0.5));
        delta_fp = (int32_t)(val * 1000000.0 + (val >= 0 ? 0.5 : -0.5)) - prev_fp;
    } else {
        delta_fp = (int32_t)(val * 1000000.0 + (val >= 0 ? 0.5 : -0.5));
    }
    dt = c->last_emit_t ? (t > c->last_emit_t ? t - c->last_emit_t : 0) : 0;
    idx = c->n_comp % SIG_RING;
    c->comp_delta[idx] = zigzag(delta_fp);
    c->comp_dt[idx] = dt > 65535u ? 65535u : (uint16_t)dt;
    c->n_comp++;
    c->ticks_out++;
    c->last_emit = val;
    c->last_emit_t = t;
}

void sig_bus_init(SigBus *b) {
    memset(b, 0, sizeof(*b));
}

SigChannel *sig_channel(SigBus *b, const char *iso3) {
    int i;

    for (i = 0; i < b->n_ch; i++) {
        if (b->ch[i].id[0] == iso3[0] && b->ch[i].id[1] == iso3[1] &&
            b->ch[i].id[2] == iso3[2])
            return &b->ch[i];
    }
    if (b->n_ch >= SIG_MAX_CH) return NULL;
    i = b->n_ch++;
    memset(&b->ch[i], 0, sizeof(b->ch[i]));
    b->ch[i].id[0] = iso3[0];
    b->ch[i].id[1] = iso3[1];
    b->ch[i].id[2] = iso3[2];
    b->ch[i].id[3] = 0;
    return &b->ch[i];
}

int sig_push(SigBus *b, const char *iso3, double raw, uint32_t epoch_sec) {
    SigChannel *c;
    double band, rel_floor;

    c = sig_channel(b, iso3);
    if (!c) return 0;

    b->total_in++;
    c->ticks_in++;
    c->raw = raw;

    if (c->ticks_in == 1) {
        c->ema_f = c->ema_s = c->signal = raw;
        c->noise = fabs(raw) * 1e-6 + 1e-9;
        sig_store(c, raw, epoch_sec);
        b->total_out++;
        return 1;
    }

    c->ema_f = SIG_ALPHA_F * raw + (1.0 - SIG_ALPHA_F) * c->ema_f;
    c->ema_s = SIG_ALPHA_S * raw + (1.0 - SIG_ALPHA_S) * c->ema_s;
    c->noise = SIG_ALPHA_N * fabs(raw - c->ema_f) + (1.0 - SIG_ALPHA_N) * c->noise;
    if (c->noise < 1e-12) c->noise = 1e-12;

    c->signal = c->ema_f;

    rel_floor = fabs(c->signal) * SIG_MIN_BP;
    band = 2.5 * c->noise;
    if (band < rel_floor) band = rel_floor;

    if (fabs(c->signal - c->last_emit) >= band) {
        sig_store(c, c->signal, epoch_sec);
        b->total_out++;
        return 1;
    }
    return 0;
}

double sig_value(const SigBus *b, const char *iso3) {
    int i;

    for (i = 0; i < b->n_ch; i++) {
        if (b->ch[i].id[0] == iso3[0] && b->ch[i].id[1] == iso3[1] &&
            b->ch[i].id[2] == iso3[2])
            return b->ch[i].signal;
    }
    return 0.0;
}

void sig_stats(const SigBus *b, double *compress_ratio, double *avg_noise_bp) {
    int i, n = 0;
    double sum_bp = 0.0;

    if (compress_ratio) {
        if (b->total_out == 0)
            *compress_ratio = 1.0;
        else
            *compress_ratio = (double)b->total_in / (double)b->total_out;
    }
    if (avg_noise_bp) {
        for (i = 0; i < b->n_ch; i++) {
            if (b->ch[i].ticks_in == 0) continue;
            if (fabs(b->ch[i].signal) > 1e-12)
                sum_bp += (b->ch[i].noise / fabs(b->ch[i].signal)) * 10000.0;
            n++;
        }
        *avg_noise_bp = n ? sum_bp / n : 0.0;
    }
}
