"""
AstroFlyer HEO - NRLMSISE-00 atmosphere in double precision

A line-by-line port of the public-domain NRLMSISE-00 C release 20041227
(D. Brodowski), itself a translation of the NRL Fortran model by M. Picone,
A. Hedin and D. Drob. US Government work, not subject to copyright
(17 U.S.C. 105); this port is not endorsed by or affiliated with NRL.

Why not pymsis: it runs the model in single precision, so the density jitters
by ~1e-6 between points millimetres apart. Under drag that jitter defeats an
adaptive integrator (metres per day at a 250 km GTO perigee, different on each
computer). This port keeps every step in float64, so the density is smooth.

Function and variable names follow the C source so the two can be compared.
The C file-level shared variables live in `st` (scalars) and the `plg`, `tn*`
and `tgn*` arrays, created per call. Units follow the C code: altitude km,
latitude/longitude deg, local solar time h, seconds of UT day; densities in
cm^-3 and g/cm^3, or m^-3 and kg/m^3 when switch 0 is 1.
"""

import math

import numpy as np

try:
    from numba import njit
except ImportError:  # pure NumPy fallback
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]
        return lambda f: f

from .nrlmsise00_data import PT, PD, PS, PDL, PTL, PMA, PTM, PDM, PAVGM

# Geodetic altitudes (km) where the model switches terms on or off (altl, the 300 km lower-
# thermosphere switch, za, and the 72.5 km mesosphere join), so the density jumps there:
# up to ~3e-4 at 160 km and ~6e-5 at 300 km. The propagator restarts at each one.
DISCONTINUITY_ALTITUDES_KM = tuple(sorted({72.5, float(PDL[1, 15]), 160.0, 200.0, 240.0, 250.0,
                                           300.0, 320.0, 450.0}))

# Indices of the shared scalars in `st`
_GSURF, _RE, _DFA, _APDF, _CTLOC, _STLOC, _C2TLOC, _S2TLOC, _C3TLOC, _S3TLOC, _APT0, _DM28 = range(12)
# Indices of the input vector
_DOY, _SEC, _ALT, _LAT, _LON, _LST, _F107A, _F107, _AP = range(9)


@njit(cache=False)
def _tselec(switches, sw, swc):
    for i in range(24):
        if i != 9:
            sw[i] = 1.0 if switches[i] == 1 else 0.0
            swc[i] = 1.0 if switches[i] > 0 else 0.0
        else:
            sw[i] = switches[i]
            swc[i] = switches[i]


@njit(cache=False)
def _glatf(lat, st):
    dgtr = 1.74533E-2
    c2 = math.cos(2.0 * dgtr * lat)
    st[_GSURF] = 980.616 * (1.0 - 0.0026373 * c2)
    st[_RE] = 2.0 * st[_GSURF] / (3.085462E-6 + 2.27E-9 * c2) * 1.0E-5


@njit(cache=False)
def _ccor(alt, r, h1, zh):
    e = (alt - zh) / h1
    if e > 70:
        return 1.0
    if e < -70:
        return math.exp(r)
    ex = math.exp(e)
    return math.exp(r / (1.0 + ex))


@njit(cache=False)
def _ccor2(alt, r, h1, zh, h2):
    e1 = (alt - zh) / h1
    e2 = (alt - zh) / h2
    if e1 > 70 or e2 > 70:
        return 1.0
    if e1 < -70 and e2 < -70:
        return math.exp(r)
    ex1 = math.exp(e1)
    ex2 = math.exp(e2)
    return math.exp(r / (1.0 + 0.5 * (ex1 + ex2)))


@njit(cache=False)
def _scalh(alt, xm, temp, st):
    rgas = 831.4
    g = st[_GSURF] / ((1.0 + alt / st[_RE]) ** 2)
    return rgas * temp / (g * xm)


@njit(cache=False)
def _dnet(dd, dm, zhm, xmm, xm):
    a = zhm / (xmm - xm)
    if not (dm > 0 and dd > 0):
        if dd == 0 and dm == 0:
            dd = 1.0
        if dm == 0:
            return dd
        if dd == 0:
            return dm
    ylog = a * math.log(dm / dd)
    if ylog < -10:
        return dd
    if ylog > 10:
        return dm
    return dd * (1.0 + math.exp(ylog)) ** (1.0 / a)


@njit(cache=False)
def _splini(xa, ya, y2a, n, x):
    yi = 0.0
    klo = 0
    khi = 1
    while x > xa[klo] and khi < n:
        xx = x
        if khi < n - 1:
            xx = x if x < xa[khi] else xa[khi]
        h = xa[khi] - xa[klo]
        a = (xa[khi] - xx) / h
        b = (xx - xa[klo]) / h
        a2 = a * a
        b2 = b * b
        yi += ((1.0 - a2) * ya[klo] / 2.0 + b2 * ya[khi] / 2.0
               + ((-(1.0 + a2 * a2) / 4.0 + a2 / 2.0) * y2a[klo]
                  + (b2 * b2 / 4.0 - b2 / 2.0) * y2a[khi]) * h * h / 6.0) * h
        klo += 1
        khi += 1
    return yi


@njit(cache=False)
def _splint(xa, ya, y2a, n, x):
    klo = 0
    khi = n - 1
    while khi - klo > 1:
        k = (khi + klo) // 2
        if xa[k] > x:
            khi = k
        else:
            klo = k
    h = xa[khi] - xa[klo]
    a = (xa[khi] - x) / h
    b = (x - xa[klo]) / h
    return a * ya[klo] + b * ya[khi] + ((a * a * a - a) * y2a[klo] + (b * b * b - b) * y2a[khi]) * h * h / 6.0


