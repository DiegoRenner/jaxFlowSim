from functools import partial
import jax.numpy as jnp
from jax import lax, vmap, jit
from src.anastomosis import solveAnastomosis
from src.conjunctions import solveConjunction
from src.bifurcations import solveBifurcation
from src.boundary_conditions import setInletBC, setOutletBC
from src.utils import pressureSA, waveSpeedSA
#from jax.sharding import Mesh, PartitionSpec
#from jax.experimental import mesh_utils
#from jax.experimental.shard_map import shard_map


#devices = mesh_utils.create_device_mesh((20))
#mesh = Mesh(devices, axis_names=('i'))



#@partial(jax.jit, static_argnums=(0))
def calculateDeltaT(Ccfl, u, c, dx):
    Smax = vmap(lambda a, b: jnp.abs(a+b))(u,c)
    vessel_dt = vmap(lambda a, b: a*Ccfl/b)(dx,Smax)
    dt = jnp.min(vessel_dt)
    return dt



#@jit
def solveModel(N, B, starts, ends, starts_rep, ends_rep, indices1, indices2, t, dt, sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, edges, input_data, rho):

    inlet = sim_dat_const_aux[0,1] 
    u0 = sim_dat[0,B]
    u1 = sim_dat[0,B+1]
    A0 = sim_dat[2,B]
    c0 = sim_dat[3,B]
    c1 = sim_dat[3,B+1]
    cardiac_T = sim_dat_const_aux[0,0]
    dx = sim_dat_const[-1,B]
    A00 = sim_dat_const[0,B]
    beta0 = sim_dat_const[1,B]
    Pext = sim_dat_const[4,B]
    #debug.print("{x}", x = (inlet, u0, u1, A0, c0, c1,
    #                            cardiac_T, dx, A00, beta0,
    #                            Pext))
    #debug.print("{x}", x = setInletBC(inlet, u0, u1, A0, 
    #                    c0, c1, t, dt, 
    #                    input_data, cardiac_T, 1/dx, A00, 
    #                    beta0, Pext))
    sim_dat = sim_dat.at[1:3,0:B+1].set(jnp.array(setInletBC(inlet, u0, u1, A0, 
                        c0, c1, t, dt, 
                        input_data, cardiac_T, 1/dx, A00, 
                        beta0, Pext))[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:])
    #inlet = sim_dat_const_aux[1,1] 
    #u0 = sim_dat[0,B+M+2*B]
    #u1 = sim_dat[0,B+M+2*B+1]
    #A0 = sim_dat[2,B+M+2*B]
    #c0 = sim_dat[3,B+M+2*B]
    #c1 = sim_dat[3,B+M+2*B+1]
    #cardiac_T = sim_dat_const_aux[1,0]
    #dx = sim_dat_const[-1,B+M+2*B]
    #A00 = sim_dat_const[0,B+M+2*B]
    #beta0 = sim_dat_const[1,B+M+2*B]
    #Pext = sim_dat_const[4,B+M+2*B]

    # uncomment the following to make aspirator test work
    #M = ini.ENDS[0]-ini.STARTS[0]
    #sim_dat = sim_dat.at[1:3,ini.STARTS[1]-B:ini.STARTS[1]+1].set(sim_dat[1:3,ini.STARTS[1]][:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:])

    #_Q, _A = setInletBC(inlet, u0, u1, A0, 
    #                    c0, c1, t, dt, 
    #                    input_data, cardiac_T, 1/dx, A00, 
    #                    beta0, Pext)
    #sim_dat = sim_dat.at[1,0].set(_Q)
    #sim_dat = sim_dat.at[2,0].set(_A)



    #def body_fun1(j, dat):
    #    (dt, sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux) = dat
    #    i = edges[j,0]-1
    #    start = i*M + 2 + 4*i
    #    sim_dat = lax.dynamic_update_slice(
    #        sim_dat,
    #        muscl(N, M, dt, 
    #              lax.dynamic_slice(sim_dat, (1,start), (1,M)).flatten(),
    #              lax.dynamic_slice(sim_dat, (2,start), (1,M)).flatten(), 
    #              lax.dynamic_slice(sim_dat_const, (0,start), (1,M)).flatten(), 
    #              lax.dynamic_slice(sim_dat_const, (1,start), (1,M)).flatten(), 
    #              lax.dynamic_slice(sim_dat_const, (2,start), (1,M)).flatten(), 
    #              lax.dynamic_slice(sim_dat_const, (3,start), (1,M)).flatten(),
    #              lax.dynamic_slice(sim_dat_const, (-1,start), (1,M)).flatten(),
    #              lax.dynamic_slice(sim_dat_const, (4,start), (1,M)).flatten(),
    #              lax.dynamic_slice(sim_dat_const, (5,start), (1,M)).flatten()),
    #        (0,start))
    #    
    #    #debug.print("{x}", x = sim_dat)
    #    

    #    return (dt, sim_dat, sim_dat_aux, 
    #            sim_dat_const, sim_dat_const_aux)

    #(_, sim_dat, sim_dat_aux, _, _)  = lax.fori_loop(0, N, body_fun1, 
    #                                               (dt, sim_dat, sim_dat_aux, 
    #                                                sim_dat_const, sim_dat_const_aux))
                                                
    #debug.print("{x}", x = sim_dat_const[2,:])

    sim_dat = sim_dat.at[:,B:-B].set(muscl(dt, 
                  sim_dat[1,B:-B],
                  sim_dat[2,B:-B], 
                  sim_dat_const[0,B:-B], 
                  sim_dat_const[1,B:-B], 
                  sim_dat_const[2,B:-B], 
                  sim_dat_const[3,B:-B],
                  sim_dat_const[-1,B:-B],
                  sim_dat_const[4,B:-B],
                  sim_dat_const[5,B:-B],
                  indices1, indices2))
    
    #debug.print("{x}", x = sim_dat[0:2,:])

    def body_fun2(j, dat):
        (sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, edges, rho, starts, ends) = dat
        i = edges[j,0]-1
        end = ends[i]
        
        def setOutletBC_wrapper(sim_dat, sim_dat_aux):
            u1 = sim_dat[0,end-1]
            u2 = sim_dat[0,end-2]
            Q1 = sim_dat[1,end-1]
            A1 = sim_dat[2,end-1]
            c1 = sim_dat[3,end-1]
            c2 = sim_dat[3,end-2]
            P1 = sim_dat[4,end-1]
            P2 = sim_dat[4,end-2]
            P3 = sim_dat[4,end-3]
            Pc = sim_dat_aux[i,2]
            W1M0 = sim_dat_aux[i,0]
            W2M0 = sim_dat_aux[i,1]
            #debug.print("{x}", x = (u1, u2, Q1, A1, c1, c2, P1, P2, P3, Pc, W1M0, W2M0))
            u, Q, A, c, P1, Pc = setOutletBC(dt,
                                             u1, u2, Q1, A1, c1, c2, 
                                             P1, P2, P3, Pc, W1M0, W2M0,
                                             sim_dat_const[0,end-1],
                                             sim_dat_const[1,end-1],
                                             sim_dat_const[2,end-1],
                                             sim_dat_const[-1, end-1],
                                             sim_dat_const[4, end-1],
                                             sim_dat_const_aux[i, 2], 
                                             sim_dat_const[6, end-1],
                                             sim_dat_const[7, end-1],
                                             sim_dat_const[8, end-1],
                                             sim_dat_const[9, end-1])
            #debug.print("{x}", x = (u,Q,A,c,P1))
            temp = jnp.array((u,Q,A,c,P1))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,end-1))
            sim_dat_aux = sim_dat_aux.at[i,2].set(Pc)
            return sim_dat, sim_dat_aux

        (sim_dat, 
         sim_dat_aux) = lax.cond(sim_dat_const_aux[i,2] != 0,
                                    lambda x, y: setOutletBC_wrapper(x,y), 
                                    lambda x, y: (x,y), sim_dat, sim_dat_aux)



        def solveBifurcation_wrapper(sim_dat):
            d1_i = edges[j,4]
            d2_i = edges[j,5]
            #d1_i_start = d1_i*M + B + 2*B*d1_i
            #d2_i_start = d2_i*M + B + 2*B*d2_i
            d1_i_start = starts[d1_i] 
            d2_i_start = starts[d2_i] 
            u1 = sim_dat[0,end-1]
            u2 = sim_dat[0,d1_i_start]
            u3 = sim_dat[0,d2_i_start]
            A1 = sim_dat[2,end-1]
            A2 = sim_dat[2,d1_i_start]
            A3 = sim_dat[2,d2_i_start]
            (u1, u2, u3, 
             Q1, Q2, Q3, 
             A1, A2, A3, 
             c1, c2, c3, 
             P1, P2, P3) = solveBifurcation(u1, u2, u3, 
                                            A1, A2, A3,
                                            sim_dat_const[0,end-1],
                                            sim_dat_const[0,d1_i_start],
                                            sim_dat_const[0,d2_i_start],
                                            sim_dat_const[1,end-1],
                                            sim_dat_const[1,d1_i_start],
                                            sim_dat_const[1,d2_i_start],
                                            sim_dat_const[2,end-1],
                                            sim_dat_const[2,d1_i_start],
                                            sim_dat_const[2,d2_i_start],
                                            sim_dat_const[4, end-1],
                                            sim_dat_const[4, d1_i_start],
                                            sim_dat_const[4, d2_i_start],
                                            )
            temp1 = jnp.array((u1, Q1, A1, c1, P1))
            temp2 = jnp.array((u2, Q2, A2, c2, P2))
            temp3 = jnp.array((u3, Q3, A3, c3, P3))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp1[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,end-1))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp2[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,d1_i_start-B))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp3[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,d2_i_start-B))
            return sim_dat

        sim_dat = lax.cond((sim_dat_const_aux[i,2] == 0) * (edges[j,3] == 2),
                                    lambda x: solveBifurcation_wrapper(x), 
                                    lambda x: x, sim_dat)

        #elif :
        def solveConjunction_wrapper(sim_dat, rho):
            d_i = edges[j,7]
            d_i_start = starts[d_i]
            u1 = sim_dat[0,end-1]
            u2 = sim_dat[0,d_i_start]
            A1 = sim_dat[2,end-1]
            A2 = sim_dat[2,d_i_start]
            (u1, u2, Q1, Q2, 
             A1, A2, c1, c2, P1, P2) = solveConjunction(u1, u2, 
                                                        A1, A2,
                                                        sim_dat_const[0,end-1],
                                                        sim_dat_const[0,d_i_start],
                                                        sim_dat_const[1,end-1],
                                                        sim_dat_const[1,d_i_start],
                                                        sim_dat_const[2,end-1],
                                                        sim_dat_const[2,d_i_start],
                                                        sim_dat_const[4, end-1],
                                                        sim_dat_const[4, d_i_start],
                                                        rho)
            temp1 = jnp.array((u1, Q1, A1, c1, P1))
            temp2 = jnp.array((u2, Q2, A2, c2, P2))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp1[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,end-1))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp2[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,d_i_start-B))
            return sim_dat

        sim_dat = lax.cond((sim_dat_const_aux[i,2] == 0) * 
                               (edges[j,3] != 2) *
                               (edges[j,6] == 1),
                                lambda x, y: solveConjunction_wrapper(x, y), 
                                lambda x, y: x, sim_dat, rho)

        #elif edges[j,6] == 2:                                           
        def solveAnastomosis_wrapper(sim_dat):
            p1_i = edges[j,7]
            p2_i = edges[j,8]
            d = edges[j,9]
            p1_i_end = ends[p1_i]
            d_start = starts[d]
            u1 = sim_dat[0,end-1]
            u2 = sim_dat[0,p1_i_end-1]
            u3 = sim_dat[0,d_start]
            Q1 = sim_dat[1,end-1]
            Q2 = sim_dat[1,p1_i_end-1]
            Q3 = sim_dat[1,d_start]
            A1 = sim_dat[2,end-1]
            A2 = sim_dat[2,p1_i_end-1]
            A3 = sim_dat[2,d_start]
            c1 = sim_dat[3,end-1]
            c2 = sim_dat[3,p1_i_end-1]
            c3 = sim_dat[3,d_start]
            P1 = sim_dat[4,end-1]
            P2 = sim_dat[4,p1_i_end-1]
            P3 = sim_dat[4,d_start]
            #debug.print("0")
            #debug.print("{x}", x = (u1, u2, u3, Q1, Q2, Q3, A1, A2, A3, c1, c2, c3, P1, P2, P3))
            u1, u2, u3, Q1, Q2, Q3, A1, A2, A3, c1, c2, c3, P1, P2, P3 = lax.cond(
                jnp.maximum(p1_i, p2_i) == i, 
                lambda: solveAnastomosis(u1, u2, u3, 
                                         A1, A2, A3,
                                         sim_dat_const[0,end-1],
                                         sim_dat_const[0,p1_i_end-1],
                                         sim_dat_const[0,d_start],
                                         sim_dat_const[1,end-1],
                                         sim_dat_const[1,p1_i_end-1],
                                         sim_dat_const[1,d_start],
                                         sim_dat_const[2,end-1],
                                         sim_dat_const[2,p1_i_end-1],
                                         sim_dat_const[2,d_start],
                                         sim_dat_const[4,end-1],
                                         sim_dat_const[4,p1_i_end-1],
                                         sim_dat_const[4,d_start],
                                        ), 
                lambda: (u1, u2, u3, Q1, Q2, Q3, A1, A2, A3, c1, c2, c3, P1, P2, P3))
            #debug.print("1")
            #debug.print("{x}", x = (u1, u2, u3, Q1, Q2, Q3, A1, A2, A3, c1, c2, c3, P1, P2, P3))
            temp1 = jnp.array((u1, Q1, A1, c1, P1))
            temp2 = jnp.array((u2, Q2, A2, c2, P2))
            temp3 = jnp.array((u3, Q3, A3, c3, P3))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp1[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,end-1))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp2[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,p1_i_end-1))
            sim_dat = lax.dynamic_update_slice( 
                sim_dat, 
                temp3[:,jnp.newaxis]*jnp.ones(B+1)[jnp.newaxis,:],
                (0,d_start-B))
            return sim_dat
        
        sim_dat = lax.cond((sim_dat_const_aux[i,2] == 0) * 
                               (edges[j,3] != 2) *
                               (edges[j,6] == 2),
                                lambda x: solveAnastomosis_wrapper(x), 
                                lambda x: x, sim_dat)


        return (sim_dat, sim_dat_aux, 
                sim_dat_const, sim_dat_const_aux, 
                edges, rho, starts, ends)
    #for j in np.arange(0,,1):
    
    #def cond_fun(dat):
    #    _, _, j = dat
    #    return j < ini.EDGES.edges.shape[0]


    #(sim_dat, sim_dat_aux), _ = lax.scan(body_fun, (sim_dat, sim_dat_aux), jnp.arange(ini.NUM_VESSELS))
    (sim_dat, sim_dat_aux, _, _, _, _, _, _)  = lax.fori_loop(0, N, body_fun2, 
                                                   (sim_dat, sim_dat_aux, 
                                                    sim_dat_const, sim_dat_const_aux, 
                                                    edges, rho, starts, ends))
    #debug.print("{x}", x = sim_dat)
    #debug.print("{x}", x = sim_dat[0:2,:])

    
    return sim_dat, sim_dat_aux


