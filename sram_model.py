"""Behavioral cross-coupled inverter model; voltages are in V.

This model has no access devices, transistor I-V equations, or process calibration.
See docs/model.md for its scope and the diagonal SNM construction.
"""
from statistics import NormalDist
import numpy as np


def inverter_vtc(v_in, vdd=1.0, vth_n=0.4, vth_p=0.4, gain_per_v=14.0):
    if vdd <= 0 or gain_per_v <= 0:
        raise ValueError("vdd and gain_per_v must be positive")
    vm = (vdd - vth_p + vth_n) / 2
    z = np.clip(gain_per_v * (np.asarray(v_in) - vm), -700, 700)
    return vdd / (1 + np.exp(z))


def sample_thresholds(n=10000, mean_v=0.4, sigma_v=0.04, seed=42):
    """Four independent columns: n1, p1, n2, p2; preserve original draw order."""
    if n < 1 or sigma_v < 0:
        raise ValueError("n must be positive and sigma_v nonnegative")
    rng = np.random.RandomState(seed)  # local MT19937, compatible with original
    return np.column_stack([rng.normal(mean_v, sigma_v, n) for _ in range(4)])


def _lobe_snm(c, x1, x2):
    """Measure the two closed lobes between three butterfly intersections.

    A monostable pair has only one intersection and receives zero margin.
    Both columns of an inscribed square lie on y-x=c: side length = |x1-x2|.
    """
    d = x1 - x2
    crosses = np.signbit(d[:, :-1]) != np.signbit(d[:, 1:])
    count = crosses.sum(axis=1)
    rank = np.cumsum(crosses, axis=1)
    positions = np.arange(d.shape[1] - 1)[None, :]
    roots = [np.max(np.where(crosses & (rank == k), positions, -1), axis=1)
             for k in (1, 2, 3)]
    j = np.arange(d.shape[1])[None, :]
    left = (j > roots[0][:, None]) & (j <= roots[1][:, None])
    right = (j > roots[1][:, None]) & (j <= roots[2][:, None])
    a = np.max(np.where(left, np.abs(d), 0), axis=1)
    b = np.max(np.where(right, np.abs(d), 0), axis=1)
    return np.where(count == 3, np.minimum(a, b), 0.0)


def snm_batch(thresholds, vdd=1.0, gain_per_v=14.0,
              diagonal_points=1001, vtc_points=4097, batch_size=256):
    """Vectorized interpolation in bounded batches; returns one SNM per row.

    gain_per_v is fixed in physical voltage units across the supply sweep.
    Diagonal sweeps use the shared domain of the two physical VTCs.
    """
    t = np.atleast_2d(np.asarray(thresholds, dtype=float))
    if t.ndim != 2 or t.shape[1] != 4 or not np.isfinite(t).all():
        raise ValueError("thresholds must have shape (n, 4) with finite values")
    if vdd <= 0 or gain_per_v <= 0 or min(diagonal_points, vtc_points) < 5 or batch_size < 1:
        raise ValueError("positive voltage/gain/batch and grids >= 5 required")
    result = np.empty(len(t))
    for start in range(0, len(t), batch_size):
        a = t[start:start + batch_size]
        vm1 = (vdd - a[:, 1] + a[:, 0]) / 2
        vm2 = (vdd - a[:, 3] + a[:, 2]) / 2
        vm = np.r_[vm1, vm2]
        u = np.linspace(-vm.max(), vdd - vm.min(), vtc_points)
        f = vdd / (1 + np.exp(np.clip(gain_per_v * u, -700, 700)))
        f10 = inverter_vtc(0, vdd, a[:, 0], a[:, 1], gain_per_v)
        f11 = inverter_vtc(vdd, vdd, a[:, 0], a[:, 1], gain_per_v)
        f20 = inverter_vtc(0, vdd, a[:, 2], a[:, 3], gain_per_v)
        f21 = inverter_vtc(vdd, vdd, a[:, 2], a[:, 3], gain_per_v)
        lo, hi = np.maximum(f11 - vdd, -f20), np.minimum(f10, vdd - f21)
        c = lo[:, None] + (hi - lo)[:, None] * np.linspace(0, 1, diagonal_points)
        x1 = np.interp(c + vm1[:, None], (f-u)[::-1], u[::-1]) + vm1[:, None]
        x2 = np.interp(c - vm2[:, None], u-f, f)
        result[start:start + len(a)] = _lobe_snm(c, x1, x2)
    return result


def snm_reference(thresholds, vdd=1.0, gain_per_v=14.0, points=20001):
    """Independent scalar reference: invert each physical VTC by bisection.

    No shared interpolation table or production lobe routine is used.
    Returns SNM and butterfly/square coordinates for inspection.
    """
    n1, p1, n2, p2 = np.asarray(thresholds, dtype=float)
    f1 = lambda x: inverter_vtc(x, vdd, n1, p1, gain_per_v)
    f2 = lambda y: inverter_vtc(y, vdd, n2, p2, gain_per_v)
    c = np.linspace(max(f1(vdd)-vdd, -f2(0)), min(f1(0), vdd-f2(vdd)), points)
    low, high = np.zeros(points), np.full(points, vdd)
    for _ in range(48):
        mid = (low+high)/2
        mask = f1(mid)-mid > c
        low, high = np.where(mask, mid, low), np.where(mask, high, mid)
    x1 = (low+high)/2
    low, high = np.zeros(points), np.full(points, vdd)
    for _ in range(48):
        mid = (low+high)/2
        mask = mid-f2(mid) < c
        low, high = np.where(mask, mid, low), np.where(mask, high, mid)
    x2 = f2((low+high)/2)
    d = x1-x2
    roots = np.flatnonzero(np.signbit(d[:-1]) != np.signbit(d[1:]))
    squares = []
    if len(roots) == 3:
        for a, b in zip(roots[:-1], roots[1:]):
            k = a+1+np.argmax(np.abs(d[a+1:b+1]))
            x = min(x1[k], x2[k])
            squares.append((float(x), float(x+c[k]), float(abs(d[k]))))
    snm = min(s[2] for s in squares) if squares else 0.0
    v = np.linspace(0, vdd, 2001)
    return snm, {"v": v, "f1": f1(v), "f2": f2(v), "squares": squares,
                 "intersection_count": int(len(roots))}


def wilson_interval(k, n, confidence=0.95):
    """Two-sided Wilson score interval for a binomial proportion (NIST)."""
    if n <= 0 or not 0 <= k <= n or not 0 < confidence < 1:
        raise ValueError("require n > 0, 0 <= k <= n and confidence in (0, 1)")
    z = NormalDist().inv_cdf((1+confidence)/2)
    p = k/n
    denom = 1+z*z/n
    center = (p+z*z/(2*n))/denom
    half = z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return max(0., center-half), min(1., center+half)


def summarize(snm_v, threshold_v=0.18):
    a = np.asarray(snm_v)
    k, n = int(np.count_nonzero(a < threshold_v)), len(a)
    lo, hi = wilson_interval(k, n)
    return {"n": n, "mean_snm_mv": float(a.mean()*1000),
            "std_snm_mv": float(a.std(ddof=0)*1000),
            "p01_snm_mv": float(np.quantile(a, .01)*1000),
            "p50_snm_mv": float(np.quantile(a, .5)*1000),
            "below_threshold_count": k, "below_threshold_pct": 100*k/n,
            "ci95_low_pct": 100*lo, "ci95_high_pct": 100*hi}
