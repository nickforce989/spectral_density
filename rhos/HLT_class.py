from mpmath import mp, mpf
import sys
import numpy as np
import os
sys.path.append("../utils")
from rhoMath import *
from rhoUtils import LogMessage, Inputs, MatrixBundle
from rhoUtils import *
from transform import *
from abw import *
from core import *
from core import A0E_mp
from abw import gAg, gBg
import matplotlib.pyplot as plt

_big = 100

class AlgorithmParameters:
    def __init__(
        self,
        alphaA=0,
        alphaB=-1,
        alphaC=-1.99,
        lambdaMax=50,
        lambdaStep=0.5,
        lambdaScanPrec=0.1,
        lambdaScanCap=6,
        kfactor=0.1,
        lambdaMin=0.
    ):
        assert alphaA != alphaB
        assert alphaA != alphaC
        self.alphaA = float(alphaA)
        self.alphaB = float(alphaB)
        self.alphaC = float(alphaC)
        self.lambdaMax = lambdaMax
        self.lambdaStep = lambdaStep
        self.lambdaScanPrec = lambdaScanPrec
        self.lambdaScanCap = lambdaScanCap
        self.kfactor = kfactor
        self.alphaAmp = mpf(str(alphaA))
        self.alphaBmp = mpf(str(alphaB))
        self.alphaCmp = mpf(str(alphaC))
        self.lambdaMin = lambdaMin


class A0_t:
    def __init__(self, par_: Inputs, alphaMP_=0, eminMP_=0):
        self.valute_at_E = mp.matrix(par_.Ne, 1)
        self.valute_at_E_dictionary = (
            {}
        )  # Auxiliary dictionary: A0espace[n] = A0espace_dictionary[espace[n]] # espace must be float
        self.is_filled = False
        self.alphaMP = alphaMP_
        self.eminMP = eminMP_
        self.par = par_

    def evaluate(self, espaceMP_):
        print(
            LogMessage(),
            "Computing A0 at all energies with Alpha = {:2.2e}".format(
                float(self.alphaMP)
            ),
        )
        self.valute_at_E = A0E_mp(
            espaceMP_, self.par, alpha_=self.alphaMP, e0_=self.par.mpe0
        )
        print(self.valute_at_E)

        for e_id in range(self.par.Ne):
            self.valute_at_E_dictionary[float(espaceMP_[e_id])] = self.valute_at_E[e_id]
        self.is_filled = True