#@jit
#@partial(shard_map, mesh=mesh, in_specs=P('i', 'j'),
#         out_specs=P('i'))
#@partial(jit, static_argnums=(0, 1))
def muscl(dt, 
          Q, A, 
          A0, beta,  gamma, wallE,
          dx, Pext,viscT,
          indices1, indices2):
    #debug.print("{x}", x = A)
    #debug.print("{x}", x = (M, dt, Q, A, 
    #                            A0, beta, gamma, wallE, 
    #                            dx, Pext, viscT))
    #s_A0 = block_until_ready(shard_map(lambda a: jnp.sqrt(a), mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(A0))
    #debug.print("A = {x}", x = A)

    K = len(Q) + 2


    s_A0 = vmap(lambda a: jnp.sqrt(a))(A0)
    #s_A0 = jnp.sqrt(A0)
    s_inv_A0 = vmap(lambda a: 1/jnp.sqrt(a))(A0)
    #s_inv_A0 = 1/jnp.sqrt(A0)
    halfDx = 0.5*dx
    invDx = 1/dx
    gamma_ghost = jnp.zeros(K)
    gamma_ghost = gamma_ghost.at[1:-1].set(gamma)
    gamma_ghost = gamma_ghost.at[0].set(gamma[0])
    gamma_ghost = gamma_ghost.at[-1].set(gamma[-1])
    vA = jnp.empty(K)
    vQ = jnp.empty(K)
    vA = vA.at[0].set(A[0])
    vA = vA.at[-1].set(A[-1])

    vQ = vQ.at[0].set(Q[0])
    vQ = vQ.at[-1].set(Q[-1])
    vA = vA.at[1:-1].set(A)
    vQ = vQ.at[1:-1].set(Q)
    #vA = jnp.concatenate((jnp.array([U00A]),A,jnp.array([UM1A])))
    #vQ = jnp.concatenate((jnp.array([U00Q]),Q,jnp.array([UM1Q])))

    invDx_temp = jnp.concatenate((invDx, jnp.array([invDx[-1]])))
    limiterA = computeLimiter(vA, invDx_temp)
    limiterQ = computeLimiter(vQ, invDx_temp)
    halfDx_temp = jnp.concatenate((jnp.array([halfDx[0]]), halfDx, jnp.array([halfDx[-1]])))
    slopeA_halfDx = vmap(lambda a, b: a * b)(limiterA, halfDx_temp)
    slopeQ_halfDx = vmap(lambda a, b: a * b)(limiterQ, halfDx_temp)
    #debug.print("slopeQ_halfDx = {x}", x = slopeQ_halfDx)
    #debug.print("slopeA_halfDx = {x}", x = slopeA_halfDx)

    #slopeA_halfDx = slopesA * ini.VCS[i].halfDx
    #slopeQ_halfDx = slopesQ * ini.VCS[i].halfDx
    
    Al = vmap(lambda a, b: a+b)(vA, slopeA_halfDx)
    Ar = vmap(lambda a, b: a-b)(vA, slopeA_halfDx)
    Ql = vmap(lambda a, b: a+b)(vQ, slopeQ_halfDx)
    Qr = vmap(lambda a, b: a-b)(vQ, slopeQ_halfDx)
    #Al = shard_map(lambda a, b: a+b, mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(vA, slopeA_halfDx)
    #Ar = shard_map(lambda a, b: a-b, mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(vA, slopeA_halfDx)
    #Ql = shard_map(lambda a, b: a+b, mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(vQ, slopeQ_halfDx)
    #Qr = shard_map(lambda a, b: a-b, mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(vQ, slopeQ_halfDx)
    #Al = vA + slopeA_halfDx
    #Ar = vA - slopeA_halfDx
    #Ql = vQ + slopeQ_halfDx
    #Qr = vQ - slopeQ_halfDx
    #debug.print("Qr = {x}", x = Qr)
    #debug.print("Ql = {x}", x = Ql)
    #debug.print("Ar = {x}", x = Ar)
    #debug.print("Al = {x}", x = Al)

    Fl = jnp.array(vmap(computeFlux_par)(gamma_ghost, Al, Ql))
    Fr = jnp.array(vmap(computeFlux_par)(gamma_ghost, Ar, Qr))
    #Fl = jnp.array(computeFlux(gamma_ghost, Al, Ql))
    #Fr = jnp.array(computeFlux(gamma_ghost, Ar, Qr))
    #debug.print("Fr = {x}", x = Fr)
    #debug.print("Fl = {x}", x = Fl)

    dxDt = dx / dt
    
    invDxDt = dt / dx

    flux = jnp.empty((2,K-1))
    dxDt_temp = jnp.empty(K-1)
    dxDt_temp = dxDt_temp.at[0:-1].set(dxDt)
    dxDt_temp = dxDt_temp.at[-1].set(dxDt[-1])
    flux = flux.at[0,:].set(vmap(lambda a, b, c, d, e: 0.5*(a+b - e*(c-d)))(Fr[0, 1:], Fl[0, 0:-1], Ar[1:], Al[0:-1], dxDt_temp))
    flux = flux.at[1,:].set(vmap(lambda a, b, c, d, e: 0.5*(a+b - e*(c-d)))(Fr[1, 1:], Fl[1, 0:-1], Qr[1:], Ql[0:-1], dxDt_temp))
    #flux = flux.at[0,:].set(0.5 * (Fr[0, 1:] + Fl[0, 0:-1] - dxDt_temp * (Ar[1:] - Al[0:-1])))
    #flux = flux.at[1,:].set(0.5 * (Fr[1, 1:] + Fl[1, 0:-1] - dxDt_temp * (Qr[1:] - Ql[0:-1])))
    #flux = jnp.stack((0.5 * (Fr[0, 1:M+2] + Fl[0, 0:M+1] - dxDt * (Ar[1:M+2] - Al[0:M+1])), 
    #                  0.5 * (Fr[1, 1:M+2] + Fl[1, 0:M+1] - dxDt * (Qr[1:M+2] - Ql[0:M+1]))), dtype=jnp.float64)
    #debug.print("flux = {x}", x = flux)

    uStar = jnp.empty((2,K))
    #invDxDt_temp = jnp.empty(M*N + 20*N - 18)
    #invDxDt_temp = invDxDt_temp.at[1:-1].set(invDxDt)
    #invDxDt_temp = invDxDt_temp.at[-1].set(invDxDt[0])
    #invDxDt_temp = invDxDt_temp.at[-1].set(invDxDt[-1])
    uStar = uStar.at[0,1:-1].set(vmap(lambda a, b, c, d: a+d*(b-c))(vA[1:-1],
                                                             flux[0,0:-1],
                                                             flux[0,1:],
                                                             invDxDt))
    uStar = uStar.at[1,1:-1].set(vmap(lambda a, b, c, d: a+d*(b-c))(vQ[1:-1],
                                                             flux[1,0:-1],
                                                             flux[1,1:],
                                                             invDxDt))
    #uStar = uStar.at[0,1:M+1].set(vmap(lambda a, b: a-invDxDt*b)(vA[1:-1],
    #                                                         jnp.diff(flux[0,1:])))
    #uStar = uStar.at[1,1:M+1].set(vmap(lambda a, b: a-invDxDt*b)(vQ[1:-1],
    #                                                         jnp.diff(flux[1,1:])))
    #uStar = uStar.at[0,1:-1].set(vA[1:-1] + invDxDt*(flux[0,0:-1] - flux[0,1:]))
    #uStar = uStar.at[1,1:-1].set(vQ[1:-1] + invDxDt*(flux[1,0:-1] - flux[1,1:]))
    #uStar1 = vA[1:M+1] - invDxDt * jnp.diff(flux[0,0:M+1])
    #uStar2 = vQ[1:M+1] - invDxDt * jnp.diff(flux[1,0:M+1])
    #uStar = jnp.stack((jnp.concatenate((jnp.array([uStar1[0]]),uStar1,jnp.array([uStar1[-1]]))), 
    #                   jnp.concatenate((jnp.array([uStar2[0]]),uStar2,jnp.array([uStar2[-1]])))))


    uStar1 = jnp.zeros((2, K+2))
    uStar1 = uStar1.at[:,0:-2].set(uStar)
    uStar2 = jnp.zeros((2, K+2))
    uStar2 = uStar1.at[:,1:-1].set(uStar)
    uStar3 = jnp.zeros((2, K+2))
    uStar3 = uStar1.at[:,2:].set(uStar)
    #uStar2 = jnp.where(indices%(M+2*B)==1, uStar1, uStar2) 
    uStar2 = jnp.where(indices1, uStar1, uStar2) 
    #uStar2 = jnp.where(indices%(M+2*B)==M+2, uStar3, uStar2) 
    uStar2 = jnp.where(indices2, uStar3, uStar2) 
    uStar = uStar2[:,1:-1]
    #uStar = uStar.at[0,0].set(uStar[0,1])
    #uStar = uStar.at[1,0].set(uStar[1,1])
    #uStar = uStar.at[0,-1].set(uStar[0,-2])
    #uStar = uStar.at[1,-1].set(uStar[1,-2])
    #debug.print("uStar = {x}", x = uStar)

    limiterA = computeLimiterIdx(uStar, 0, invDx_temp)
    limiterQ = computeLimiterIdx(uStar, 1, invDx_temp)
    slopesA = vmap(lambda a, b: a * b)(limiterA, halfDx_temp)
    slopesQ = vmap(lambda a, b: a * b)(limiterQ, halfDx_temp)
    #debug.print("slopesQ = {x}", x = slopesQ)
    #debug.print("slopesA = {x}", x = slopesA)

    #Al = uStar[0,0:M+2] + slopesA
    #Ar = uStar[0,0:M+2] - slopesA
    #Ql = uStar[1,0:M+2] + slopesQ
    #Qr = uStar[1,0:M+2] - slopesQ
    Al = vmap(lambda a, b: a+b)(uStar[0,:], slopesA)
    Ar = vmap(lambda a, b: a-b)(uStar[0,:], slopesA)
    Ql = vmap(lambda a, b: a+b)(uStar[1,:], slopesQ)
    Qr = vmap(lambda a, b: a-b)(uStar[1,:], slopesQ)
    #debug.print("Qr = {x}", x = Qr)
    #debug.print("Ql = {x}", x = Ql)
    #debug.print("Ar = {x}", x = Ar)
    #debug.print("Al = {x}", x = Al)
    
    Fl = jnp.array(vmap(computeFlux_par)(gamma_ghost, Al, Ql))
    Fr = jnp.array(vmap(computeFlux_par)(gamma_ghost, Ar, Qr))
    #debug.print("{x}", x = Fr)
    #debug.print("{x}", x = Fl)
    #debug.print("{x}", x = uStar)
    #debug.print("{x}", x = Ar)
    #debug.print("{x}", x = Al)
    #debug.print("{x}", x = Qr)
    #debug.print("{x}", x = Ql)
    #debug.print("{x}", x = Fr)
    #debug.print("{x}", x = Fl)
    
    #debug.print("{x}", x = Fl)
    #Fl = jnp.array(computeFlux(gamma_ghost, Al, Ql))
    #Fr = jnp.array(computeFlux(gamma_ghost, Ar, Qr))
    #debug.print("Fr = {x}", x = Fr)
    #debug.print("Fl = {x}", x = Fl)
    #debug.print ("(ˊ̱˂˃ˋ̱ )")

    flux = jnp.empty((2,K-1))
    flux = flux.at[0,:].set(vmap(lambda a, b, c, d, e: 0.5*(a+b - e*(c-d)))(Fr[0, 1:], Fl[0, 0:-1], Ar[1:], Al[0:-1], dxDt_temp))
    flux = flux.at[1,:].set(vmap(lambda a, b, c, d, e: 0.5*(a+b - e*(c-d)))(Fr[1, 1:], Fl[1, 0:-1], Qr[1:], Ql[0:-1], dxDt_temp))
    #debug.print("{x}", x = flux)
    #flux = jnp.empty((2,M+2))
    #flux = flux.at[0,0:M+1].set(vmap(lambda a, b, c, d: 0.5*(a+b - dxDt[0]*(c-d)))(Fr[0, 1:M+2], Fl[0, 0:M+1], Ar[1:M+2], Al[0:M+1]))
    #flux = flux.at[1,0:M+1].set(vmap(lambda a, b, c, d: 0.5*(a+b - dxDt[0]*(c-d)))(Fr[1, 1:M+2], Fl[1, 0:M+1], Qr[1:M+2], Ql[0:M+1]))
    #flux = flux.at[0,:].set(0.5 * (Fr[0, 1:] + Fl[0, 0:-1] - dxDt_temp * (Ar[1:] - Al[0:-1])))
    #flux = flux.at[1,:].set(0.5 * (Fr[1, 1:] + Fl[1, 0:-1] - dxDt_temp * (Qr[1:] - Ql[0:-1])))
    #flux = jnp.stack((0.5 * (Fr[0, 1:M+2] + Fl[0, 0:M+1] - dxDt * (Ar[1:M+2] - Al[0:M+1])), 
    #                 0.5 * (Fr[1, 1:M+2] + Fl[1, 0:M+1] - dxDt * (Qr[1:M+2] - Ql[0:M+1]))))


    #A = A.at[0:M].set(0.5*(A[0:M] + uStar[0,1:M+1] + invDxDt * (flux[0, 0:M] - flux[0, 1:M+1])))
    #debug.print("{x}", x = Q)
    #debug.print("{x}", x = uStar)
    #debug.print("flux = {x}", x = flux)
    A = vmap(lambda a, b, c, d, e: 0.5*(a+b+e*(c-d)))(A[:],
                                                             uStar[0,1:-1],
                                                             flux[0,0:-1],
                                                             flux[0,1:],
                                                             invDxDt)
    Q = vmap(lambda a, b, c, d, e: 0.5*(a+b+e*(c-d)))(Q[:],
                                                             uStar[1,1:-1],
                                                             flux[1,0:-1],
                                                             flux[1,1:],
                                                             invDxDt)
    #A = 0.5*(A + uStar[0,1:-1] + invDxDt*(flux[0,0:-1]-flux[0,1:]))
    #Q = 0.5*(Q + uStar[1,1:-1] + invDxDt*(flux[1,0:-1]-flux[1,1:]))
    #debug.print("{x}", x = A)
    #debug.print("{x}", x = Q)
    #uStar = uStar.at[1,1:M+1].set(vmap(lambda a, b, c: a+invDxDt*(b-c))(vQ[1:M+1],
    #                                                         flux[1,0:M],
    #                                                         flux[1,1:M+1]))
    #A = A.at[0:M].set(0.5*(A[0:M] + uStar[0,1:M+1] - invDxDt * jnp.diff(flux[0,0:M+1])))
    #Q = Q.at[0:M].set(0.5*(Q[0:M] + uStar[1,1:M+1] - invDxDt * jnp.diff(flux[1,0:M+1])))

    s_A = vmap(lambda a: jnp.sqrt(a))(A)
    #Si = - ini.VCS[i].viscT * Q / A - ini.VCS[i].wallE * (s_A - ini.VCS[i].s_A0) * A
    #debug.print("{x}", x = Q)
    Q = vmap(lambda a, b, c, d, e: a - dt*(viscT[0]*a/b + c*(d - e)*b))(Q, A, wallE, s_A, s_A0)
    #debug.print("Q = {x}", x = Q)
    #debug.print("A = {x}", x = A)
    #debug.print("{x}", x = wallE)
    #debug.print("{x}", x = s_A)
    #debug.print("{x}", x = s_A0)
    #Q = Q - dt * (viscT * Q / A + wallE * (s_A - s_A0) * A)

    P = vmap(lambda a, b, c, d: pressureSA(a*b, c, d))(s_A, s_inv_A0, beta, Pext)
    #P = pressureSA(s_A * s_inv_A0, beta, Pext)
    c = vmap(waveSpeedSA)(s_A, gamma)
    #c = waveSpeedSA(s_A, gamma)

    #if (v.wallVa[0] != 0.0).astype(bool):
    #mask = v.wallVa != 0.0
    #    Td = 1.0 / dt + v.wallVb
    #    Tlu = -v.wallVa    return @SArray [f1, f2, f3, f4, f5, f6]
    #    d = (1.0 / dt - v.wallVb) * v.Q[mask]
    #    d = d.at[0].set(v.wallVa[1:-1] * v.Q[mask[:-1]])
    #    d = d.at[-1].set(v.wallVa[1:-1] * v.Q[mask[1:]])
    #    d = d.at[ops.index[1:-1]].set(v.wallVa[1:-1] * v.Q[mask[:-2]] + v.wallVa[:-2] * v.Q[mask[2:]])

    #    v.Q = v.Q.at[mask].set(scipy.linalg.solve_banded((1, 1), jnp.array([Tlu[:-1], Td, Tlu[1:]]), d))

    u = vmap(lambda a, b: a/b)(Q, A)
    #u =  Q/A
    #debug.print("{x}", x = A)
    #debug.print("u = {x}", x = u)
    #debug.print("{x}", x = (M, dt, Q, A, 
    #                            A0, beta, gamma, wallE, 
    #                            dx, Pext, viscT))
    #debug.print("{x}", x = Q)
    ##u = shard_map(lambda a, b: a/b, mesh, in_specs=PartitionSpec('i'), out_specs=PartitionSpec('i'))(Q, A)
    ##debug.print("{x}", x=u)
    return jnp.stack((u,Q,A,c,P))


