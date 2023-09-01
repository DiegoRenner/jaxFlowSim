import jax.numpy as jnp
from jax import jit
from src.newton import newtonRaphson
from src.utils import pressure, waveSpeed
import src.initialise as ini
from functools import partial
import jax


#@jit
@partial(jit, static_argnums=(3,4,5,))
def solveAnastomosis(v1, v2, v3, l, m, n):
    U0 = jnp.array([v1.u[-1],
                    v2.u[-1],
                    v3.u[0],
                    jnp.sqrt(jnp.sqrt(v1.A[-1])),
                    jnp.sqrt(jnp.sqrt(v2.A[-1])),
                    jnp.sqrt(jnp.sqrt(v3.A[0]))])

    k1 = ini.VCS[l].s_15_gamma[-1]
    k2 = ini.VCS[m].s_15_gamma[-1]
    k3 = ini.VCS[n].s_15_gamma[0]
    k = jnp.array([k1, k2, k3])

    J = calculateJacobianAnastomosis(v1, v2, v3, U0, k, (l, m, n))
    U = newtonRaphson([v1, v2, v3], J, U0, k, calculateWstarAnastomosis, calculateFAnastomosis, (l,m,n))[0]
        
    #jax.debug.breakpoint()

    return updateAnastomosis(U, v1, v2, v3, l, m, n)

#@jit
@partial(jit, static_argnums=(5,))
def calculateJacobianAnastomosis(v1, v2, v3, U, k, indices):
    l, m, n = indices
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

    J54 =  2.0 * ini.VCS[l].beta[-1] * U[3] * ini.VCS[l].s_inv_A0[-1]
    J56 = -2.0 * ini.VCS[n].beta[0] * U[5] * ini.VCS[n].s_inv_A0[0]

    J65 =  2.0 * ini.VCS[m].beta[-1] * U[4] * ini.VCS[m].s_inv_A0[-1]
    J66 = -2.0 * ini.VCS[n].beta[0] * U[5] * ini.VCS[n].s_inv_A0[0]

    return jnp.array([[1.0, 0.0, 0.0, J14, 0.0, 0.0],
                      [0.0, 1.0, 0.0, 0.0, J25, 0.0],
                      [0.0, 0.0, 1.0, 0.0, 0.0, J36],
                      [J41, J42, J43, J44, J45, J46],
                      [0.0, 0.0, 0.0, J54, 0.0, J56],
                      [0.0, 0.0, 0.0, 0.0, J65, J66]])

@jit
def calculateWstarAnastomosis(U, k):
    W1 = U[0] + 4 * k[0] * U[3]
    W2 = U[1] + 4 * k[1] * U[4]
    W3 = U[2] - 4 * k[2] * U[5]

    return jnp.array([W1, W2, W3])

#@jit
@partial(jit, static_argnums=(4,))
def calculateFAnastomosis(vessels, U, k, W, indices):
    l, m, n = indices
    v1 = vessels[0]
    v2 = vessels[1]
    v3 = vessels[2]

    U42 = U[3]**2
    U52 = U[4]**2
    U62 = U[5]**2

    f1 = U[0] + 4 * k[0] * U[3] - W[0]
    f2 = U[1] + 4 * k[1] * U[4] - W[1]
    f3 = U[2] - 4 * k[2] * U[5] - W[2]
    f4 = U[0] * U42**2 + U[1] * U52**2 - U[2] * U62**2

    f5 = ini.VCS[l].beta[-1] * (U42 * ini.VCS[l].s_inv_A0[-1] - 1.0) - (ini.VCS[n].beta[0] * (U62 * ini.VCS[n].s_inv_A0[0] - 1.0))
    f6 = ini.VCS[m].beta[0] * (U52 * ini.VCS[m].s_inv_A0[-1] - 1.0) - (ini.VCS[n].beta[0] * (U62 * ini.VCS[n].s_inv_A0[0] - 1.0))

    return jnp.array([f1, f2, f3, f4, f5, f6])

#@jit
@partial(jit, static_argnums=(4,5,6))
def updateAnastomosis(U, v1, v2, v3, l, m, n):
    v1.u = v1.u.at[-1].set(U[0])
    v2.u = v2.u.at[-1].set(U[1])
    v3.u = v3.u.at[0].set(U[2])

    v1.A = v1.A.at[-1].set(U[3]**4)
    v2.A = v2.A.at[-1].set(U[4]**4)
    v3.A = v3.A.at[0].set(U[5]**4)

    v1.Q = v1.Q.at[-1].set(v1.u[-1] * v1.A[-1])
    v2.Q = v2.Q.at[-1].set(v2.u[-1] * v2.A[-1])
    v3.Q = v3.Q.at[0].set(v3.u[0] * v3.A[0])

    v1.P = v1.P.at[-1].set(pressure(v1.A[-1], ini.VCS[l].A0[-1], ini.VCS[l].beta[-1], ini.VCS[l].Pext))
    v2.P = v2.P.at[-1].set(pressure(v2.A[-1], ini.VCS[m].A0[-1], ini.VCS[m].beta[-1], ini.VCS[m].Pext))
    v3.P = v3.P.at[0].set(pressure(v3.A[0], ini.VCS[n].A0[0], ini.VCS[n].beta[0], ini.VCS[n].Pext))

    v1.c = v1.c.at[-1].set(waveSpeed(v1.A[-1], ini.VCS[l].gamma[-1]))
    v2.c = v2.c.at[-1].set(waveSpeed(v2.A[-1], ini.VCS[m].gamma[-1]))
    v3.c = v3.c.at[0].set(waveSpeed(v3.A[0], ini.VCS[n].gamma[0]))

    #jax.debug.breakpoint()
    return v1, v2, v3