class HLTWrapper:
    def __init__(
        self,
        par: Inputs,
        algorithmPar: AlgorithmParameters,
        matrix_bundle: MatrixBundle,
        correlator: Obs,
    ):
        self.par = par
        self.correlator = correlator
        self.algorithmPar = algorithmPar
        self.matrix_bundle = matrix_bundle
        #
        self.espace = np.linspace(par.emin, par.emax, par.Ne)
        self.e0MP = mpf(str(par.e0))
        self.espaceMP = mp.matrix(par.Ne, 1)
        self.sigmaMP = mpf(str(par.sigma))
        self.emaxMP = mpf(str(par.emax))
        self.eminMP = mpf(str(par.emin))
        self.espace_dictionary = (
            {}
        )  #   Auxiliary dictionary: espace_dictionary[espace[n]] = n
        #
        self.A0_A = A0_t(
            alphaMP_=self.algorithmPar.alphaAmp, eminMP_=self.eminMP, par_=self.par
        )
        self.A0_B = A0_t(
            alphaMP_=self.algorithmPar.alphaBmp, eminMP_=self.eminMP, par_=self.par
        )
        self.A0_C = A0_t(
            alphaMP_=self.algorithmPar.alphaCmp, eminMP_=self.eminMP, par_=self.par
        )
        self.selectA0 = {}
        self.selectA0[algorithmPar.alphaA] = self.A0_A
        self.selectA0[algorithmPar.alphaB] = self.A0_B
        self.selectA0[algorithmPar.alphaC] = self.A0_C
        #
        self.espace_is_filled = False
        #   Lists of result as functions of lambda
        self.rho_list = [[] for _ in range(self.par.Ne)]
        self.drho_list = [[] for _ in range(self.par.Ne)]
        self.gAA0g_list = [[] for _ in range(self.par.Ne)]
        self.lambda_list = [[] for _ in range(self.par.Ne)]
        self.rho_list_alpha2 = [[] for _ in range(self.par.Ne)]
        self.drho_list_alpha2 = [[] for _ in range(self.par.Ne)]
        self.gAA0g_list_alpha2 = [[] for _ in range(self.par.Ne)]
        self.rho_list_alpha3 = [[] for _ in range(self.par.Ne)]
        self.drho_list_alpha3 = [[] for _ in range(self.par.Ne)]
        self.gAA0g_list_alpha3 = [[] for _ in range(self.par.Ne)]
        #   Results
        self.lambda_result = np.ndarray(self.par.Ne, dtype=np.float64)
        self.rho_result = np.ndarray(self.par.Ne, dtype=np.float64)
        self.drho_result = np.ndarray(self.par.Ne, dtype=np.float64)
        self.result_is_filled = np.full(par.Ne, False, dtype=bool)
        self.rho_sys_err = np.ndarray(self.par.Ne, dtype=np.float64)
        self.rho_quadrature_err = np.ndarray(self.par.Ne, dtype=np.float64)
    def fillEspaceMP(self):
        for e_id in range(self.par.Ne):
            self.espaceMP[e_id] = mpf(str(self.espace[e_id]))
            self.espace_dictionary[self.espace[e_id]] = e_id
        self.espace_is_filled = True
    def prepareHLT(self):
        self.fillEspaceMP()
        self.A0_A.evaluate(self.espaceMP)
        if self.algorithmPar.alphaB != 0:
            self.A0_B.evaluate(self.espaceMP)
        if self.algorithmPar.alphaC != 0:
            self.A0_C.evaluate(self.espaceMP)
    def report(self):
        print(LogMessage(), "Inverse problem ::: Time extent:", self.par.time_extent)
        print(LogMessage(), "Inverse problem ::: tmax:", self.par.tmax)
        print(LogMessage(), "Inverse problem ::: Mpi:", self.par.massNorm)
        print(
            LogMessage(),
            "Inverse problem ::: sigma (mp):",
            self.par.sigma,
            "(",
            self.sigmaMP,
            ")",
        )
        print(LogMessage(), "Inverse problem ::: Bootstrap samples:", self.par.num_boot)
        print(LogMessage(), "Inverse problem ::: Number of energies:", self.par.Ne)
        print(
            LogMessage(),
            "Inverse problem ::: Emax (mp) [lattice unit]:",
            self.par.emax,
            self.emaxMP,
        )
        print(
            LogMessage(),
            "Inverse problem ::: Emax [mass units]:",
            self.par.emax / self.par.massNorm,
        )
        print(
            LogMessage(),
            "Inverse problem ::: Emin (mp) [lattice unit]:",
            self.par.emin,
            self.eminMP,
        )
        print(
            LogMessage(),
            "Inverse problem ::: Emin [mass units]:",
            self.par.emin / self.par.massNorm,
        )
        print(
            LogMessage(),
            "Inverse problem ::: alpha (mp):",
            self.par.alpha,
            "(",
            self.alphaMP,
            ")",
        )
        print(
            LogMessage(),
            "Inverse problem ::: E0 (mp):",
            self.par.e0,
            "(",
            self.e0MP,
            ")",
        )
    def lambdaToRho(self, lambda_, estar_, alpha_):
        import time
        #print("Print bnorm: ", self.matrix_bundle.bnorm)
        _Bnorm = (self.matrix_bundle.bnorm / (estar_ * estar_))
        #_Bnorm = (mpf(1.0) / (estar_ * estar_))
        _factor = (lambda_ * self.selectA0[float(alpha_)].valute_at_E_dictionary[estar_]) / _Bnorm

        S_ = Smatrix_mp(
            tmax_=self.par.tmax,
            alpha_=mpf(alpha_),
            e0_=self.par.mpe0,
            type=self.par.periodicity,
            T=mpf(self.par.time_extent),
        )
        _M = S_ + (_factor * self.matrix_bundle.B)
        start_time = time.time()
        _Minv = invert_matrix_ge(_M)
        end_time = time.time()
        print(LogMessage(), "\t \t lambdaToRho ::: Matrix inverted in {:4.4f}".format( end_time - start_time), "s")
        _g_t_estar = h_Et_mp_Eslice(_Minv, self.par, estar_, alpha_=mpf(alpha_))
        rho_estar, drho_estar = y_combine_sample_Eslice_mp(
            _g_t_estar, self.correlator.mpsample, self.par
        )

        gag_estar = gAg(S_, _g_t_estar, estar_, mpf(alpha_), self.par)

        gBg_estar = gBg(_g_t_estar, self.matrix_bundle.B, _Bnorm)

        print(LogMessage(), "\t \t  B / Bnorm = ", float(gBg_estar), " (alpha = ", float(alpha_), ")")
        print(LogMessage(), "\t \t  A / A0 = ", float(gag_estar/self.selectA0[float(alpha_)].valute_at_E_dictionary[estar_])," (alpha = ", float(alpha_), ")")

        return rho_estar, drho_estar, gag_estar
    def lambdaToRho_mod(self, lambda_, estar_, alpha_):
        import time
        #print("Print bnorm: ", self.matrix_bundle.bnorm)
        _Bnorm = (self.matrix_bundle.bnorm / (estar_ * estar_))
        #_Bnorm = (mpf(1.0) / (estar_ * estar_))
        _factor = (lambda_ * self.selectA0[float(alpha_)].valute_at_E_dictionary[estar_]) / _Bnorm

        S_ = Smatrix_mp(
            tmax_=self.par.tmax,
            alpha_=mpf(alpha_),
            e0_=self.par.mpe0,
            type=self.par.periodicity,
            T=mpf(self.par.time_extent),
        )
        _M = S_ + (_factor * self.matrix_bundle.B)
        start_time = time.time()
        _Minv = invert_matrix_ge(_M)
        end_time = time.time()
        print(LogMessage(), "\t \t lambdaToRho ::: Matrix inverted in {:4.4f}".format( end_time - start_time), "s")
        _g_t_estar = h_Et_mp_Eslice(_Minv, self.par, estar_, alpha_=mpf(alpha_))
        rho_estar, drho_estar = y_combine_sample_Eslice_mp(
            _g_t_estar, self.correlator.mpsample, self.par
        )

        gag_estar = gAg(S_, _g_t_estar, estar_, mpf(alpha_), self.par)

        gBg_estar = gBg(_g_t_estar, self.matrix_bundle.B, _Bnorm)

        print(LogMessage(), "\t \t  B / Bnorm = ", float(gBg_estar), " (alpha = ", float(alpha_), ")")
        print(LogMessage(), "\t \t  A / A0 = ", float(gag_estar/self.selectA0[float(alpha_)].valute_at_E_dictionary[estar_])," (alpha = ", float(alpha_), ")")

        return rho_estar, drho_estar, gag_estar, _g_t_estar
    def scanLambda(self, estar_, alpha_):
        lambda_ = self.algorithmPar.lambdaMax
        lambda_step = self.algorithmPar.lambdaStep
        resize = 4
        prec_ = self.algorithmPar.lambdaScanPrec
        cap_ = self.algorithmPar.lambdaScanCap
        _count = 0

        print(LogMessage(), " --- ")
        print(LogMessage(), "Scan Lambda at energy {:2.2e}".format(estar_))

        print(LogMessage(), "Scan Lambda ::: Lambda = ", lambda_)
        _this_rho, _this_drho, _this_gAg = self.lambdaToRho(
            lambda_, estar_, alpha_=alpha_
        )  #   _this_drho will remain the first one
        self.rho_list[self.espace_dictionary[estar_]].append(_this_rho)  #   store
        self.drho_list[self.espace_dictionary[estar_]].append(_this_drho)  #   store
        self.gAA0g_list[self.espace_dictionary[estar_]].append(
            _this_gAg / self.selectA0[alpha_].valute_at_E_dictionary[estar_]
        )  #   store
        #        self.lambda_list.append(lambda_)
        lambda_ -= lambda_step

        while _count < cap_ and lambda_ > self.algorithmPar.lambdaMin:
            print(
                LogMessage(), "Scan Lambda ::: Lambda = {:1.3e}".format(float(lambda_))
            )
            print(
                LogMessage(),
                "Scan Lambda ::: Lambda (old) = {:1.3e}".format(
                    float(lambda_ / (1 + lambda_))
                ),
            )
            _this_updated_rho, _this_updated_drho, _this_gAg = self.lambdaToRho(
                lambda_, estar_, alpha_=alpha_
            )
            self.rho_list[self.espace_dictionary[estar_]].append(
                _this_updated_rho
            )  #   store
            print(
                LogMessage(),
                "Scan Lambda ::: Rho = {:1.3e}".format(float(_this_updated_rho)),
            )
            self.drho_list[self.espace_dictionary[estar_]].append(
                _this_updated_drho
            )  #   store
            self.gAA0g_list[self.espace_dictionary[estar_]].append(
                _this_gAg / self.selectA0[alpha_].valute_at_E_dictionary[estar_]
            )  #   store
            #            self.lambda_list.append(lambda_)
            _residual = abs((_this_updated_rho - _this_rho) / (_this_updated_drho))
            print(LogMessage(), "Scan Lambda ::: Residual = ", float(_residual))
            if _residual < prec_:
                _count += 1
                print(LogMessage(), "Scan Lambda ::: count = ", _count)
            else:
                _count = 0

            _this_rho = _this_updated_rho
            lambda_ -= lambda_step

            if lambda_ <= 0:
                print(LogMessage(), "Resize LambdaStep")
                lambda_step /= resize
                lambda_ += lambda_step * (resize - 1 / resize)

            if lambda_ < self.algorithmPar.lambdaMin:
                print(
                    LogMessage(),
                    f"{bcolors.WARNING}Warning{bcolors.ENDC} ::: Reached lower limit Lambda, did not find optimal lambda",
                )

        self.lambda_result[self.espace_dictionary[estar_]] = lambda_
        self.rho_result[self.espace_dictionary[estar_]] = _this_rho
        self.drho_result[self.espace_dictionary[estar_]] = _this_updated_drho
        self.result_is_filled[self.espace_dictionary[estar_]] = True

        print(LogMessage(), "Scan Lambda ::: Lambda * = ", lambda_)

        return (
            self.rho_list[self.espace_dictionary[estar_]],
            self.drho_list[self.espace_dictionary[estar_]],
            self.gAA0g_list[self.espace_dictionary[estar_]],
        )

    def scanLambdaAlpha(self, estar_, how_many_alphas=2):
        lambda_ = self.algorithmPar.lambdaMax
        lambda_step = self.algorithmPar.lambdaStep
        prec_ = self.algorithmPar.lambdaScanPrec
        cap_ = self.algorithmPar.lambdaScanCap
        _count = 0
        resize = 4
        lambda_flag = 0
        rho_flag = 0
        drho_flag = 0
        comp_diff_AC = _big
        comp_diff_AB = _big

        print(LogMessage(), " --- ")
        print(LogMessage(), "At Energy {:2.2e}".format(estar_))
        print(LogMessage(), "Setting Lambda ::: Lambda (0,inf) = {:1.3e}".format(float(lambda_)))
        print(LogMessage(), "Setting Lambda ::: Lambda (0,1) = {:1.3e}".format(float(lambda_ / (1 + lambda_))))

        # Setting alpha to the first value
        print(LogMessage(), "\t Setting Alpha ::: First Alpha = ", float(self.algorithmPar.alphaA))
        _this_rho, _this_drho, _this_gAg = self.lambdaToRho(lambda_, estar_, self.algorithmPar.alphaAmp)
        self.rho_list[self.espace_dictionary[estar_]].append(_this_rho)  #   store
        self.drho_list[self.espace_dictionary[estar_]].append(_this_drho)  #   store
        self.gAA0g_list[self.espace_dictionary[estar_]].append(_this_gAg/ self.selectA0[self.algorithmPar.alphaA].valute_at_E_dictionary[estar_])  #   store
        self.lambda_list[self.espace_dictionary[estar_]].append(lambda_)  #   store
        print(LogMessage(), "\t \t Rho (Alpha = {:2.2f}) ".format(self.algorithmPar.alphaA), " = {:1.3e}".format(float(_this_rho)), " Stat = {:1.3e}".format(float(_this_drho)))
        # Setting alpha to the second value
        print(LogMessage(), "\t Setting Alpha ::: Second Alpha = ", float(self.algorithmPar.alphaB))
        _this_rho2, _this_drho2, _this_gAg2 = self.lambdaToRho(lambda_, estar_, self.algorithmPar.alphaBmp)  #   _this_drho will remain the first one
        self.rho_list_alpha2[self.espace_dictionary[estar_]].append(_this_rho2)  #   store
        self.drho_list_alpha2[self.espace_dictionary[estar_]].append(_this_drho2)  #   store
        self.gAA0g_list_alpha2[self.espace_dictionary[estar_]].append(_this_gAg2/ self.selectA0[self.algorithmPar.alphaB].valute_at_E_dictionary[estar_])  #   store
        print(LogMessage(), "\t \t Rho (Alpha = {:2.2f}) ".format(self.algorithmPar.alphaB), " = {:1.3e}".format(float(_this_rho2)), " Stat = {:1.3e}".format(float(_this_drho2)))
        # Setting alpha for the third value
        if how_many_alphas == 3:
            print(LogMessage(), "\t Setting Alpha ::: Third Alpha = ", float(self.algorithmPar.alphaC))
            _this_rho3, _this_drho3, _this_gAg3 = self.lambdaToRho(lambda_, estar_, self.algorithmPar.alphaCmp)  # _this_drho will remain the first one
            self.rho_list_alpha3[self.espace_dictionary[estar_]].append(_this_rho3)  # store
            self.drho_list_alpha3[self.espace_dictionary[estar_]].append(_this_drho3)  # store
            self.gAA0g_list_alpha3[self.espace_dictionary[estar_]].append(_this_gAg3/ self.selectA0[self.algorithmPar.alphaC].valute_at_E_dictionary[estar_])  # store
            print(LogMessage(), "\t \t Rho (Alpha = {:2.2f}) ".format(self.algorithmPar.alphaC), " = {:1.3e}".format(float(_this_rho3)), " Stat = {:1.3e}".format(float(_this_drho3)))
        lambda_ -= lambda_step

        while _count < cap_ and lambda_ > self.algorithmPar.lambdaMin:
            print(LogMessage(), "Setting Lambda ::: Lambda (0,inf) = {:1.3e}".format(float(lambda_)))
            print(LogMessage(), "Setting Lambda ::: Lambda (0,1) = {:1.3e}".format(float(lambda_ / (1 + lambda_))))

            print(
                LogMessage(),
                "\t Setting Alpha ::: First Alpha = ",
                self.algorithmPar.alphaA,
            )
            _this_updated_rho, _this_updated_drho, _this_gAg = self.lambdaToRho(
                lambda_, estar_, self.algorithmPar.alphaAmp
            )
            self.rho_list[self.espace_dictionary[estar_]].append(
                _this_updated_rho
            )  #   store
            print(LogMessage(), "\t \t Rho (Alpha = {:2.2f}) ".format(self.algorithmPar.alphaA), " = {:1.3e}".format(float(_this_updated_rho)), " Stat = {:1.3e}".format(float(_this_updated_drho)))
            self.drho_list[self.espace_dictionary[estar_]].append(_this_updated_drho)  #   store
            self.gAA0g_list[self.espace_dictionary[estar_]].append(_this_gAg/ self.selectA0[self.algorithmPar.alphaA].valute_at_E_dictionary[estar_])  #   store
            self.lambda_list[self.espace_dictionary[estar_]].append(lambda_)
            _residual1 = abs((_this_updated_rho - _this_rho) / (_this_updated_drho))
            print(LogMessage(), "\t \t ", f"{bcolors.OKBLUE}Residual{bcolors.ENDC}" + " = ", float(_residual1), "(alpha = {:2.2f}".format(self.algorithmPar.alphaA), ")")

            print(LogMessage(), "\t Setting Alpha ::: Second Alpha = ", self.algorithmPar.alphaB)
            _this_updated_rho2, _this_updated_drho2, _this_gAg2 = self.lambdaToRho(lambda_, estar_, self.algorithmPar.alphaBmp)
            self.rho_list_alpha2[self.espace_dictionary[estar_]].append(_this_updated_rho2)  # store
            print(LogMessage(), "\t \t  Rho (Alpha = {:2.2f}) ".format(self.algorithmPar.alphaB), "= {:1.3e}".format(float(_this_updated_rho2)), "Stat = {:1.3e}".format(float(_this_updated_drho2)))
            self.drho_list_alpha2[self.espace_dictionary[estar_]].append(_this_updated_drho2)  # store
            self.gAA0g_list_alpha2[self.espace_dictionary[estar_]].append(_this_gAg2 / self.selectA0[self.algorithmPar.alphaB].valute_at_E_dictionary[estar_])  # store
            _residual2 = abs((_this_updated_rho2 - _this_rho2) / (_this_updated_drho2))
            print(LogMessage(), "\t \t  Residual = ", float(_residual2), "(alpha = {:2.2f}".format(self.algorithmPar.alphaB), ")")


            if how_many_alphas == 3:
                print(LogMessage(), "\t Setting Alpha ::: Third Alpha = ", self.algorithmPar.alphaC)
                _this_updated_rho3, _this_updated_drho3, _this_gAg3 = self.lambdaToRho(lambda_, estar_, self.algorithmPar.alphaCmp)
                self.rho_list_alpha3[self.espace_dictionary[estar_]].append(_this_updated_rho3)  # store
                print(LogMessage(), "\t \t  Rho (Alpha = {:2.2f}) ".format( self.algorithmPar.alphaC), "= {:1.3e}".format(float(_this_updated_rho3)), "Stat = {:1.3e}".format(float(_this_updated_drho3)))
                self.drho_list_alpha3[self.espace_dictionary[estar_]].append(_this_updated_drho3)  # store
                self.gAA0g_list_alpha3[self.espace_dictionary[estar_]].append(_this_gAg3 / self.selectA0[self.algorithmPar.alphaC].valute_at_E_dictionary[estar_])  # store
                _residual3 = abs((_this_updated_rho3 - _this_rho3) / (_this_updated_drho3))
                print(LogMessage(), "\t \t  Residual ", float(_residual3), "(alpha = {:2.2f}".format(self.algorithmPar.alphaC) )
                comp_diff_AC = abs(_this_updated_rho - _this_updated_rho3) - (_this_updated_drho + _this_updated_drho3)
                print(LogMessage(), "\t \t  Rho Diff at alphas = (0 , -1.99) ::: {:2.2e}".format(float(comp_diff_AC / _this_updated_rho)))
            else:
                comp_diff_AC = comp_diff_AB

            comp_diff_AB = abs(_this_updated_rho - _this_updated_rho2) - (_this_updated_drho + _this_updated_drho2)

            print(LogMessage(), "\t \t  Rho Diff at alphas = (0 : -1) ::: {:2.2E}".format( float(comp_diff_AB / _this_updated_rho)))
            if (
                _this_gAg / self.selectA0[self.algorithmPar.alphaA].valute_at_E_dictionary[estar_] < self.par.A0cut
                and _residual1 < prec_
                #and _residual2 < prec_
                and comp_diff_AB < 0    #-(_this_updated_drho2 * 0.1)
                and comp_diff_AC < 0    #-(_this_updated_drho * 0.1)
            ):
                if _count == 1:
                    lambda_flag = lambda_
                    rho_flag = _this_updated_rho
                    drho_flag = _this_updated_drho
                _count += 1
                print(LogMessage(), f"{bcolors.OKGREEN}Counting{bcolors.ENDC}", _count)
            else:
                _count = 0

            _this_rho = _this_updated_rho
            _this_rho2 = _this_updated_rho2
            lambda_ -= lambda_step

            print(LogMessage(), "\t Ending while loop with lambda = ", lambda_ , "lambdaMin = ", self.algorithmPar.lambdaMin)

            if lambda_ <= 0:
                lambda_step /= resize
                lambda_ += lambda_step * (resize - 1 / resize)
                print(LogMessage(), "Resize LambdaStep to ", lambda_step, "Setting Lambda = ", lambda_)

            if lambda_ < self.algorithmPar.lambdaMin:
                print(
                    LogMessage(),
                    f"{bcolors.WARNING}Warning{bcolors.ENDC} ::: Reached lower limit Lambda, did not find optimal lambda",
                )

        #   while loop ends here

        if rho_flag != 0:   #   if count was at filled at least once
            self.lambda_result[self.espace_dictionary[estar_]] = lambda_flag
            self.rho_result[self.espace_dictionary[estar_]] = rho_flag
            self.drho_result[self.espace_dictionary[estar_]] = drho_flag
        else:
            print(
                LogMessage(),
                f"{bcolors.WARNING}Warning{bcolors.ENDC} ::: Did not find optimal lambda through plateau",
            )
            self.lambda_result[self.espace_dictionary[estar_]] = lambda_
            if how_many_alphas > 1:
                self.rho_result[self.espace_dictionary[estar_]] =  self.rho_list[self.espace_dictionary[estar_]][-1]
                self.drho_result[self.espace_dictionary[estar_]] =self.drho_list[self.espace_dictionary[estar_]][-1]
            else:
                self.rho_result[self.espace_dictionary[estar_]] = self.rho_list[self.espace_dictionary[estar_]][
                    -1]  # _this_rho
                self.drho_result[self.espace_dictionary[estar_]] = self.drho_list[self.espace_dictionary[estar_]][
                    -1]  # _this_drho

        print(
            LogMessage(),
            "Result ::: E = ",
            estar_,
            "Rho = ",
            float(self.rho_result[self.espace_dictionary[estar_]]),
            "Stat = ",
            float(self.drho_result[self.espace_dictionary[estar_]]),
            "Lambda = ",
            float(self.lambda_result[self.espace_dictionary[estar_]]),
        )

        self.result_is_filled[self.espace_dictionary[estar_]] = True

        print(
            LogMessage(),
            "Scan Lambda ::: Lambda * = ",
            lambda_,
            "at E = ",
            estar_,
        )

        return (
            self.rho_list[self.espace_dictionary[estar_]],
            self.drho_list[self.espace_dictionary[estar_]],
            self.gAA0g_list[self.espace_dictionary[estar_]],
            self.rho_list_alpha2[self.espace_dictionary[estar_]],
            self.drho_list_alpha2[self.espace_dictionary[estar_]],
            self.gAA0g_list_alpha2[self.espace_dictionary[estar_]],
        )

    def estimate_sys_error(self, estar_):
        assert self.result_is_filled[self.espace_dictionary[estar_]] == True

        _this_y = self.rho_result[self.espace_dictionary[estar_]]  #   rho at lambda*
        _that_y, _that_yerr, _that_x = self.lambdaToRho(
            self.lambda_result[self.espace_dictionary[estar_]]
            * self.algorithmPar.kfactor,
            estar_,
            alpha_=0,
        )

        self.rho_sys_err[self.espace_dictionary[estar_]] = abs(_this_y - _that_y) / 2
        self.rho_quadrature_err[self.espace_dictionary[estar_]] = np.sqrt(
            self.rho_sys_err[self.espace_dictionary[estar_]] ** 2
            + self.drho_result[self.espace_dictionary[estar_]] ** 2
        )

        with open(os.path.join(self.par.logpath, 'Result.txt'), "a") as output:
            print(estar_,
                float(self.lambda_result[self.espace_dictionary[estar_]]),
                float(self.rho_result[self.espace_dictionary[estar_]]),
                float(self.drho_result[self.espace_dictionary[estar_]]),
                float(self.rho_sys_err[self.espace_dictionary[estar_]]),
                float(self.rho_quadrature_err[self.espace_dictionary[estar_]]),
                file=output)

        return self.rho_sys_err[self.espace_dictionary[estar_]]

    def plotKernel(self, _e):
        # Activating text rendering by LaTeX
        plt.style.use("paperdraft.mplstyle")
        _, _, _, gt = self.lambdaToRho_mod(lambda_=self.lambda_result[_e], estar_=self.espace[_e], alpha_=self.algorithmPar.alphaAmp)

        self._plotKernel(gt, ne_=60, omega=self.espace[_e], alpha_ = self.algorithmPar.alphaA, ker_type=self.par.kerneltype)

    def _plotKernel(self, gt_, omega, alpha_, ne_=150, ker_type = 'GAUSS'):
        # Activating text rendering by LaTeX
        plt.style.use("paperdraft.mplstyle")
        #plt.figure(figsize=(4.5, 2.0))
        energies = np.linspace(self.par.massNorm*0.05, self.par.massNorm*4.0, ne_)
        kernel = np.zeros(ne_)
        for _e in range(len(energies)):
            kernel[_e] = combine_base_Eslice(gt_, self.par, energies[_e])
        plt.plot(
            energies / self.par.massNorm,
            kernel,
            marker="o",
            markersize=5.8,
            ls="--",
            linewidth = 1.2,
            label="$\omega/m_0$ = " + "{:2.1e}".format(omega/self.par.massNorm),
            color='black',
            markerfacecolor=CB_colors[0],
        )

        y_to_plot = []
        if ker_type == 'CAUCHY':
            def ker(k, sigma_, omega_):
                aux = omega_ - k
                aux = aux * aux + sigma_ * sigma_
                aux = sigma_ / aux
                return aux
            y_to_plot = ker(energies, self.par.sigma, omega)

        elif ker_type == 'GAUSS':
            y_to_plot = gauss_fp(energies, omega, self.par.sigma, norm="half")

        plt.plot(
            energies / self.par.massNorm,
            y_to_plot,
            ls = '-',
            label = 'Target',
            color='red',
            linewidth=1.2,
        )

        with open(os.path.join(self.par.logpath, f'kernel_{omega}.txt'), "a") as output:
            for e_i in range(len(energies)):
                print(energies[e_i] / self.par.massNorm,
                    kernel[e_i],
                    file=output)

        plt.title(r" $\sigma$" + " = {:2.2f}".format(self.par.sigma / self.par.massNorm) + r"$m_V$ " + " $\;$ "+ r"$\alpha$ = {:2.1f}".format(alpha_), fontsize=13)
        #plt.ylim((-0.1, 6.5))
        plt.xlabel(r"$E / m_{0}$", fontsize = 13)
        plt.legend(fontsize=9, loc=1, frameon=False)
        #plt.tight_layout()
        plt.savefig(
            os.path.join(
                self.par.plotpath,
                "SmearingKernelSigma{:2.2e}".format(self.par.sigma)
                + "Enorm{:2.2e}".format(self.par.massNorm)
                + "Energy{:2.2e}".format(omega)
                + "Alpha{:2.2f}".format(alpha_)
                + ".png",
            ),
            dpi=300, bbox_inches='tight'
        )
        plt.clf()
        return

    def run(self, how_many_alphas=1, saveplots=True, plot_live=False):

        with open(os.path.join(self.par.logpath, 'Result.txt'), "w") as output:
            print("# Energy \t Lambda \t Rho \t Stat \t Sys \t Quadrature ", file=output)

        if how_many_alphas == 1:
            for e_i in range(self.par.Ne):
                _, _, _ = self.scanLambda(
                    self.espace[e_i], alpha_=self.algorithmPar.alphaAmp
                )
                self.plotKernel(e_i)
                _ = self.estimate_sys_error(self.espace[e_i])
                self.plotStability(estar=self.espace[e_i], savePlot=saveplots)
            print(
                LogMessage(),
                "Rho Stat Sys = ",
                self.rho_result,
                self.drho_result,
                self.rho_sys_err,
            )
            return
        elif how_many_alphas == 2 or how_many_alphas == 3:
            for e_i in range(self.par.Ne):
                '''
                if e_i < 6:
                    self.algorithmPar.lambdaMin = 0.1
                    self.algorithmPar.lambdaScanCap = 9
                    self.algorithmPar.lambdaScanPrec=0.1
                    self.algorithmPar.lambdaMax= 0.9
                    self.algorithmPar.lambdaStep =self.algorithmPar.lambdaMax / 6
                else:
                    self.algorithmPar.lambdaMin = 0.1
                    self.algorithmPar.lambdaScanCap = 9
                    self.algorithmPar.lambdaScanPrec = 0.1
                    self.algorithmPar.lambdaMax = 2e+2
                    self.algorithmPar.lambdaStep = self.algorithmPar.lambdaMax / 2
                '''
                '''
                elif e_i < 5 and e_i >= 4:
                    self.algorithmPar.lambdaMin = 1e6
                    self.algorithmPar.lambdaScanCap = 10
                    self.algorithmPar.lambdaMax= 1e7
                    self.algorithmPar.lambdaStep =(self.algorithmPar.lambdaMax - self.algorithmPar.lambdaMin) / 10
                elif e_i < 6 and e_i >= 5:
                    self.algorithmPar.lambdaMin = 1
                    self.algorithmPar.lambdaScanCap = 10
                    self.algorithmPar.lambdaMax= 1e5
                    self.algorithmPar.lambdaStep = self.algorithmPar.lambdaMax / 2
                elif e_i < 7 and e_i >= 6:
                    self.algorithmPar.lambdaMin = 1
                    self.algorithmPar.lambdaScanCap = 10
                    self.algorithmPar.lambdaMax = 1e5
                    self.algorithmPar.lambdaStep = self.algorithmPar.lambdaMax / 2
                else:
                    self.algorithmPar.lambdaMin = 1
                    self.algorithmPar.lambdaScanCap = 10
                    self.algorithmPar.lambdaMax = 1e5
                    self.algorithmPar.lambdaStep = self.algorithmPar.lambdaMax / 2
                '''
                _, _, _, _, _, _ = self.scanLambdaAlpha(self.espace[e_i], how_many_alphas=how_many_alphas)
                self.plotKernel(e_i)
                _ = self.estimate_sys_error(self.espace[e_i])
                if saveplots==True:
                    self.plotStabilityMultipleAlpha(estar=self.espace[e_i], savePlot=saveplots, nalphas=how_many_alphas, plot_live=plot_live)
            print(
                LogMessage(),
                "Energies Rho Stat Sys = ",
                self.espace,
                self.rho_result,
                self.drho_result,
                self.rho_sys_err,
            )
            return
        else:
            raise ValueError(
                "how_many_alphas : Invalid value specified. Only 1, 2 or 3 are allowed."
            )

    def plotParameterScan(self, how_many_alphas=1, save_plots=True, plot_live=False):
        assert all(self.result_is_filled) == True
        if how_many_alphas == 1:
            for e_i in range(self.par.Ne):
                self.plotStability(estar=self.espace[e_i], savePlot=save_plots)
            return
        elif how_many_alphas == 2 or how_many_alphas == 3:
            for e_i in range(self.par.Ne):
                self.plotStabilityMultipleAlpha(
                    estar=self.espace[e_i], savePlot=save_plots, nalphas=how_many_alphas
                )
            return
        else:
            raise ValueError(
                "how_many_alphas : Invalid value specified. Only 1, 2 or 3 are allowed."
            )

    def plotRhos(self, savePlot=True):
        plt.errorbar(
            x=self.espace / self.par.massNorm,
            y=np.array(self.rho_result, dtype=float),
            yerr=np.array(self.drho_result, dtype=float),
            marker="o",
            markersize=1.5,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label="Stat",
            color=CB_color_cycle[0],
        )

        plt.errorbar(
            x=self.espace / self.par.massNorm,
            y=np.array(self.rho_result, dtype=float),
            yerr=np.array(self.rho_sys_err, dtype=float),
            marker="o",
            markersize=1.5,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label="Sys",
            color=CB_color_cycle[1],
        )

        plt.errorbar(
            x=self.espace / self.par.massNorm,
            y=np.array(self.rho_result, dtype=float),
            yerr=np.array(self.rho_quadrature_err, dtype=float),
            marker="o",
            markersize=1.5,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label="Quadrature Sum",
            color=CB_color_cycle[2],
        )

        plt.title(
            r" $\sigma$" + " = {:2.2f} Mpi".format(self.par.sigma / self.par.massNorm)
        )
        plt.xlabel(r"$E / M_{\pi}$", fontdict=timesfont)
        # plt.ylabel("Spectral density", fontdict=u.timesfont)
        plt.legend(prop={"size": 12, "family": "Helvetica"})
        plt.grid()
        plt.tight_layout()
        if savePlot == True:
            plt.savefig(
                os.path.join(
                    self.par.plotpath,
                    "RhoSigma{:2.2e}".format(self.par.sigma)
                    + "Enorm{:2.2e}".format(self.par.massNorm)
                    + ".png",
                ),
                dpi=300,
            )
        plt.clf()
        return

    def plotStability(self, estar: float, savePlot=True):
        # Activating text rendering by LaTeX
        plt.style.use("paperdraft.mplstyle")
        plt.errorbar(
            x=np.array(self.gAA0g_list[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list[self.espace_dictionary[estar]], dtype=float),
            marker="o",
            markersize=1.5,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaA),
            color=CB_color_cycle[0],
        )
        plt.title(
            r"$E/M_{\pi}$"
            + "= {:2.2f}  ".format(estar / self.par.massNorm)
            + r" $\sigma$"
            + " = {:2.2f} Mpi".format(self.par.sigma / self.par.massNorm)
        )
        plt.xlabel(r"$A[g_\lambda] / A_0$", fontdict=timesfont)
        # plt.ylabel("Spectral density", fontdict=u.timesfont)
        plt.legend(prop={"size": 12, "family": "Helvetica"})
        plt.grid()
        plt.tight_layout()
        if savePlot == True:
            plt.savefig(
                os.path.join(
                    self.par.plotpath, "LambdaScanE{:2.2e}".format(estar) + ".png"
                ),
                dpi=300,
            )
        plt.clf()
        return

    def plotStabilityMultipleAlpha(self, estar: float, savePlot=True, nalphas=2, plot_live=False):
        # Activating text rendering by LaTeX
        plt.style.use("paperdraft.mplstyle")
        fig, ax = plt.subplots(2, 1, figsize=(6, 8))
        plt.title(
            "$E/m_{0}$"
            + "= {:2.2f}        ".format(estar / self.par.massNorm)
            + r" $\sigma$"
            + " = {:2.2f}".format(self.par.sigma / self.par.massNorm)
            + "$m_{0}$", fontsize=14
        )
        ax[0].errorbar(
            x=np.array(self.lambda_list[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list[self.espace_dictionary[estar]], dtype=float),
            marker=plot_markers[0],
            markersize=3.8,
            elinewidth=1.4,
            capsize=3,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaA),
            color=CB_colors[0],
        )
        ax[0].errorbar(
            x=np.array(self.lambda_list[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list_alpha2[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list_alpha2[self.espace_dictionary[estar]], dtype=float),
            marker=plot_markers[1],
            markersize=3.8,
            elinewidth=1.4,
            capsize=3,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaB),
            color=CB_colors[1],
        )
        if nalphas == 3:
            ax[0].errorbar(
                x=np.array(self.lambda_list[self.espace_dictionary[estar]], dtype=float),
                y=np.array(self.rho_list_alpha3[self.espace_dictionary[estar]], dtype=float),
                yerr=np.array(self.drho_list_alpha3[self.espace_dictionary[estar]], dtype=float),
                marker=plot_markers[1],
                markersize=3.8,
                elinewidth=1.4,
                capsize=3,
                ls="",
                label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaC),
                color=CB_colors[2],
            )

        ax[0].axhspan(
            ymin=float(self.rho_result[self.espace_dictionary[estar]]
            - self.drho_result[self.espace_dictionary[estar]]),
            ymax=float(self.rho_result[self.espace_dictionary[estar]]
            + self.drho_result[self.espace_dictionary[estar]]),
            alpha=0.3,
            color=CB_colors[4],
        )
        ax[0].set_xlabel(r"$\lambda$", fontdict=timesfont)
        ax[0].set_ylabel(r"$\rho_\sigma$", fontdict=timesfont)
        ax[0].legend(prop={"size": 14, "family": "Helvetica"})
        ax[0].set_xscale('log')
        ax[0].grid()

        # Second subplot with A/A_0
        ax[1].errorbar(
            x=np.array(self.gAA0g_list[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list[self.espace_dictionary[estar]], dtype=float),
            marker=plot_markers[0],
            markersize=3.8,
            elinewidth=1.4,
            capsize=3,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaA),
            color=CB_colors[0],
        )
        '''
        ax[1].errorbar(
            x=np.array(self.gAA0g_list_alpha2[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list_alpha2[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list_alpha2[self.espace_dictionary[estar]], dtype=float),
            marker=plot_markers[1],
            markersize=2,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaB),
            color=CB_colors[1],
        )
        ax[1].errorbar(
            x=np.array(self.gAA0g_list_alpha3[self.espace_dictionary[estar]], dtype=float),
            y=np.array(self.rho_list_alpha3[self.espace_dictionary[estar]], dtype=float),
            yerr=np.array(self.drho_list_alpha3[self.espace_dictionary[estar]], dtype=float),
            marker=plot_markers[2],
            markersize=2,
            elinewidth=1.3,
            capsize=2,
            ls="",
            label=r"$\alpha = {:1.2f}$".format(self.algorithmPar.alphaC),
            color=CB_colors[2],
        )
        '''
        ax[1].axhspan(
            ymin=float(self.rho_result[self.espace_dictionary[estar]]
            - self.drho_result[self.espace_dictionary[estar]]),
            ymax=float(self.rho_result[self.espace_dictionary[estar]]
            + self.drho_result[self.espace_dictionary[estar]]),
            alpha=0.3,
            color=CB_colors[4],
        )
        ax[1].set_xscale('log')
        ax[1].set_xlabel(r"$A[g_\lambda] / A_0$", fontdict=timesfont)
        ax[1].set_ylabel(r"$\rho_\sigma$", fontdict=timesfont)
        ax[1].legend(prop={"size": 14, "family": "Helvetica"})
        ax[1].grid()
        plt.tight_layout()
        if savePlot == True:
            plt.savefig(
                os.path.join(
                    self.par.plotpath,
                    "LambdaScanE{:2.2e}".format(self.espace_dictionary[estar]) + ".png",
                ),
                dpi=300,
            )
        if plot_live==True:
            plt.show()
        plt.clf()
        plt.close(fig)
