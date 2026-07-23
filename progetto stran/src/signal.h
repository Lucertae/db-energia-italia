#ifndef SIGNAL_H
#define SIGNAL_H

#include <stdint.h>

#define SIG_MAX_CH   48
#define SIG_RING     96
#define SIG_ALPHA_F  0.35
#define SIG_ALPHA_S  0.08
#define SIG_ALPHA_N  0.20
#define SIG_MIN_BP   0.0003

typedef struct {
    char     id[4];
    double   raw;
    double   signal;
    double   ema_f;
    double   ema_s;
    double   noise;
    double   last_emit;
    uint32_t last_emit_t;
    uint32_t ticks_in;
    uint32_t ticks_out;
    int      n_comp;
    int32_t  comp_delta[SIG_RING];
    uint16_t comp_dt[SIG_RING];
} SigChannel;

typedef struct {
    SigChannel ch[SIG_MAX_CH];
    int        n_ch;
    uint64_t   total_in;
    uint64_t   total_out;
} SigBus;

void       sig_bus_init(SigBus *b);
SigChannel *sig_channel(SigBus *b, const char *iso3);
int        sig_push(SigBus *b, const char *iso3, double raw, uint32_t epoch_sec);
double     sig_value(const SigBus *b, const char *iso3);
void       sig_stats(const SigBus *b, double *compress_ratio, double *avg_noise_bp);

#endif
