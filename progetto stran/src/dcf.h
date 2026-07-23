#ifndef DCF_H
#define DCF_H

/* long double kernel — deterministic, no heap */

typedef long double ldf;

ldf dcf_exp_ld(ldf x);
ldf dcf_ln_ld(ldf x);
ldf dcf_pow_ld(ldf b, ldf e);

ldf dcf_df(ldf rate_annual, ldf t_years);
ldf dcf_cip_forward(ldf spot, ldf r_dom, ldf r_for, ldf t_years);
ldf dcf_npv(const ldf *cf, const ldf *t, int n, ldf wacc);

#endif
