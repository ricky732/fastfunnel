import os, numpy as np

def _envelope(x, xr, f, tx, ty):
    """Bordo superiore dell'ellisse (tx, ty) fatta scorrere lungo la polilinea (xr, f)."""
    n = len(xr)
    dxr, df = np.diff(xr), np.diff(f)
    a, b = (tx[:-1] + tx[1:]) / 2, (ty[:-1] + ty[1:]) / 2   # semiassi medi del tratto
    ok = dxr > 0                                            # tratti verticali (eventi): solo archi
    m = np.where(ok, df / np.where(ok, dxr, 1), 0)
    d = np.hypot(m * a, b)
    sx, sy = -m * a * a / d, b * b / d                      # punto di tangenza
    l, r = np.searchsorted(xr + tx, x), np.searchsorted(xr - tx, x, 'right')
    up = np.full(x.shape, -np.inf)
    for j in range(-1, int((r - l).max(initial=0)) + 1):
        i = np.clip(l + j, 0, n - 1)                        # archi di ellisse sui vertici
        q = (x - xr[i]) / tx[i]
        up = np.maximum(up, np.where(np.abs(q) <= 1,
                        f[i] + ty[i] * np.sqrt(np.clip(1 - q * q, 0, None)), -np.inf))
        s = np.clip(l + j, 0, n - 2)                        # segmenti traslati
        u = x - xr[s] - sx[s]
        up = np.maximum(up, np.where(ok[s] & (u >= 0) & (u <= dxr[s]),
                        f[s] + sy[s] + m[s] * u, -np.inf))
    return up

def compareAndReport(xReference, yReference, xTest, yTest, outputDirectory=None,
                     atolx=0, atoly=0, ltolx=0, ltoly=0, rtolx=0, rtoly=0):
    """Una variabile, come pyfunnel (funnel ellittico). Ritorna True se fallisce."""
    xr, yr, xt, yt = (np.asarray(v, float) for v in (xReference, yReference, xTest, yTest))
    tx = np.maximum(max(atolx, rtolx * np.ptp(xr)), ltolx * np.abs(xr))
    ty = np.maximum(max(atoly, rtoly * np.ptp(yr)), ltoly * np.abs(yr))
    tx[tx == 0] = max(rtolx * max(xr.max(), -xr.min()), 1e-10)
    ty[ty == 0] = max(rtoly * max(yr.max(), -yr.min()), 1e-10)
    up, lo = _envelope(xt, xr, yr, tx, ty), -_envelope(xt, xr, -yr, tx, ty)
    err = np.maximum(yt - up, 0) + np.maximum(lo - yt, 0)
    if err.any() and outputDirectory:
        os.makedirs(outputDirectory, exist_ok=True)
        np.savetxt(os.path.join(outputDirectory, 'errors.csv'), np.c_[xt, yt, lo, up, err],
                   delimiter=',', header='x,test,lowerBound,upperBound,error', comments='')
    return bool(err.any())