def computeFlux(gamma_ghost, A, Q):
    #Flux = jnp.empty((2,A.size), dtype=jnp.float64)
    #Flux = Flux.at[0,:].set(Q)
    #Flux = Flux.at[1,:].set(Q * Q / A + gamma_ghost * A * jnp.sqrt(A))

    #return Flux
    return Q, Q * Q / A + gamma_ghost * A * jnp.sqrt(A)
    #return jnp.stack((Q, Q * Q / A + gamma_ghost * A * jnp.sqrt(A)))

def computeFlux_par(gamma_ghost, A, Q):
    #Flux = jnp.empty((2,A.size), dtype=jnp.float64)
    #Flux = Flux.at[0,:].set(Q)
    #Flux = Flux.at[1,:].set(Q * Q / A + gamma_ghost * A * jnp.sqrt(A))

    #return Flux
    #debug.print("{x}", x = 0)
    #debug.print("{x}", x = gamma_ghost.transpose())
    #debug.print("{x}", x = 1)
    #debug.print("{x}", x = A.transpose())
    #jax.debug.print("{x}", x = 2)
    #debug.print("{x}", x = Q.transpose())
    #debug.print("{x}", x = 3)
    #debug.print("{x}", x = (Q * Q / A + gamma_ghost * A * jnp.sqrt(A)).transpose())
    return Q, Q * Q / A + gamma_ghost * A * jnp.sqrt(A)


