import jax.numpy as jnp
from src.newton import newtonRaphson
from src.utils import pressure, waveSpeed

def solveAnastomosis(u1, u2, u3, 
                     A1, A2, A3,
                     A01, A02, A03,
                     beta1, beta2, beta3,
                     gamma1, gamma2, gamma3,
                     Pext1, Pext2, Pext3):
    U0 = jnp.array((u1,
                    u2,
                    u3,
                    jnp.sqrt(jnp.sqrt(A1)),
                    jnp.sqrt(jnp.sqrt(A2)),
                    jnp.sqrt(jnp.sqrt(A3))), dtype=jnp.float64)

    k1 = jnp.sqrt(1.5*gamma1)
    k2 = jnp.sqrt(1.5*gamma2)
    k3 = jnp.sqrt(1.5*gamma3)
    k = jnp.array([k1, k2, k3], dtype=jnp.float64)

    J = calculateJacobianAnastomosis(U0, k,
                                     A01, A02, A03,
                                     beta1, beta2, beta3)
    U = newtonRaphson(calculateWstarAnastomosis, calculateFAnastomosis, 
                      J, U0, k,
                      (A01, A02, A03),
                      (beta1, beta2, beta3))[0]
        
    #jax.debug.breakpoint()

    return updateAnastomosis(U,
                             A01, A02, A03,
                             beta1, beta2, beta3,
                             gamma1, gamma2, gamma3,
                             Pext1, Pext2, Pext3)

def calculateJacobianAnastomosis(U, k,
                                 A01, A02, A03,
                                 beta1, beta2, beta3):
    U43 = U[3]**3
    U53 = U[4]**3
    U63 = U[5]**3

    J14 =  4.0 * k[0]
    J25 =  4.0 * k[1]
    J36 = -4.0 * k[2]

    J41 =  U[3] * U43
    J42 =  U[4] * U53
    J43 = -U[5] * U63
    J44 =   4.0 * U[0] * U43
    J45 =   4.0 * U[1] * U53
    J46 =  -4.0 * U[2] * U63

    J54 =  2.0 * beta1 * U[3] * jnp.sqrt(1/A01)
    J56 = -2.0 * beta3 * U[5] * jnp.sqrt(1/A03)

    J65 =  2.0 * beta2 * U[4] * jnp.sqrt(1/A02)
    J66 = -2.0 * beta3 * U[5] * jnp.sqrt(1/A03)

    return jnp.array([[1.0, 0.0, 0.0, J14, 0.0, 0.0],
                      [0.0, 1.0, 0.0, 0.0, J25, 0.0],
                      [0.0, 0.0, 1.0, 0.0, 0.0, J36],
                      [J41, J42, J43, J44, J45, J46],
                      [0.0, 0.0, 0.0, J54, 0.0, J56],
                      [0.0, 0.0, 0.0, 0.0, J65, J66]], dtype=jnp.float64)

def calculateWstarAnastomosis(U, k):
    W1 = U[0] + 4 * k[0] * U[3]
    W2 = U[1] + 4 * k[1] * U[4]
    W3 = U[2] - 4 * k[2] * U[5]

    return jnp.array([W1, W2, W3], dtype=jnp.float64)

def calculateFAnastomosis(U, k, W,
                          A0s,
                          betas):
    A01, A02, A03 = A0s
    beta1, beta2, beta3 = betas

    U42 = U[3]**2
    U52 = U[4]**2
    U62 = U[5]**2

    f1 = U[0] + 4 * k[0] * U[3] - W[0]
    f2 = U[1] + 4 * k[1] * U[4] - W[1]
    f3 = U[2] - 4 * k[2] * U[5] - W[2]
    f4 = U[0] * U42**2 + U[1] * U52**2 - U[2] * U62**2

    f5 = beta1 * (U42 * jnp.sqrt(1/A01) - 1.0) - (beta3 * (U62 * jnp.sqrt(1/A03) - 1.0))
    f6 = beta2 * (U52 * jnp.sqrt(1/A02) - 1.0) - (beta3 * (U62 * jnp.sqrt(1/A03) - 1.0))

    return jnp.array([f1, f2, f3, f4, f5, f6], dtype=jnp.float64)

def updateAnastomosis(U,
                      A01, A02, A03,
                      beta1, beta2, beta3,
                      gamma1, gamma2, gamma3,
                      Pext1, Pext2, Pext3):
    u1 = U[0]
    u2 = U[1]
    u3 = U[2]

    A1 = U[3]**4
    A2 = U[4]**4
    A3 = U[5]**4

    Q1 = u1 * A1
    Q2 = u2 * A2
    Q3 = u3 * A3

    c1 = waveSpeed(A1, gamma1)
    c2 = waveSpeed(A2, gamma2)
    c3 = waveSpeed(A3, gamma3)

    P1 = pressure(A1, A01, beta1, Pext1)
    P2 = pressure(A2, A02, beta2, Pext2)
    P3 = pressure(A3, A03, beta3, Pext3)

    return u1, u2, u3, Q1, Q2, Q3, A1, A2, A3, c1, c2, c3, P1, P2, P3
