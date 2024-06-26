from jax import lax, debug
import jax.numpy as jnp


def calcNorms(N, P_t, P_l):
    norms = jnp.zeros(N)
    def body_fun(i,norms):
        err = P_l[:, i*5 + 2] - P_t[:, i*5 + 2]
        norms = norms.at[i].set(jnp.sqrt(jnp.sum(err**2)))
        return norms
    norms = lax.fori_loop(0,N,body_fun, norms)
    return norms

def computeConvError(N, P_t, P_l):
    current_norms = calcNorms(N, P_t, P_l)
    maxnorm = jnp.max(current_norms)
    return maxnorm

def printConvError(err):
    err /= 133.332
    debug.print("error norm = {x} mmHg", x=err)

def checkConv(err, conv_toll):
    return err / 133.332 <= conv_toll
