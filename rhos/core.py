from mpmath import mp, mpf
from progressbar import ProgressBar
import sys
import numpy as np
sys.path.append("../utils")
import math

def Smatrix_sigma_mp(tmax_, sigma_):    # for gaussian processes once implemented
    exit(0)
    S_ = mp.matrix(tmax_, tmax_)
    for i in range(tmax_):
        for j in range(tmax_):
            entry = mp.quad(
                lambda x: b_times_exp_mp(x, i + 1, j + 1, sigma_),
                [0, mp.inf],
                error=True,
            )
            S_[i, j] = entry[0]
    return S_


def Smatrix_mp(tmax_: int, alpha_=mpf(0), e0_=mpf(0), type='EXP', T=0):    #   TODO: rename emin into e0
    S_ = mp.matrix(tmax_, tmax_)
    for i in range(tmax_):
        for j in range(tmax_):
            entry = mp.fadd(mpf(i), mpf(j))
            arg = mp.fadd(entry, mpf(2))  # i+j+2
            entry = mp.fsub(arg, alpha_)    # i+j+2-a
            arg = mp.fneg(arg)
            arg = mp.fmul(arg, e0_)
            arg = mp.exp(arg)
            entry = mp.fdiv(arg, entry)
            S_[i, j] = entry
            if type == 'COSH':
                assert (T > 0)
                entry2 = mp.fsub(mpf(i), mpf(j))
                entry3 = mp.fsub(mpf(j), mpf(i))
                entry4 = mp.fneg(mpf(i))
                entry4 = mp.fsub(entry4, mpf(j))
                arg2 = mp.fadd(entry2, mpf(T))  # T+i-j
                arg3 = mp.fadd(entry3, mpf(T))  # T+j-i
                arg4 = mp.fadd(entry4, mpf(2 * T))  # 2T-j-i
                arg4 = mp.fsub(arg4, mpf(2))  # 2T-j-i-2
                entry2 = mp.fsub(arg2, alpha_)  # T+i-j-a
                entry3 = mp.fsub(arg3, alpha_)  # T+j-i-a
                entry4 = mp.fsub(arg4, alpha_)  # 2T-j-i-2-a
                arg2 = mp.fneg(arg2)
                arg3 = mp.fneg(arg3)
                arg4 = mp.fneg(arg4)
                arg2 = mp.fmul(arg2, e0_)
                arg3 = mp.fmul(arg3, e0_)
                arg4 = mp.fmul(arg4, e0_)
                arg2 = mp.exp(arg2)
                arg3 = mp.exp(arg3)
                arg4 = mp.exp(arg4)
                entry2 = mp.fdiv(arg2, entry2)
                entry3 = mp.fdiv(arg3, entry3)
                entry4 = mp.fdiv(arg4, entry4)
                S_[i, j] += entry2 + entry3 + entry4
    return S_

def Smatrix_float64(tmax_: int, alpha_=0, e0=0, S_in=None, type='EXP', T=0):
    if S_in is None:
        S_ = np.ndarray((tmax_, tmax_), dtype=np.float64)
    else:
        S_ = S_in
    for i in range(tmax_):
        for j in range(tmax_):
            S_[i, j] = np.exp(-(i+j+2)*e0) / (i+j+2-alpha_)
            if type == 'COSH':
                assert (T > 0)
                aux = np.exp(-(T+i-j)*e0) / (T+i-j-alpha_)
                aux2 = np.exp(-(T+j-i)*e0) / (T+j-i-alpha_)
                aux3 = np.exp(-(2*T-j-i-2)*e0) / (2*T-j-i-2-alpha_)
                S_[i, j] += aux + aux2 + aux3
    return S_

