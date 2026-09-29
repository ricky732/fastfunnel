import os, numpy as np

def _upper(x, xr, tx, f):  # bordo superiore dell'unione dei rettangoli (xr±tx, f) collegati lungo la curva
    l, r = np.searchsorted(xr + tx, x), np.searchsorted(xr - tx, x, 'right')
    k = np.log2(np.maximum(r - l, 1)).astype(int)
    S = [f]  # sparse table: S[j][i] = max(f[i : i+2^j])
    for j in range(k.max()): S.append(np.maximum(S[-1], np.r_[S[-1][2**j:], S[-1][-2**j:]]))
    S = np.stack(S); top = np.maximum(S[k, np.minimum(l, len(xr) - 1)], S[k, np.maximum(r - 2**k, 0)])
    return np.maximum(np.where(l < r, top, -np.inf), np.maximum(np.interp(x, xr - tx, f), np.interp(x, xr + tx, f)))

def compareAndReport(xReference, yReference, xTest, yTest, outputDirectory=None,
                     atolx=0, atoly=0, ltolx=0, ltoly=0, rtolx=0, rtoly=0):
    """Una variabile, come pyfunnel. Ritorna True se fallisce; scrive errors.csv solo se fallisce e outputDirectory è dato."""
    xr, yr, xt, yt = (np.asarray(v, float) for v in (xReference, yReference, xTest, yTest))
    tx = np.maximum(max(atolx, rtolx * np.ptp(xr)), ltolx * np.abs(xr))
    ty = np.maximum(max(atoly, rtoly * np.ptp(yr)), ltoly * np.abs(yr))
    tx[tx == 0] = max(rtolx * max(xr.max(), -xr.min()), 1e-10)  # stessi fallback del C
    ty[ty == 0] = max(rtoly * max(yr.max(), -yr.min()), 1e-10)
    up, lo = _upper(xt, xr, tx, yr + ty), -_upper(xt, xr, tx, ty - yr)
    err = np.maximum(yt - up, 0) + np.maximum(lo - yt, 0)
    if err.any() and outputDirectory:
        os.makedirs(outputDirectory, exist_ok=True)
        np.savetxt(os.path.join(outputDirectory, 'errors.csv'), np.c_[xt, yt, lo, up, err], delimiter=',',
                   header='x,test,lowerBound,upperBound,error', comments='')
    return bool(err.any())