def maxMod(a, b):
    return jnp.where(a > b, a, b)

def minMod(a, b):
    return jnp.where((a <= 0.0) | (b <= 0.0), 0.0, jnp.where(a < b, a, b))

def superBee(dU):
    #s1 = minMod(dU[0, :], 2 * dU[1, :])
    #s2 = minMod(2 * dU[0, :], dU[1, :])

    #return maxMod(s1, s2)
    return maxMod(minMod(dU[0, :], 2 * dU[1, :]), minMod(2 * dU[0, :], dU[1, :]))

def computeLimiter(U, invDx):
    #dU = jnp.empty((2, U.size), dtype=jnp.float64)
    #dU = dU.at[0, 1:].set((U[1:] - U[:-1]) * invDx)
    #dU = dU.at[1, 0:-1].set(dU[0, 1:])
    dU = vmap(lambda a, b: a*b)(jnp.diff(U), invDx)
    #test = [[0,(U[1:] - U[:-1]) * invDx], 
    #       [0, (U[1:-1] - U[:-2]) * invDx, 0]]
    #debug.breakpoint()
    #return superBee(dU)
    return superBee(jnp.stack((jnp.concatenate((jnp.array([0.0]),dU)),
                               jnp.concatenate((dU,jnp.array([0.0]))))))
                                                                   


def computeLimiterIdx(U, idx, invDx):
    #U = U[idx, :]
    dU = vmap(lambda a, b: a*b)(jnp.diff(U[idx, :]), invDx)
    #dU = jnp.empty((2, U.size), dtype=jnp.float64)
    #dU = dU.at[0, 1:].set((U[1:] - U[:-1]) * invDx)
    #dU = dU.at[1, 0:-1].set(dU[0, 1:])
    
    #return superBee(dU)
    return superBee(jnp.stack((jnp.concatenate((jnp.array([0.0]),dU)),
                               jnp.concatenate((dU,jnp.array([0.0]))))))