@njit(cache=False)
def _spline(x, y, n, yp1, ypn, y2):
    u = np.empty(n)
    if yp1 > 0.99E30:
        y2[0] = 0.0
        u[0] = 0.0
    else:
        y2[0] = -0.5
        u[0] = (3.0 / (x[1] - x[0])) * ((y[1] - y[0]) / (x[1] - x[0]) - yp1)
    for i in range(1, n - 1):
        sig = (x[i] - x[i - 1]) / (x[i + 1] - x[i - 1])
        p = sig * y2[i - 1] + 2.0
        y2[i] = (sig - 1.0) / p
        u[i] = (6.0 * ((y[i + 1] - y[i]) / (x[i + 1] - x[i]) - (y[i] - y[i - 1]) / (x[i] - x[i - 1]))
                / (x[i + 1] - x[i - 1]) - sig * u[i - 1]) / p
    if ypn > 0.99E30:
        qn = 0.0
        un = 0.0
    else:
        qn = 0.5
        un = (3.0 / (x[n - 1] - x[n - 2])) * (ypn - (y[n - 1] - y[n - 2]) / (x[n - 1] - x[n - 2]))
    y2[n - 1] = (un - qn * u[n - 2]) / (qn * y2[n - 2] + 1.0)
    for k in range(n - 2, -1, -1):
        y2[k] = y2[k] * y2[k + 1] + u[k]


@njit(cache=False)
def _zeta(zz, zl, re):
    return (zz - zl) * (re + zl) / (re + zz)


@njit(cache=False)
def _densm(alt, d0, xm, mn3, zn3, tn3, tgn3, mn2, zn2, tn2, tgn2, st):
    """Lower-atmosphere temperature and density. Returns (density or temperature, tz)."""
    re = st[_RE]
    gsurf = st[_GSURF]
    rgas = 831.4
    xs = np.zeros(10)
    ys = np.zeros(10)
    y2out = np.zeros(10)
    densm_tmp = d0
    tz = 0.0
    if alt > zn2[0]:
        return (tz if xm == 0.0 else d0), tz

    # Stratosphere/mesosphere temperature
    z = alt if alt > zn2[mn2 - 1] else zn2[mn2 - 1]
    mn = mn2
    z1 = zn2[0]
    z2 = zn2[mn - 1]
    t1 = tn2[0]
    t2 = tn2[mn - 1]
    zg = _zeta(z, z1, re)
    zgdif = _zeta(z2, z1, re)
    for k in range(mn):
        xs[k] = _zeta(zn2[k], z1, re) / zgdif
        ys[k] = 1.0 / tn2[k]
    yd1 = -tgn2[0] / (t1 * t1) * zgdif
    yd2 = -tgn2[1] / (t2 * t2) * zgdif * ((re + z2) / (re + z1)) ** 2
    _spline(xs, ys, mn, yd1, yd2, y2out)
    x = zg / zgdif
    y = _splint(xs, ys, y2out, mn, x)
    tz = 1.0 / y
    if xm != 0.0:
        glb = gsurf / ((1.0 + z1 / re) ** 2)
        gamm = xm * glb * zgdif / rgas
        yi = _splini(xs, ys, y2out, mn, x)
        expl = gamm * yi
        if expl > 50.0:
            expl = 50.0
        densm_tmp = densm_tmp * (t1 / tz) * math.exp(-expl)

    if alt > zn3[0]:
        return (tz if xm == 0.0 else densm_tmp), tz

    # Troposphere/stratosphere temperature
    z = alt
    mn = mn3
    z1 = zn3[0]
    z2 = zn3[mn - 1]
    t1 = tn3[0]
    t2 = tn3[mn - 1]
    zg = _zeta(z, z1, re)
    zgdif = _zeta(z2, z1, re)
    for k in range(mn):
        xs[k] = _zeta(zn3[k], z1, re) / zgdif
        ys[k] = 1.0 / tn3[k]
    yd1 = -tgn3[0] / (t1 * t1) * zgdif
    yd2 = -tgn3[1] / (t2 * t2) * zgdif * ((re + z2) / (re + z1)) ** 2
    _spline(xs, ys, mn, yd1, yd2, y2out)
    x = zg / zgdif
    y = _splint(xs, ys, y2out, mn, x)
    tz = 1.0 / y
    if xm != 0.0:
        glb = gsurf / ((1.0 + z1 / re) ** 2)
        gamm = xm * glb * zgdif / rgas
        yi = _splini(xs, ys, y2out, mn, x)
        expl = gamm * yi
        if expl > 50.0:
            expl = 50.0
        densm_tmp = densm_tmp * (t1 / tz) * math.exp(-expl)
    return (tz if xm == 0.0 else densm_tmp), tz


@njit(cache=False)
def _densu(alt, dlb, tinf, tlb, xm, alpha, zlb, s2, mn1, zn1, tn1, tgn1, st):
    """Thermosphere temperature and density (Bates profile + spline). Returns (density or temperature, tz)."""
    re = st[_RE]
    gsurf = st[_GSURF]
    rgas = 831.4
    xs = np.zeros(5)
    ys = np.zeros(5)
    y2out = np.zeros(5)
    x = 0.0
    z1 = 0.0
    t1 = 0.0
    zgdif = 0.0
    mn = 0
    za = zn1[0]
    z = alt if alt > za else za
    zg2 = _zeta(z, zlb, re)

    # Bates temperature
    tt = tinf - (tinf - tlb) * math.exp(-s2 * zg2)
    ta = tt
    tz = tt
    densu_temp = tz

    if alt < za:
        dta = (tinf - ta) * s2 * ((re + zlb) / (re + za)) ** 2
        tgn1[0] = dta
        tn1[0] = ta
        z = alt if alt > zn1[mn1 - 1] else zn1[mn1 - 1]
        mn = mn1
        z1 = zn1[0]
        z2 = zn1[mn - 1]
        t1 = tn1[0]
        t2 = tn1[mn - 1]
        zg = _zeta(z, z1, re)
        zgdif = _zeta(z2, z1, re)
        for k in range(mn):
            xs[k] = _zeta(zn1[k], z1, re) / zgdif
            ys[k] = 1.0 / tn1[k]
        yd1 = -tgn1[0] / (t1 * t1) * zgdif
        yd2 = -tgn1[1] / (t2 * t2) * zgdif * ((re + z2) / (re + z1)) ** 2
        _spline(xs, ys, mn, yd1, yd2, y2out)
        x = zg / zgdif
        y = _splint(xs, ys, y2out, mn, x)
        tz = 1.0 / y
        densu_temp = tz
    if xm == 0:
        return densu_temp, tz

    # Density above za
    glb = gsurf / (1.0 + zlb / re) ** 2
    gamma = xm * glb / (s2 * rgas * tinf)
    expl = math.exp(-s2 * gamma * zg2)
    if expl > 50.0:
        expl = 50.0
    if tt <= 0:
        expl = 50.0
    densa = dlb * (tlb / tt) ** (1.0 + alpha + gamma) * expl
    densu_temp = densa
    if alt >= za:
        return densu_temp, tz

    # Density below za
    glb = gsurf / (1.0 + z1 / re) ** 2
    gamm = xm * glb * zgdif / rgas
    yi = _splini(xs, ys, y2out, mn, x)
    expl = gamm * yi
    if expl > 50.0:
        expl = 50.0
    if tz <= 0:
        expl = 50.0
    densu_temp = densu_temp * (t1 / tz) ** (1.0 + alpha) * math.exp(-expl)
    return densu_temp, tz