def Zfact_mp(estar_, sigma_):  # int_0^inf dE exp{(-e-estar)^2/2s^2}
    fact_ = mp.sqrt(2)
    res_ = mp.fdiv(estar_, fact_)
    res_ = mp.fdiv(res_, sigma_)  #   e/(sqrt2 sigma)
    res_ = mp.erf(res_)  #   erf [e/(sqrt2 sigma)]
    res_ = mp.fadd(res_, 1)  #   1 + erf [e/(sqrt2 sigma)]
    res_ = mp.fmul(res_, sigma_)  #   sigma (1 + erf [e/(sqrt2 sigma)])
    fact_ = mp.fdiv(mp.pi, 2)
    fact_ = mp.sqrt(fact_)  # sqrt(pi/2)
    res_ = mp.fmul(res_, fact_)  # sqrt(pi/2) sigma (1 + erf [e/(sqrt2 sigma)])
    return res_


def ft_mp(e, t, sigma_, alpha=mpf("0"), e0=mpf("0"), type='EXP', T=0):
    newt = mp.fsub(t, alpha)  #
    aux = mp.fmul(sigma_, sigma_)  #   s^2
    arg = mp.fmul(aux, newt)  #   s^2 (t-alpha)
    aux = mp.fmul(arg, newt)  #   s^2 (alpha-t)^2
    aux = mp.fmul(aux, mpf("0.5"))  #   s^2 (alpha-t)^2 /2
    res = mp.exp(aux)  #   exp{s^2 (alpha-t)^2 /2}
    aux = mp.fneg(newt)  #   alpha-t
    aux = mp.fmul(e, aux)  #   e(alpha-t)
    aux = mp.exp(aux)
    res = mp.fmul(res, aux)  #   exp{s^2 (alpha-t)^2 /2} exp{estar (alpha-t) }
    arg = mp.fadd(arg, e0)
    arg = mp.fsub(arg, e)
    arg = mp.fdiv(arg, sigma_)
    aux = mp.sqrt(2)
    arg = mp.fdiv(arg, aux)
    arg = mp.erfc(arg)  #   this is the COMPLEMENTARY erf
    res = mp.fmul(res, arg)
    aux = mp.fdiv(e, aux)
    aux = mp.fdiv(aux, sigma_)
    aux = mp.erf(aux)
    aux = mp.fadd(mpf(1), aux)
    res = mp.fdiv(res, aux)
    if type=='COSH':
        assert(T>0)
        newt2 = mp.fadd(t, alpha)  # alpha+t
        newt2 = mp.fsub(newt2, mpf(T))  # alpha+t-T
        aux2 = mp.fmul(sigma_, sigma_)  # s^2
        arg2 = mp.fmul(aux2, newt2)  # s^2 (t+alpha-T)
        aux2 = mp.fmul(arg2, newt2)  # s^2 (alpha+t-T)^2
        aux2 = mp.fmul(aux2, mpf("0.5"))  # s^2 (alpha+t-T)^2 /2
        res2 = mp.exp(aux2)  # exp{s^2 (alpha+t-T)^2 /2}
        aux2 = newt2  # alpha+t-T
        aux2 = mp.fmul(e, aux2)  # e(alpha+t-T)
        aux2 = mp.exp(aux2)
        res2 = mp.fmul(res2, aux2)  # exp{s^2 (alpha-t)^2 /2} exp{estar (alpha+t-T) }
        arg2 = mp.fsub(e0, arg2)
        arg2 = mp.fsub(arg2, e)
        arg2 = mp.fdiv(arg2, sigma_)
        aux2 = mp.sqrt(2)
        arg2 = mp.fdiv(arg2, aux2)
        arg2 = mp.erfc(arg2)  # this is the COMPLEMENTARY erf
        res2 = mp.fmul(res2, arg2)
        aux2 = mp.fdiv(e, aux2)
        aux2 = mp.fdiv(aux2, sigma_)
        aux2 = mp.erf(aux2)
        aux2 = mp.fadd(mpf(1), aux2)
        res2 = mp.fdiv(res2, aux2)
        res += res2
    return res

