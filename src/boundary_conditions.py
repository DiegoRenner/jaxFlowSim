import jax.numpy as jnp
from jax import lax, debug
from src.utils import pressure

def setInletBC(inlet, u0, u1, 
               A, c0, c1, 
               t, dt, input_data, 
               cardiac_T, invDx, A0, 
               beta, P_ext):
    Q0, P0 = lax.cond(inlet==1, lambda:(inputFromData(t, input_data.transpose(), cardiac_T),0.0), 
                                lambda:(0.0,inputFromData(t, input_data.transpose(), cardiac_T)))
    return inletCompatibility(inlet, u0, u1, 
                              Q0, A, c0, 
                              c1, P0, dt, 
                              invDx, A0, beta, 
                              P_ext)


def inputFromData(t, input_data, cardiac_T):
    idt = input_data[:, 0]
    idt1 = idt
    idt1 = idt1.at[:-1].set(idt1[1:])
    idq = input_data[:, 1]

    t_hat = t // cardiac_T
    t -= t_hat * cardiac_T

    idx = jnp.where((t >= idt) & (t <= idt1), jnp.arange(0,idt.size,1),jnp.zeros(idt.size)).sum().astype(int) #[0][0]

    qu = idq[idx] + (t - idt[idx]) * (idq[idx+1] - idq[idx]) / (idt[idx+1] - idt[idx])

    return qu

def inletCompatibility(inlet, u0, u1, Q0, A, c0, c1, P0, dt, invDx, A0, beta, Pext):
    W11, W21 = riemannInvariants(u0, c0)
    W12, _ = riemannInvariants(u1, c1)

    W11 += (W12 - W11) * (c0 - u0) * dt * invDx
    W21 = 2.0 * Q0 / A - W11

    u0, c0 = inverseRiemannInvariants(W11, W21)

    return lax.cond(inlet == 1, lambda: (Q0,  Q0/u0), lambda: (u0 * areaFromPressure(P0, A0, beta, Pext), areaFromPressure(P0, A0, beta, Pext)))

def riemannInvariants(u, c):
    W1 = u - 4.0 * c
    W2 = u + 4.0 * c

    return W1, W2


def inverseRiemannInvariants(W1, W2):
    u = 0.5 * (W1 + W2)
    c = (W2 - W1) * 0.125

    return u, c

def areaFromPressure(P, A0, beta, P_ext):
    return A0 * ((P - P_ext) / beta + 1.0) * ((P - P_ext) / beta + 1.0)

def setOutletBC(dt, u1, u2, 
                Q1, A1, c1, 
                c2, P1, P2, 
                P3, Pc, W1M0, 
                W2M0, A0, beta, 
                gamma, dx, P_ext, 
                outlet, Rt, R1, 
                R2, Cc):
    def outletCompatibility_wrapper(dt, u1, u2, 
                                    Q1, A1, c1, 
                                    c2, P1, P2, 
                                    P3, Pc, W1M0, 
                                    W2M0, A0, beta, 
                                    gamma, dx, Pext, 
                                    outlet, Rt, R1, 
                                    R2, Cc):
        P1_out = 2.0 * P2 - P3
        u1_out, Q1_out, c1_out = outletCompatibility(u1, u2, A1, 
                                                     c1, c2, W1M0, 
                                                     W2M0, dt, dx, 
                                                     Rt)
        return u1_out, Q1_out, A1, c1_out, P1_out, Pc

    def threeElementWindkessel_wrapper(dt, u1, u2, 
                                       Q1, A1, c1, 
                                       c2, P1, P2, 
                                       P3, Pc, W1M0, 
                                       W2M0, A0, beta, 
                                       gamma, dx, Pext, 
                                       outlet, Rt, R1, 
                                       R2, Cc):
        u1_out, A1_out, Pc_out = threeElementWindkessel(dt, u1, A1, 
                                                        Pc, Cc, R1, 
                                                        R2, beta, gamma, 
                                                        A0, Pext)
        return u1_out, Q1, A1_out, c1, P1, Pc_out
    return lax.cond(outlet == 1,
                  lambda dt, u1, u2, 
                            Q1, A1, c1, 
                            c2, P1, P2, 
                            P3, Pc, W1M0, 
                            W2M0, A0, beta, 
                            gamma, dx, Pext, 
                            outlet, Rt, R1, 
                            R2, Cc: outletCompatibility_wrapper(dt, u1, u2, 
                                                                Q1, A1, c1, 
                                                                c2, P1, P2, 
                                                                P3, Pc, W1M0, 
                                                                W2M0, A0, beta, 
                                                                gamma, dx, Pext, 
                                                                outlet, Rt, R1, 
                                                                R2, Cc),
                  lambda dt, u1, u2, 
                            Q1, A1, c1, 
                            c2, P1, P2, 
                            P3, Pc, W1M0, 
                            W2M0, A0, beta, 
                            gamma, dx, Pext, 
                            outlet, Rt, R1, 
                            R2, Cc: threeElementWindkessel_wrapper(dt, u1, u2, 
                                                                   Q1, A1, c1, 
                                                                   c2, P1, P2, 
                                                                   P3, Pc, W1M0, 
                                                                   W2M0, A0, beta, 
                                                                   gamma, dx, Pext, 
                                                                   outlet, Rt, R1, 
                                                                   R2, Cc), 
                  dt, u1, u2, 
                  Q1, A1, c1, 
                  c2, P1, P2, 
                  P3, Pc, W1M0, 
                  W2M0, A0, beta, 
                  gamma, dx, P_ext, 
                  outlet, Rt, R1, 
                  R2, Cc)


def outletCompatibility(u1, u2, A1, 
                        c1, c2, W1M0, 
                        W2M0, dt, dx, 
                        Rt):
    _, W2M1 = riemannInvariants(u2, c2)
    W1M, W2M = riemannInvariants(u1, c1)

    W2M += (W2M1 - W2M) * (u1 + c1) * dt / dx
    W1M = W1M0 - Rt * (W2M - W2M0)

    u1, c1 = inverseRiemannInvariants(W1M, W2M)
    Q1 = A1 * u1

    return u1, Q1, c1

def threeElementWindkessel(dt, u1, A1, 
                           Pc, Cc, R1, 
                           R2, beta, gamma, 
                           A0, Pext):
    Pout = 0.0

    Al = A1
    ul = u1
    Pc += dt / Cc * (Al * ul - (Pc - Pout) / R2)

    As = Al
    ssAl = jnp.sqrt(jnp.sqrt(Al))
    sgamma = 2 * jnp.sqrt(6 * gamma)
    sA0 = jnp.sqrt(A0)
    bA0 = beta / sA0

    def fun(As):
        return As * R1 * (ul + sgamma * (ssAl - jnp.sqrt(jnp.sqrt(As)))) - (Pext + bA0 * (jnp.sqrt(As) - sA0)) + Pc

    def dfun(As):
        return R1 * (ul + sgamma * (ssAl - 1.25 * jnp.sqrt(jnp.sqrt(As)))) - bA0 * 0.5 / jnp.sqrt(As)
    def newtonSolver(x0):
        xn = x0 - fun(x0) / dfun(x0)

        return xn

    As = newtonSolver(As)

    us = (pressure(As, A0, beta, Pext) - Pout) / (As * R1)

    A1 = As
    u1 = us

    return u1, A1, Pc
