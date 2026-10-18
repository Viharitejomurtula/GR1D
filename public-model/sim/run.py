import sys, numpy as np
sys.path.insert(0, "."); from network import net
rng = np.random.default_rng(0); n = 5000
s = net.sample(n, rng)
f = lambda k, m=slice(None): s[k][m].mean()
print(f"P(IT failure)={f('it_failure'):.3f}  P(outage>0)={(s['psu_outage_s']>0).mean():.3f}  P(board trip)={f('board_trip'):.3f}  P(VFD trip)={f('cooling_vfd_trip'):.3f}")
print("do(bbu_ok=False): P(outage>0) = %.3f" % (net.sample(n, rng, do={'bbu_ok': False})['psu_outage_s'] > 0).mean())
seq = s['event_type'] == 1
print("P(fail|6-dip) %.3f  P(fail|isolated) %.3f" % (s['it_failure'][seq].mean(), s['it_failure'][~seq].mean()))
# sensitivity: |spearman| of each root-ish input vs outage seconds
def rank(a): return np.argsort(np.argsort(a)).astype(float)
def spearman(a, b): return np.corrcoef(rank(a), rank(b))[0, 1]
for k in ["load_frac", "cap_loss", "sts_detect_ms", "sts_present", "bbu_ok", "ton_s", "board_deglitch_ms", "vfd_ride_ms", "event_type"]:
    r = spearman(s[k].astype(float), s["psu_outage_s"]); print(f"{k:18} rho(vs PSU outage s)={r:+.2f}")