def A0_mp(e_, sigma_, alpha=mpf(0), e0=mpf(0)):
    aux = mp.fmul(sigma_, sigma_)
    aux = mp.fdiv(aux, mpf(2))
    aux = mp.fmul(aux, alpha)
    aux = mp.fadd(e_, aux)
    aux = mp.fsub(aux, e0)
    res = mp.fdiv(aux, sigma_)
    res = mp.erf(res)  #   Erf
    res = mp.fadd(1, res)  # 1+erf, the numerator
    aux_ = mp.sqrt(mp.pi)
    res = mp.fdiv(res, aux_)  # 1+erf /pi
    res = mp.fdiv(res, sigma_)  # 1+erf / (sqrt{pi} s)
    aux_ = mp.sqrt(2)
    aux_ = mp.fdiv(e_, aux_)
    aux_ = mp.fdiv(aux_, sigma_)
    aux_ = mp.erf(aux_)
    aux_ = mp.fadd(aux_, 1)
    aux_ = mp.fmul(aux_, aux_)
    res = mp.fdiv(res, aux_)
    return res

def A0E_mp(espacemp_, par):   #   vector of A0s for each energy
    a0_e = mp.matrix(par.Ne, 1)
    for ei in range(par.Ne):
        a0_e[ei] = A0_mp(e_=espacemp_[ei], sigma_=par.mpsigma, alpha=par.mpalpha, e0=par.e0)
    return a0_e

import scipy.special

def A0_float64(e_, sigma_, alpha=0, e0=0):
    aux = sigma_**2 / 2
    aux = aux * alpha
    aux = e_ + aux - e0
    res = aux / sigma_
    res = scipy.special.erf(res)
    res = 1 + res
    aux_ = math.sqrt(np.pi)
    res = res / aux_
    res = res / sigma_
    aux_ = math.sqrt(2)
    aux_ = e_ / aux_
    aux_ = aux_ / sigma_
    aux_ = scipy.special.erf(aux_)
    aux_ = aux_ + 1
    aux_ = aux_ * aux_
    res = res / aux_
    return res

def A0E_float64(espace_, par):   #   vector of A0s for each energy
    a0_e = np.ndarray(par.Ne, dtype = np.float64)
    for ei in range(par.Ne):
        a0_e[ei] = A0_float64(e_=espace_[ei], sigma_=par.sigma, alpha=par.alpha, e0=par.e0)
    return a0_e

def ft_float64(e, t, sigma_, alpha=0, e0=0, type='EXP', T=0):
    newt = t - alpha
    aux = sigma_**2
    arg = aux * newt
    aux = arg * newt
    aux = aux * 0.5
    res = np.exp(aux)
    aux = -newt
    aux = e * aux
    aux = np.exp(aux)
    res = res * aux
    arg = arg + e0
    arg = arg - e
    arg = arg / sigma_
    aux = math.sqrt(2)
    arg = arg / aux
    arg = scipy.special.erfc(arg)
    res = res * arg
    aux = e / aux
    aux = aux / sigma_
    aux = scipy.special.erf(aux)
    aux = 1 + aux
    res = res / aux
    if type=='COSH':
        assert(T>0)
        newt2 = t + alpha  # alpha+t
        newt2 = newt2 - T  # alpha+t-T
        aux2 = sigma_**2   # s^2
        arg2 = aux2*newt2  # s^2 (t+alpha-T)
        aux2 = arg2*newt2  # s^2 (alpha+t-T)^2
        aux2 = aux2*0.5  # s^2 (alpha+t-T)^2 /2
        res2 = np.exp(aux2)  # exp{s^2 (alpha+t-T)^2 /2}
        aux2 = newt2  # alpha+t-T
        aux2 = e*aux2  # e(alpha+t-T)
        aux2 = np.exp(aux2)
        res2 = res2*aux2  # exp{s^2 (alpha-t)^2 /2} exp{estar (alpha+t-T) }
        arg2 = e0-arg2
        arg2 = arg2-e
        arg2 = arg2/sigma_
        aux2 = math.sqrt(2)
        arg2 = arg2/aux2
        arg2 = scipy.special.erfc(arg2)  # this is the COMPLEMENTARY erf
        res2 = res2*arg2
        aux2 = e / aux2
        aux2 = aux2 / sigma_
        aux2 = scipy.special.erf(aux2)
        aux2 = 1 + aux2
        res2 = res2 / aux2
        res += res2
    return res