@njit(cache=False)
def _g0(a, p24, p25):
    return a - 4.0 + (p25 - 1.0) * (a - 4.0 + (math.exp(-math.sqrt(p24 * p24) * (a - 4.0)) - 1.0)
                                    / math.sqrt(p24 * p24))


@njit(cache=False)
def _sumex(ex):
    return 1.0 + (1.0 - ex ** 19.0) / (1.0 - ex) * ex ** 0.5


@njit(cache=False)
def _sg0(ex, p24, p25, ap):
    return (_g0(ap[1], p24, p25) + (_g0(ap[2], p24, p25) * ex + _g0(ap[3], p24, p25) * ex * ex
                                    + _g0(ap[4], p24, p25) * ex ** 3.0
                                    + (_g0(ap[5], p24, p25) * ex ** 4.0 + _g0(ap[6], p24, p25) * ex ** 12.0)
                                    * (1.0 - ex ** 8.0) / (1.0 - ex))) / _sumex(ex)


@njit(cache=False)
def _globe7(p, inp, ap_a, sw, swc, plg, st):
    """G(L) function, upper thermosphere parameters."""
    t = np.zeros(15)
    sr = 7.2722E-5
    dgtr = 1.74533E-2
    dr = 1.72142E-2
    hr = 0.2618
    tloc = inp[_LST]

    c = math.sin(inp[_LAT] * dgtr)
    s = math.cos(inp[_LAT] * dgtr)
    c2 = c * c
    c4 = c2 * c2
    s2 = s * s

    plg[0, 1] = c
    plg[0, 2] = 0.5 * (3.0 * c2 - 1.0)
    plg[0, 3] = 0.5 * (5.0 * c * c2 - 3.0 * c)
    plg[0, 4] = (35.0 * c4 - 30.0 * c2 + 3.0) / 8.0
    plg[0, 5] = (63.0 * c2 * c2 * c - 70.0 * c2 * c + 15.0 * c) / 8.0
    plg[0, 6] = (11.0 * c * plg[0, 5] - 5.0 * plg[0, 4]) / 6.0
    plg[1, 1] = s
    plg[1, 2] = 3.0 * c * s
    plg[1, 3] = 1.5 * (5.0 * c2 - 1.0) * s
    plg[1, 4] = 2.5 * (7.0 * c2 * c - 3.0 * c) * s
    plg[1, 5] = 1.875 * (21.0 * c4 - 14.0 * c2 + 1.0) * s
    plg[1, 6] = (11.0 * c * plg[1, 5] - 6.0 * plg[1, 4]) / 5.0
    plg[2, 2] = 3.0 * s2
    plg[2, 3] = 15.0 * s2 * c
    plg[2, 4] = 7.5 * (7.0 * c2 - 1.0) * s2
    plg[2, 5] = 3.0 * c * plg[2, 4] - 2.0 * plg[2, 3]
    plg[2, 6] = (11.0 * c * plg[2, 5] - 7.0 * plg[2, 4]) / 4.0
    plg[2, 7] = (13.0 * c * plg[2, 6] - 8.0 * plg[2, 5]) / 5.0
    plg[3, 3] = 15.0 * s2 * s
    plg[3, 4] = 105.0 * s2 * s * c
    plg[3, 5] = (9.0 * c * plg[3, 4] - 7. * plg[3, 3]) / 2.0
    plg[3, 6] = (11.0 * c * plg[3, 5] - 8. * plg[3, 4]) / 3.0

    if not ((sw[7] == 0 and sw[8] == 0) and sw[14] == 0):
        st[_STLOC] = math.sin(hr * tloc)
        st[_CTLOC] = math.cos(hr * tloc)
        st[_S2TLOC] = math.sin(2.0 * hr * tloc)
        st[_C2TLOC] = math.cos(2.0 * hr * tloc)
        st[_S3TLOC] = math.sin(3.0 * hr * tloc)
        st[_C3TLOC] = math.cos(3.0 * hr * tloc)
    stloc, ctloc = st[_STLOC], st[_CTLOC]
    s2tloc, c2tloc = st[_S2TLOC], st[_C2TLOC]
    s3tloc, c3tloc = st[_S3TLOC], st[_C3TLOC]

    doy = inp[_DOY]
    cd32 = math.cos(dr * (doy - p[31]))
    cd18 = math.cos(2.0 * dr * (doy - p[17]))
    cd14 = math.cos(dr * (doy - p[13]))
    cd39 = math.cos(2.0 * dr * (doy - p[38]))

    # F10.7 effect
    df = inp[_F107] - inp[_F107A]
    dfa = inp[_F107A] - 150.0
    st[_DFA] = dfa
    t[0] = p[19] * df * (1.0 + p[59] * dfa) + p[20] * df * df + p[21] * dfa + p[29] * dfa ** 2.0
    f1 = 1.0 + (p[47] * dfa + p[19] * df + p[20] * df * df) * swc[1]
    f2 = 1.0 + (p[49] * dfa + p[19] * df + p[20] * df * df) * swc[1]

    # Time independent
    t[1] = (p[1] * plg[0, 2] + p[2] * plg[0, 4] + p[22] * plg[0, 6]) \
        + (p[14] * plg[0, 2]) * dfa * swc[1] + p[26] * plg[0, 1]
    # Symmetrical annual
    t[2] = p[18] * cd32
    # Symmetrical semiannual
    t[3] = (p[15] + p[16] * plg[0, 2]) * cd18
    # Asymmetrical annual
    t[4] = f1 * (p[9] * plg[0, 1] + p[10] * plg[0, 3]) * cd14
    # Asymmetrical semiannual
    t[5] = p[37] * plg[0, 1] * cd39

    # Diurnal
    if sw[7]:
        t71 = (p[11] * plg[1, 2]) * cd14 * swc[5]
        t72 = (p[12] * plg[1, 2]) * cd14 * swc[5]
        t[6] = f2 * ((p[3] * plg[1, 1] + p[4] * plg[1, 3] + p[27] * plg[1, 5] + t71) * ctloc
                     + (p[6] * plg[1, 1] + p[7] * plg[1, 3] + p[28] * plg[1, 5] + t72) * stloc)
    # Semidiurnal
    if sw[8]:
        t81 = (p[23] * plg[2, 3] + p[35] * plg[2, 5]) * cd14 * swc[5]
        t82 = (p[33] * plg[2, 3] + p[36] * plg[2, 5]) * cd14 * swc[5]
        t[7] = f2 * ((p[5] * plg[2, 2] + p[41] * plg[2, 4] + t81) * c2tloc
                     + (p[8] * plg[2, 2] + p[42] * plg[2, 4] + t82) * s2tloc)
    # Terdiurnal
    if sw[14]:
        t[13] = f2 * ((p[39] * plg[3, 3] + (p[93] * plg[3, 4] + p[46] * plg[3, 6]) * cd14 * swc[5]) * s3tloc
                      + (p[40] * plg[3, 3] + (p[94] * plg[3, 4] + p[48] * plg[3, 6]) * cd14 * swc[5]) * c3tloc)

    # Magnetic activity
    if sw[9] == -1:
        if p[51] != 0:
            exp1 = math.exp(-10800.0 * math.sqrt(p[51] * p[51])
                            / (1.0 + p[138] * (45.0 - math.sqrt(inp[_LAT] * inp[_LAT]))))
            if exp1 > 0.99999:
                exp1 = 0.99999
            p24 = p[24] if p[24] >= 1.0E-4 else 1.0E-4
            st[_APT0] = _sg0(exp1, p24, p[25], ap_a)
            if sw[9]:
                t[8] = st[_APT0] * (p[50] + p[96] * plg[0, 2] + p[54] * plg[0, 4]
                                    + (p[125] * plg[0, 1] + p[126] * plg[0, 3] + p[127] * plg[0, 5]) * cd14 * swc[5]
                                    + (p[128] * plg[1, 1] + p[129] * plg[1, 3] + p[130] * plg[1, 5]) * swc[7]
                                    * math.cos(hr * (tloc - p[131])))
    else:
        apd = inp[_AP] - 4.0
        p44 = p[43]
        p45 = p[44]
        if p44 < 0:
            p44 = 1.0E-5
        st[_APDF] = apd + (p45 - 1.0) * (apd + (math.exp(-p44 * apd) - 1.0) / p44)
        if sw[9]:
            t[8] = st[_APDF] * (p[32] + p[45] * plg[0, 2] + p[34] * plg[0, 4]
                                + (p[100] * plg[0, 1] + p[101] * plg[0, 3] + p[102] * plg[0, 5]) * cd14 * swc[5]
                                + (p[121] * plg[1, 1] + p[122] * plg[1, 3] + p[123] * plg[1, 5]) * swc[7]
                                * math.cos(hr * (tloc - p[124])))

    apdf = st[_APDF]
    apt0 = st[_APT0]
    g_long = inp[_LON]
    sec = inp[_SEC]
    if sw[10] and g_long > -1000.0:
        # Longitudinal
        if sw[11]:
            t[10] = (1.0 + p[80] * dfa * swc[1]) * (
                (p[64] * plg[1, 2] + p[65] * plg[1, 4] + p[66] * plg[1, 6]
                 + p[103] * plg[1, 1] + p[104] * plg[1, 3] + p[105] * plg[1, 5]
                 + swc[5] * (p[109] * plg[1, 1] + p[110] * plg[1, 3] + p[111] * plg[1, 5]) * cd14)
                * math.cos(dgtr * g_long)
                + (p[90] * plg[1, 2] + p[91] * plg[1, 4] + p[92] * plg[1, 6]
                   + p[106] * plg[1, 1] + p[107] * plg[1, 3] + p[108] * plg[1, 5]
                   + swc[5] * (p[112] * plg[1, 1] + p[113] * plg[1, 3] + p[114] * plg[1, 5]) * cd14)
                * math.sin(dgtr * g_long))
        # UT and mixed UT, longitude
        if sw[12]:
            t[11] = (1.0 + p[95] * plg[0, 1]) * (1.0 + p[81] * dfa * swc[1]) \
                * (1.0 + p[119] * plg[0, 1] * swc[5] * cd14) \
                * ((p[68] * plg[0, 1] + p[69] * plg[0, 3] + p[70] * plg[0, 5])
                   * math.cos(sr * (sec - p[71])))
            t[11] += swc[11] * (p[76] * plg[2, 3] + p[77] * plg[2, 5] + p[78] * plg[2, 7]) \
                * math.cos(sr * (sec - p[79]) + 2.0 * dgtr * g_long) * (1.0 + p[137] * dfa * swc[1])
        # UT, longitude magnetic activity
        if sw[13]:
            if sw[9] == -1:
                if p[51]:
                    t[12] = apt0 * swc[11] * (1. + p[132] * plg[0, 1]) \
                        * ((p[52] * plg[1, 2] + p[98] * plg[1, 4] + p[67] * plg[1, 6])
                           * math.cos(dgtr * (g_long - p[97]))) \
                        + apt0 * swc[11] * swc[5] \
                        * (p[133] * plg[1, 1] + p[134] * plg[1, 3] + p[135] * plg[1, 5]) \
                        * cd14 * math.cos(dgtr * (g_long - p[136])) \
                        + apt0 * swc[12] \
                        * (p[55] * plg[0, 1] + p[56] * plg[0, 3] + p[57] * plg[0, 5]) \
                        * math.cos(sr * (sec - p[58]))
            else:
                t[12] = apdf * swc[11] * (1.0 + p[120] * plg[0, 1]) \
                    * ((p[60] * plg[1, 2] + p[61] * plg[1, 4] + p[62] * plg[1, 6])
                       * math.cos(dgtr * (g_long - p[63]))) \
                    + apdf * swc[11] * swc[5] \
                    * (p[115] * plg[1, 1] + p[116] * plg[1, 3] + p[117] * plg[1, 5]) \
                    * cd14 * math.cos(dgtr * (g_long - p[118])) \
                    + apdf * swc[12] \
                    * (p[83] * plg[0, 1] + p[84] * plg[0, 3] + p[85] * plg[0, 5]) \
                    * math.cos(sr * (sec - p[75]))

    tinf = p[30]
    for i in range(14):
        tinf = tinf + abs(sw[i + 1]) * t[i]
    return tinf


