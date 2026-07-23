#include "dcf.h"
#include <math.h>

ldf dcf_exp_ld(ldf x) {
    return expl(x);
}

ldf dcf_ln_ld(ldf x) {
    return x > 0.0L ? logl(x) : 0.0L;
}

ldf dcf_pow_ld(ldf b, ldf e) {
    return powl(b, e);
}

ldf dcf_df(ldf rate_annual, ldf t_years) {
    return dcf_exp_ld(-rate_annual * t_years);
}

ldf dcf_cip_forward(ldf spot, ldf r_dom, ldf r_for, ldf t_years) {
    return spot * dcf_exp_ld((r_dom - r_for) * t_years);
}

ldf dcf_npv(const ldf *cf, const ldf *t, int n, ldf wacc) {
    ldf sum = 0.0L;
    int i;

    for (i = 0; i < n; i++)
        sum += cf[i] * dcf_df(wacc, t[i]);
    return sum;
}
