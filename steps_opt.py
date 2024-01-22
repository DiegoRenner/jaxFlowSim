from src.model import configSimulation, simulationLoopUnsafe, simulationLoop
import jax
import sys
import time
import os
import shutil
from functools import partial
from jax import block_until_ready, jit
import matplotlib.pyplot as plt
import numpy as np

os.chdir(os.path.dirname(__file__))
jax.config.update("jax_enable_x64", True)

config_filename = ""
if len(sys.argv) == 1:
    # base cases
    #config_filename = "test/single-artery/single-artery.yml"
    #config_filename = "test/tapering/tapering.yml"
    #config_filename = "test/conjunction/conjunction.yml"
    #config_filename = "test/bifurcation/bifurcation.yml"
    #config_filename = "test/aspirator/aspirator.yml"

    # openBF-hub 
    config_filename = "test/adan56/adan56.yml"

    # vascularmodels.com
    #modelname = "0007_H_AO_H"
    #modelname = "0029_H_ABAO_H"
    #modelname = "0053_H_CERE_H"
    #input_filename = "test/" + modelname + "/" + modelname + ".yml"
else:
    config_filename = "test/" + sys.argv[1] + "/" + sys.argv[1] + ".yml"

verbose = True
(N, B, J, 
 sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
 timepoints, conv_toll, Ccfl, edges, input_data, 
            rho, total_time, nodes, 
            starts, ends,
            indices_1, indices_2,
            vessel_names, cardiac_T) = configSimulation(config_filename, verbose, False)


#jnp.set_printoptions(threshold=sys.maxsize)
filename = config_filename.split("/")[-1]
network_name = filename.split(".")[0]
r_folder = "results/steps_opt_" + network_name
# delete existing folder and results
if os.path.isdir(r_folder):
    shutil.rmtree(r_folder)
os.makedirs(r_folder, mode = 0o777)


vessel_names_0007 = ["ascending aorta", "right subclavian artery", "right common carotid artery", 
                "arch of aorta I", "brachiocephalic artery", 
                "arch of aorta II",
                "left common carotid artery", 
                "left subclavian artery",
                "descending aorta", 
                ]
vessel_names_0029 = [
                "aorta I",
                "left common iliac artery I",
                "left internal iliac artery",
                "left common iliac artery II",
                "right common iliac artery I",
                "celiac trunk II",
                "celiac branch",
                "aorta IV",
                "left renal artery",
                "aorta III",
                "superior mesentric artery",
                "celiac trunk I",
                "aorta II",
                "aorta V",
                "right renal artery",
                "right common iliac artery II",
                "right internal iliac artery",
                ]
vessel_names_0053 = [
                "right vertebral artery I", 
                "left vertebral artery II",
                "left posterior meningeal branch of vertebral artery",
                "basilar artery III",
                "left anterior inferior cerebellar artery",
                "basilar artery II",
                "right anterior inferior cerebellar artery",
                "basilar artery IV",
                "right superior cerebellar artery", 
                "basilar artery I",
                "left vertebral artery I",
                "right posterior cerebellar artery I",
                "left superior cerebellar artery",
                "left posterior cerebellar artery I",
                "right posterior central artery",
                "right vertebral artery II",
                "right posterior meningeal branch of vertebral artery",
                "right posterior cerebellar artery II",
                "right posterior comunicating artery",
                ]

#plt.rcParams.update({'font.size': 20})

#print(sim_dat)
if verbose:
    starting_time = time.time_ns()
sim_loop_old_jit = partial(jit, static_argnums=(0, 1, 2))(simulationLoop)
sim_dat, t, P  = block_until_ready(sim_loop_old_jit(N, B, J, 
                                      sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
                                      timepoints, conv_toll, Ccfl, edges, input_data, 
                                      rho, total_time, nodes, 
                                      starts, ends,
                                      indices_1, indices_2))

if verbose:
    ending_time_base = (time.time_ns() - starting_time) / 1.0e9
    print(f"elapsed time = {ending_time_base} seconds")
P0_temp = np.loadtxt("/home/diego/studies/uni/thesis_maths/openBF/test/" + network_name + "/" + network_name + "_results/" + vessel_names[0] + "_P.last")
t0 = P0_temp[:,0]%cardiac_T