@njit(cache=False)
def _glob7s(p, inp, sw, swc, plg, st):
    """Version of globe for the lower atmosphere (10/26/99)."""
    if p[99] != 0 and p[99] != 2.0:
        return -1.0
    t = np.zeros(14)
    dr = 1.72142E-2
    dgtr = 1.74533E-2
    doy = inp[_DOY]
    cd32 = math.cos(dr * (doy - p[31]))
    cd18 = math.cos(2.0 * dr * (doy - p[17]))
    cd14 = math.cos(dr * (doy - p[13]))
    cd39 = math.cos(2.0 * dr * (doy - p[38]))

    t[0] = p[21] * st[_DFA]
    t[1] = p[1] * plg[0, 2] + p[2] * plg[0, 4] + p[22] * plg[0, 6] + p[26] * plg[0, 1] \
        + p[14] * plg[0, 3] + p[59] * plg[0, 5]
    t[2] = (p[18] + p[47] * plg[0, 2] + p[29] * plg[0, 4]) * cd32
    t[3] = (p[15] + p[16] * plg[0, 2] + p[30] * plg[0, 4]) * cd18
    t[4] = (p[9] * plg[0, 1] + p[10] * plg[0, 3] + p[20] * plg[0, 5]) * cd14
    t[5] = (p[37] * plg[0, 1]) * cd39

    if sw[7]:
        t71 = p[11] * plg[1, 2] * cd14 * swc[5]
        t72 = p[12] * plg[1, 2] * cd14 * swc[5]
        t[6] = ((p[3] * plg[1, 1] + p[4] * plg[1, 3] + t71) * st[_CTLOC]
                + (p[6] * plg[1, 1] + p[7] * plg[1, 3] + t72) * st[_STLOC])
    if sw[8]:
        t81 = (p[23] * plg[2, 3] + p[35] * plg[2, 5]) * cd14 * swc[5]
        t82 = (p[33] * plg[2, 3] + p[36] * plg[2, 5]) * cd14 * swc[5]
        t[7] = ((p[5] * plg[2, 2] + p[41] * plg[2, 4] + t81) * st[_C2TLOC]
                + (p[8] * plg[2, 2] + p[42] * plg[2, 4] + t82) * st[_S2TLOC])
    if sw[14]:
        t[13] = p[39] * plg[3, 3] * st[_S3TLOC] + p[40] * plg[3, 3] * st[_C3TLOC]
    if sw[9]:
        if sw[9] == 1:
            t[8] = st[_APDF] * (p[32] + p[45] * plg[0, 2] * swc[2])
        if sw[9] == -1:
            t[8] = p[50] * st[_APT0] + p[96] * plg[0, 2] * st[_APT0] * swc[2]
    g_long = inp[_LON]
    if not (sw[10] == 0 or sw[11] == 0 or g_long <= -1000.0):
        t[10] = (1.0 + plg[0, 1] * (p[80] * swc[5] * math.cos(dr * (doy - p[81]))
                                    + p[85] * swc[6] * math.cos(2.0 * dr * (doy - p[86])))
                 + p[83] * swc[3] * math.cos(dr * (doy - p[84]))
                 + p[87] * swc[4] * math.cos(2.0 * dr * (doy - p[88]))) \
            * ((p[64] * plg[1, 2] + p[65] * plg[1, 4] + p[66] * plg[1, 6]
                + p[74] * plg[1, 1] + p[75] * plg[1, 3] + p[76] * plg[1, 5]) * math.cos(dgtr * g_long)
               + (p[90] * plg[1, 2] + p[91] * plg[1, 4] + p[92] * plg[1, 6]
                  + p[77] * plg[1, 1] + p[78] * plg[1, 3] + p[79] * plg[1, 5]) * math.sin(dgtr * g_long))
    tt = 0.0
    for i in range(14):
        tt += abs(sw[i + 1]) * t[i]
    return tt


