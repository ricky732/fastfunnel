import os, numpy as np

def _interp(x, xp, fp):  # np.interp su tutte le colonne insieme (xp crescente, anche con duplicati)
    i = np.clip(np.searchsorted(xp, x, 'right') - 1, 0, len(xp) - 2)
    w = np.clip((x - xp[i]) / np.where(xp[i + 1] > xp[i], xp[i + 1] - xp[i], np.inf), 0, 1)[:, None]
    return fp[i] * (1 - w) + fp[i + 1] * w

def _upper(x, xr, tx, f, B=64):  # bordo superiore dell'unione dei rettangoli (xr±tx, f) collegati lungo la curva
    l, r = np.searchsorted(xr + tx, x), np.searchsorted(xr - tx, x, 'right')
    k = np.log2(np.maximum(r - l, 1)).astype(int); a, b = np.minimum(l, len(xr) - 1), np.maximum(r - 2**k, 0)
    out = np.maximum(_interp(x, xr - tx, f), _interp(x, xr + tx, f))
    for c in range(0, f.shape[1], B):  # sparse table (max su finestre) a blocchi di colonne
        S = [f[:, c:c+B]]
        for j in range(k.max()): S.append(np.maximum(S[-1], np.vstack([S[-1][2**j:], S[-1][-2**j:]])))
        S = np.stack(S); top = np.maximum(S[k, a], S[k, b]); top[l >= r] = -np.inf
        out[:, c:c+B] = np.maximum(out[:, c:c+B], top)
    return out

def compareAndReport(xReference, yReference, xTest, yTest, outputDirectory=None, atolx=0, atoly=0,
                     ltolx=0, ltoly=0, rtolx=0, rtoly=0, names=None):
    """yReference/yTest: (n,) oppure (n, nVar). Ritorna array bool (True = variabile fallita).
    Se outputDirectory è dato, scrive <nome>.csv SOLO per le variabili fallite."""
    xr, xt = np.asarray(xReference, float), np.asarray(xTest, float)
    yr, yt = np.asarray(yReference, float).reshape(len(xr), -1), np.asarray(yTest, float).reshape(len(xt), -1)
    tx = np.maximum(max(atolx, rtolx * np.ptp(xr)), ltolx * np.abs(xr))
    ty = np.maximum(np.maximum(atoly, rtoly * np.ptp(yr, 0)), ltoly * np.abs(yr))
    tx[tx == 0] = max(rtolx * max(xr.max(), -xr.min()), 1e-10)  # stessi fallback del C
    ty = np.where(ty == 0, np.maximum(rtoly * np.maximum(yr.max(0), -yr.min(0)), 1e-10), ty)
    up, lo = _upper(xt, xr, tx, yr + ty), -_upper(xt, xr, tx, ty - yr)
    err = np.maximum(yt - up, 0) + np.maximum(lo - yt, 0)
    fail = (err > 0).any(0)
    for j in np.flatnonzero(fail) if outputDirectory else []:
        os.makedirs(outputDirectory, exist_ok=True)
        np.savetxt(os.path.join(outputDirectory, f'{names[j] if names is not None else j}.csv'),
                   np.c_[xt, yt[:, j], lo[:, j], up[:, j], err[:, j]], delimiter=',',
                   header='x,test,lowerBound,upperBound,error', comments='')
    return fail
