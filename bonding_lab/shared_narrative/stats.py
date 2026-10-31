"""Seed-level bootstrap summaries. Seeds are the independent unit."""
import numpy as np

QUANTILES = (.05, .10, .25, .50, .75, .90, .95)


def bootstrap(values, stat=np.mean, n=2000, seed=7):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(len(v), size=(n, len(v)))
    boots = stat(v[idx], axis=1)
    return float(stat(v)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def describe(values, prefix=""):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    mean, lo, hi = bootstrap(v, np.mean)
    med, mlo, mhi = bootstrap(v, np.median)
    out = {f"{prefix}n": len(v), f"{prefix}mean": mean, f"{prefix}mean_lo": lo, f"{prefix}mean_hi": hi,
           f"{prefix}median": med, f"{prefix}median_lo": mlo, f"{prefix}median_hi": mhi,
           f"{prefix}min": float(v.min()) if len(v) else np.nan, f"{prefix}max": float(v.max()) if len(v) else np.nan}
    for q in QUANTILES:
        out[f"{prefix}q{int(q*100):02d}"] = float(np.quantile(v, q)) if len(v) else np.nan
    return out


def cluster_bootstrap(values, clusters, stat, n=1000, seed=11):
    """Resample whole seeds (clusters) for statistics of pooled per-creator data."""
    values = np.asarray(values, dtype=float)
    clusters = np.asarray(clusters)
    keys, inv = np.unique(clusters, return_inverse=True)
    groups = [values[inv == k] for k in range(len(keys))]
    rng = np.random.default_rng(seed)
    point = stat(values)
    boots = []
    for _ in range(n):
        pick = rng.integers(len(groups), size=len(groups))
        boots.append(stat(np.concatenate([groups[i] for i in pick])))
    return float(point), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def cara_ce(x, a):
    """Certainty equivalent under CARA utility with absolute risk aversion a ($^-1)."""
    x = np.asarray(x, dtype=float)
    z = -a*x
    m = z.max()
    return float(-(m+np.log(np.mean(np.exp(z-m))))/a)


def ssd_dominates(x, y, grid=400):
    """True if x second-order stochastically dominates y: E[(g-X)+] <= E[(g-Y)+] for all g."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    g = np.unique(np.concatenate([np.quantile(x, np.linspace(0, 1, grid)), np.quantile(y, np.linspace(0, 1, grid))]))
    ix = np.array([np.maximum(v-x, 0).mean() for v in g])
    iy = np.array([np.maximum(v-y, 0).mean() for v in g])
    return bool(np.all(ix <= iy+1e-9*(1+np.abs(iy))))