counter = 0
t_new = np.zeros(len(timepoints))
P_new = np.zeros((len(timepoints), 5*N))
for i in range(len(t)-1):
    if t0[counter] >= t[i] and t0[counter] <= t[i+1]:
        P_new[counter,:] = (P[i,:] + P[i+1,:])/2
        counter += 1

t_new = t_new[:-1]
P_new = P_new[:-1,:]
residual_base = 0
for i,vessel_name in enumerate(vessel_names):
    index_vessel_name = vessel_names.index(vessel_name)
    P0_temp = np.loadtxt("/home/diego/studies/uni/thesis_maths/openBF/test/" + network_name + "/" + network_name + "_results/" + vessel_name + "_P.last")
    node = 2
    index_jl  = 1 + node
    index_jax  = 5*index_vessel_name + node

    P0 = P0_temp[:-1,index_jl]
    t0 = P0_temp[:-1,0]%cardiac_T
    P1 = P_new[:,index_jax]
    residual_base += np.sqrt(((P1-P0).dot(P1-P0)/P0.dot(P0)))

times = []
steps = range(50000,210000,10000)
residuals = []
for m in steps:
    if verbose:
        starting_time = time.time_ns()
    sim_loop_old_jit = partial(jit, static_argnums=(0,1,15))(simulationLoopUnsafe)
    sim_dat_out, P_t, t_t = block_until_ready(sim_loop_old_jit(N, B,
                                          sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
                                          Ccfl, edges, input_data, 
                                          rho, nodes, 
                                          starts, ends,
                                          indices_1, indices_2, upper=m))

    if verbose:
        ending_time = (time.time_ns() - starting_time) / 1.0e9
        times.append(ending_time)
        print(f"elapsed time = {ending_time} seconds")

    indices = [i+1 for i in range(len(t_t)-1) if t_t[i]>t_t[i+1]]
    P_cycle = P_t[indices[-2]:indices[-1],:]
    t_cycle = t_t[indices[-2]:indices[-1]]
    P0_temp = np.loadtxt("/home/diego/studies/uni/thesis_maths/openBF/test/" + network_name + "/" + network_name + "_results/" + vessel_names[0] + "_P.last")
    t0 = P0_temp[:,0]%cardiac_T

    counter = 0
    t_new = np.zeros(len(timepoints))
    P_new = np.zeros((len(timepoints), 5*N))
    for i in range(len(t_cycle)-1):
        if t0[counter] >= t_cycle[i] and t0[counter] <= t_cycle[i+1]:
            P_new[counter,:] = (P_cycle[i,:] + P_cycle[i+1,:])/2
            counter += 1

    t_new = t_new[:-1]
    P_new = P_new[:-1,:]

    residual = 0
    for i,vessel_name in enumerate(vessel_names):
        index_vessel_name = vessel_names.index(vessel_name)
        P0_temp = np.loadtxt("/home/diego/studies/uni/thesis_maths/openBF/test/" + network_name + "/" + network_name + "_results/" + vessel_name + "_P.last")
        node = 2
        index_jl  = 1 + node
        index_jax  = 5*index_vessel_name + node

        P0 = P0_temp[:-1,index_jl]
        t0 = P0_temp[:-1,0]%cardiac_T
        P1 = P_new[:,index_jax]
        residual += np.sqrt(((P1-P0).dot(P1-P0)/P0.dot(P0)))
    
    residuals.append(residual/N)
_, ax = plt.subplots()
ax.set_xlabel("# steps")
ax1 = ax.twinx()
ln1 = ax.plot(steps,times, "g-", label="static t[s]")
ln2 = ax.plot(steps,np.ones(len(steps))*ending_time_base, "r-", label="dynamic t[s]")
ln3 = ax1.plot(steps,residuals, "b-", label ="static residual")
ln4 = ax.plot(steps,np.ones(len(steps))*residual_base, "y-", label="dynamic residual")
ax.set_xlabel("# steps")
ax.set_ylabel("t[s]")
ax1.set_ylabel("residual")
lns = ln1+ln2+ln3+ln4
labels = [l.get_label() for l in lns]
plt.legend(lns, labels, loc ="center right")
plt.tight_layout()
plt.savefig(r_folder + "/steps_opt_" + network_name +".pdf")
plt.close()