@njit(cache=False)
def _gts7(inp, ap_a, sw, swc, plg, st, tn1, tgn1, d, t):
    """Thermospheric portion of NRLMSISE-00 (alt > 72.5 km)."""
    zn1 = np.array([120.0, 110.0, 100.0, 90.0, 72.5])
    mn1 = 5
    dgtr = 1.74533E-2
    dr = 1.72142E-2
    alpha = np.array([-0.38, 0.0, 0.0, 0.0, 0.17, 0.0, -0.38, 0.0, 0.0])
    altl = np.array([200.0, 300.0, 160.0, 250.0, 240.0, 450.0, 320.0, 450.0])
    za = PDL[1, 15]
    zn1[0] = za
    for j in range(9):
        d[j] = 0.0
    alt = inp[_ALT]

    # Tinf variations not important below za or zn1(1)
    if alt > zn1[0]:
        tinf = PTM[0] * PT[0] * (1.0 + sw[16] * _globe7(PT, inp, ap_a, sw, swc, plg, st))
    else:
        tinf = PTM[0] * PT[0]
    t[0] = tinf

    # Gradient variations not important below zn1(5)
    if alt > zn1[4]:
        g0 = PTM[3] * PS[0] * (1.0 + sw[19] * _globe7(PS, inp, ap_a, sw, swc, plg, st))
    else:
        g0 = PTM[3] * PS[0]
    tlb = PTM[1] * (1.0 + sw[17] * _globe7(PD[3], inp, ap_a, sw, swc, plg, st)) * PD[3, 0]
    s = g0 / (tinf - tlb)

    # Lower thermosphere temperature variations not significant for density above 300 km
    if alt < 300.0:
        tn1[1] = PTM[6] * PTL[0, 0] / (1.0 - sw[18] * _glob7s(PTL[0], inp, sw, swc, plg, st))
        tn1[2] = PTM[2] * PTL[1, 0] / (1.0 - sw[18] * _glob7s(PTL[1], inp, sw, swc, plg, st))
        tn1[3] = PTM[7] * PTL[2, 0] / (1.0 - sw[18] * _glob7s(PTL[2], inp, sw, swc, plg, st))
        tn1[4] = PTM[4] * PTL[3, 0] / (1.0 - sw[18] * sw[20] * _glob7s(PTL[3], inp, sw, swc, plg, st))
        tgn1[1] = PTM[8] * PMA[8, 0] * (1.0 + sw[18] * sw[20] * _glob7s(PMA[8], inp, sw, swc, plg, st)) \
            * tn1[4] * tn1[4] / ((PTM[4] * PTL[3, 0]) ** 2)
    else:
        tn1[1] = PTM[6] * PTL[0, 0]
        tn1[2] = PTM[2] * PTL[1, 0]
        tn1[3] = PTM[7] * PTL[2, 0]
        tn1[4] = PTM[4] * PTL[3, 0]
        tgn1[1] = PTM[8] * PMA[8, 0] * tn1[4] * tn1[4] / ((PTM[4] * PTL[3, 0]) ** 2)

    # N2 variation factor at Zlb
    g28 = sw[21] * _globe7(PD[2], inp, ap_a, sw, swc, plg, st)

    # Variation of turbopause height
    zhf = PDL[1, 24] * (1.0 + sw[5] * PDL[0, 24] * math.sin(dgtr * inp[_LAT]) * math.cos(dr * (inp[_DOY] - PT[13])))
    t[0] = tinf
    xmm = PDM[2, 4]
    z = alt
    zlb = PTM[5]

    # N2 density
    db28 = PDM[2, 0] * math.exp(g28) * PD[2, 0]
    d[2], t[1] = _densu(z, db28, tinf, tlb, 28.0, alpha[2], zlb, s, mn1, zn1, tn1, tgn1, st)
    zh28 = PDM[2, 2] * zhf
    zhm28 = PDM[2, 3] * PDL[1, 5]
    xmd = 28.0 - xmm
    b28, tz = _densu(zh28, db28, tinf, tlb, xmd, alpha[2] - 1.0, zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z <= altl[2]:
        dm28, tz = _densu(z, b28, tinf, tlb, xmm, alpha[2], zlb, s, mn1, zn1, tn1, tgn1, st)
        st[_DM28] = dm28
        d[2] = _dnet(d[2], dm28, zhm28, xmm, 28.0)

    # He density
    g4 = sw[21] * _globe7(PD[0], inp, ap_a, sw, swc, plg, st)
    db04 = PDM[0, 0] * math.exp(g4) * PD[0, 0]
    d[0], t[1] = _densu(z, db04, tinf, tlb, 4., alpha[0], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z < altl[0]:
        zh04 = PDM[0, 2]
        b04, t[1] = _densu(zh04, db04, tinf, tlb, 4. - xmm, alpha[0] - 1., zlb, s, mn1, zn1, tn1, tgn1, st)
        dm04, t[1] = _densu(z, b04, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
        zhm04 = zhm28
        d[0] = _dnet(d[0], dm04, zhm04, xmm, 4.)
        rl = math.log(b28 * PDM[0, 1] / b04)
        zc04 = PDM[0, 4] * PDL[1, 0]
        hc04 = PDM[0, 5] * PDL[1, 1]
        d[0] = d[0] * _ccor(z, rl, hc04, zc04)

    # O density
    g16 = sw[21] * _globe7(PD[1], inp, ap_a, sw, swc, plg, st)
    db16 = PDM[1, 0] * math.exp(g16) * PD[1, 0]
    d[1], t[1] = _densu(z, db16, tinf, tlb, 16., alpha[1], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z <= altl[1]:
        zh16 = PDM[1, 2]
        b16, t[1] = _densu(zh16, db16, tinf, tlb, 16.0 - xmm, alpha[1] - 1.0, zlb, s, mn1, zn1, tn1, tgn1, st)
        dm16, t[1] = _densu(z, b16, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
        zhm16 = zhm28
        d[1] = _dnet(d[1], dm16, zhm16, xmm, 16.)
        rl = PDM[1, 1] * PDL[1, 16] * (1.0 + sw[1] * PDL[0, 23] * (inp[_F107A] - 150.0))
        hc16 = PDM[1, 5] * PDL[1, 3]
        zc16 = PDM[1, 4] * PDL[1, 2]
        hc216 = PDM[1, 5] * PDL[1, 4]
        d[1] = d[1] * _ccor2(z, rl, hc16, zc16, hc216)
        hcc16 = PDM[1, 7] * PDL[1, 13]
        zcc16 = PDM[1, 6] * PDL[1, 12]
        rc16 = PDM[1, 3] * PDL[1, 14]
        d[1] = d[1] * _ccor(z, rc16, hcc16, zcc16)

    # O2 density
    g32 = sw[21] * _globe7(PD[4], inp, ap_a, sw, swc, plg, st)
    db32 = PDM[3, 0] * math.exp(g32) * PD[4, 0]
    d[3], t[1] = _densu(z, db32, tinf, tlb, 32., alpha[3], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15]:
        if z <= altl[3]:
            zh32 = PDM[3, 2]
            b32, t[1] = _densu(zh32, db32, tinf, tlb, 32. - xmm, alpha[3] - 1., zlb, s, mn1, zn1, tn1, tgn1, st)
            dm32, t[1] = _densu(z, b32, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
            zhm32 = zhm28
            d[3] = _dnet(d[3], dm32, zhm32, xmm, 32.)
            rl = math.log(b28 * PDM[3, 1] / b32)
            hc32 = PDM[3, 5] * PDL[1, 7]
            zc32 = PDM[3, 4] * PDL[1, 6]
            d[3] = d[3] * _ccor(z, rl, hc32, zc32)
        hcc32 = PDM[3, 7] * PDL[1, 22]
        hcc232 = PDM[3, 7] * PDL[0, 22]
        zcc32 = PDM[3, 6] * PDL[1, 21]
        rc32 = PDM[3, 3] * PDL[1, 23] * (1. + sw[1] * PDL[0, 23] * (inp[_F107A] - 150.))
        d[3] = d[3] * _ccor2(z, rc32, hcc32, zcc32, hcc232)

    # Ar density
    g40 = sw[21] * _globe7(PD[5], inp, ap_a, sw, swc, plg, st)
    db40 = PDM[4, 0] * math.exp(g40) * PD[5, 0]
    d[4], t[1] = _densu(z, db40, tinf, tlb, 40., alpha[4], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z <= altl[4]:
        zh40 = PDM[4, 2]
        b40, t[1] = _densu(zh40, db40, tinf, tlb, 40. - xmm, alpha[4] - 1., zlb, s, mn1, zn1, tn1, tgn1, st)
        dm40, t[1] = _densu(z, b40, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
        zhm40 = zhm28
        d[4] = _dnet(d[4], dm40, zhm40, xmm, 40.)
        rl = math.log(b28 * PDM[4, 1] / b40)
        hc40 = PDM[4, 5] * PDL[1, 9]
        zc40 = PDM[4, 4] * PDL[1, 8]
        d[4] = d[4] * _ccor(z, rl, hc40, zc40)

    # Hydrogen density
    g1 = sw[21] * _globe7(PD[6], inp, ap_a, sw, swc, plg, st)
    db01 = PDM[5, 0] * math.exp(g1) * PD[6, 0]
    d[6], t[1] = _densu(z, db01, tinf, tlb, 1., alpha[6], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z <= altl[6]:
        zh01 = PDM[5, 2]
        b01, t[1] = _densu(zh01, db01, tinf, tlb, 1. - xmm, alpha[6] - 1., zlb, s, mn1, zn1, tn1, tgn1, st)
        dm01, t[1] = _densu(z, b01, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
        zhm01 = zhm28
        d[6] = _dnet(d[6], dm01, zhm01, xmm, 1.)
        rl = math.log(b28 * PDM[5, 1] * math.sqrt(PDL[1, 17] * PDL[1, 17]) / b01)
        hc01 = PDM[5, 5] * PDL[1, 11]
        zc01 = PDM[5, 4] * PDL[1, 10]
        d[6] = d[6] * _ccor(z, rl, hc01, zc01)
        hcc01 = PDM[5, 7] * PDL[1, 19]
        zcc01 = PDM[5, 6] * PDL[1, 18]
        rc01 = PDM[5, 3] * PDL[1, 20]
        d[6] = d[6] * _ccor(z, rc01, hcc01, zcc01)

    # Atomic nitrogen density
    g14 = sw[21] * _globe7(PD[7], inp, ap_a, sw, swc, plg, st)
    db14 = PDM[6, 0] * math.exp(g14) * PD[7, 0]
    d[7], t[1] = _densu(z, db14, tinf, tlb, 14., alpha[7], zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[15] and z <= altl[7]:
        zh14 = PDM[6, 2]
        b14, t[1] = _densu(zh14, db14, tinf, tlb, 14. - xmm, alpha[7] - 1., zlb, s, mn1, zn1, tn1, tgn1, st)
        dm14, t[1] = _densu(z, b14, tinf, tlb, xmm, 0., zlb, s, mn1, zn1, tn1, tgn1, st)
        zhm14 = zhm28
        d[7] = _dnet(d[7], dm14, zhm14, xmm, 14.)
        rl = math.log(b28 * PDM[6, 1] * math.sqrt(PDL[0, 2] * PDL[0, 2]) / b14)
        hc14 = PDM[6, 5] * PDL[0, 1]
        zc14 = PDM[6, 4] * PDL[0, 0]
        d[7] = d[7] * _ccor(z, rl, hc14, zc14)
        hcc14 = PDM[6, 7] * PDL[0, 4]
        zcc14 = PDM[6, 6] * PDL[0, 3]
        rc14 = PDM[6, 3] * PDL[0, 5]
        d[7] = d[7] * _ccor(z, rc14, hcc14, zcc14)

    # Anomalous oxygen density
    g16h = sw[21] * _globe7(PD[8], inp, ap_a, sw, swc, plg, st)
    db16h = PDM[7, 0] * math.exp(g16h) * PD[8, 0]
    tho = PDM[7, 9] * PDL[0, 6]
    dd, t[1] = _densu(z, db16h, tho, tho, 16., alpha[8], zlb, s, mn1, zn1, tn1, tgn1, st)
    zsht = PDM[7, 5]
    zmho = PDM[7, 4]
    zsho = _scalh(zmho, 16.0, tho, st)
    d[8] = dd * math.exp(-zsht / zsho * (math.exp(-(z - zmho) / zsht) - 1.))

    # Total mass density
    d[5] = 1.66E-24 * (4.0 * d[0] + 16.0 * d[1] + 28.0 * d[2] + 32.0 * d[3] + 40.0 * d[4] + d[6] + 14.0 * d[7])

    # Temperature
    z = math.sqrt(alt * alt)
    _, t[1] = _densu(z, 1.0, tinf, tlb, 0.0, 0.0, zlb, s, mn1, zn1, tn1, tgn1, st)
    if sw[0]:
        for i in range(9):
            d[i] = d[i] * 1.0E6
        d[5] = d[5] / 1000


@njit(cache=False)
def _gtd7(inp, ap_a, switches, d, t):
    sw = np.zeros(24)
    swc = np.zeros(24)
    _tselec(switches, sw, swc)
    st = np.zeros(12)
    plg = np.zeros((4, 9))
    tn1 = np.zeros(5)
    tn2 = np.zeros(4)
    tn3 = np.zeros(5)
    tgn1 = np.zeros(2)
    tgn2 = np.zeros(2)
    tgn3 = np.zeros(2)
    mn3 = 5
    zn3 = np.array([32.5, 20.0, 15.0, 10.0, 0.0])
    mn2 = 4
    zn2 = np.array([72.5, 55.0, 45.0, 32.5])
    zmix = 62.5

    # Latitude variation of gravity (none for sw[2] = 0)
    xlat = inp[_LAT]
    if sw[2] == 0:
        xlat = 45.0
    _glatf(xlat, st)
    xmm = PDM[2, 4]

    # Thermosphere/mesosphere (above zn2[0])
    alt = inp[_ALT]
    altt = alt if alt > zn2[0] else zn2[0]
    sinp = inp.copy()
    sinp[_ALT] = altt
    sd = np.zeros(9)
    stt = np.zeros(2)
    _gts7(sinp, ap_a, sw, swc, plg, st, tn1, tgn1, sd, stt)
    dm28m = st[_DM28] * 1.0E6 if sw[0] else st[_DM28]
    t[0] = stt[0]
    t[1] = stt[1]
    if alt >= zn2[0]:
        for i in range(9):
            d[i] = sd[i]
        return

    # Lower mesosphere/upper stratosphere (between zn3[0] and zn2[0])
    tgn2[0] = tgn1[1]
    tn2[0] = tn1[4]
    tn2[1] = PMA[0, 0] * PAVGM[0] / (1.0 - sw[20] * _glob7s(PMA[0], inp, sw, swc, plg, st))
    tn2[2] = PMA[1, 0] * PAVGM[1] / (1.0 - sw[20] * _glob7s(PMA[1], inp, sw, swc, plg, st))
    tn2[3] = PMA[2, 0] * PAVGM[2] / (1.0 - sw[20] * sw[22] * _glob7s(PMA[2], inp, sw, swc, plg, st))
    tgn2[1] = PAVGM[8] * PMA[9, 0] * (1.0 + sw[20] * sw[22] * _glob7s(PMA[9], inp, sw, swc, plg, st)) \
        * tn2[3] * tn2[3] / ((PMA[2, 0] * PAVGM[2]) ** 2)
    tn3[0] = tn2[3]

    if alt <= zn3[0]:
        # Lower stratosphere and troposphere (below zn3[0])
        tgn3[0] = tgn2[1]
        tn3[1] = PMA[3, 0] * PAVGM[3] / (1.0 - sw[22] * _glob7s(PMA[3], inp, sw, swc, plg, st))
        tn3[2] = PMA[4, 0] * PAVGM[4] / (1.0 - sw[22] * _glob7s(PMA[4], inp, sw, swc, plg, st))
        tn3[3] = PMA[5, 0] * PAVGM[5] / (1.0 - sw[22] * _glob7s(PMA[5], inp, sw, swc, plg, st))
        tn3[4] = PMA[6, 0] * PAVGM[6] / (1.0 - sw[22] * _glob7s(PMA[6], inp, sw, swc, plg, st))
        tgn3[1] = PMA[7, 0] * PAVGM[7] * (1.0 + sw[22] * _glob7s(PMA[7], inp, sw, swc, plg, st)) \
            * tn3[4] * tn3[4] / ((PMA[6, 0] * PAVGM[6]) ** 2)

    # Linear transition to full mixing below zn2[0]
    dmc = 0.0
    if alt > zmix:
        dmc = 1.0 - (zn2[0] - alt) / (zn2[0] - zmix)
    dz28 = sd[2]

    # N2 density
    dmr = sd[2] / dm28m - 1.0
    d[2], tz = _densm(alt, dm28m, xmm, mn3, zn3, tn3, tgn3, mn2, zn2, tn2, tgn2, st)
    d[2] = d[2] * (1.0 + dmr * dmc)
    # He density
    dmr = sd[0] / (dz28 * PDM[0, 1]) - 1.0
    d[0] = d[2] * PDM[0, 1] * (1.0 + dmr * dmc)
    # O density
    d[1] = 0.0
    d[8] = 0.0
    # O2 density
    dmr = sd[3] / (dz28 * PDM[3, 1]) - 1.0
    d[3] = d[2] * PDM[3, 1] * (1.0 + dmr * dmc)
    # Ar density
    dmr = sd[4] / (dz28 * PDM[4, 1]) - 1.0
    d[4] = d[2] * PDM[4, 1] * (1.0 + dmr * dmc)
    # Hydrogen and atomic nitrogen
    d[6] = 0.0
    d[7] = 0.0
    # Total mass density
    d[5] = 1.66E-24 * (4.0 * d[0] + 16.0 * d[1] + 28.0 * d[2] + 32.0 * d[3] + 40.0 * d[4] + d[6] + 14.0 * d[7])
    if sw[0]:
        d[5] = d[5] / 1000
    # Temperature at altitude
    _, tz = _densm(alt, 1.0, 0.0, mn3, zn3, tn3, tgn3, mn2, zn2, tn2, tgn2, st)
    t[1] = tz


@njit(cache=False)
def _gtd7d(inp, ap_a, switches, d, t):
    """gtd7 with anomalous oxygen in the total mass density (the 'effective' density for drag)."""
    _gtd7(inp, ap_a, switches, d, t)
    d[5] = 1.66E-24 * (4.0 * d[0] + 16.0 * d[1] + 28.0 * d[2] + 32.0 * d[3] + 40.0 * d[4] + d[6]
                       + 14.0 * d[7] + 16.0 * d[8])
    if switches[0] == 1:
        d[5] = d[5] / 1000


def _run(fn, doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap, ap_array=None, switches=None):
    inp = np.array([doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap], dtype=np.float64)
    ap_a = np.zeros(7) if ap_array is None else np.asarray(ap_array, dtype=np.float64)
    sws = np.ones(24) if switches is None else np.asarray(switches, dtype=np.float64)
    d = np.zeros(9)
    t = np.zeros(2)
    fn(inp, ap_a, sws, d, t)
    return d, t


def gtd7(doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap, ap_array=None, switches=None):
    """
    NRLMSISE-00 neutral atmosphere (C-release interface). Returns (d[9], t[2]):
    d = He, O, N2, O2, Ar, total mass, H, N, anomalous O; t = exospheric, local temperature (K).
    switches[0] = 1 gives SI units (m^-3, kg/m^3); all switches default to 1.
    """
    return _run(_gtd7, doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap, ap_array, switches)


def gtd7d(doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap, ap_array=None, switches=None):
    """As gtd7, but d[5] includes anomalous oxygen (use this for drag)."""
    return _run(_gtd7d, doy, sec, alt, g_lat, g_long, lst, f107a, f107, ap, ap_array, switches)


@njit(cache=False)
def mass_density(doy, sec, alt_km, lat_deg, lon_deg, f107a, f107, ap):
    """
    Total mass density for drag (kg/m^3): gtd7d, SI units, all switches on,
    daily Ap, and the MSIS-recommended local solar time sec/3600 + lon/15.
    """
    lst = sec / 3600.0 + lon_deg / 15.0
    inp = np.array([doy, sec, alt_km, lat_deg, lon_deg, lst, f107a, f107, ap])
    d = np.zeros(9)
    t = np.zeros(2)
    _gtd7d(inp, np.zeros(7), np.ones(24), d, t)
    return d[5]
