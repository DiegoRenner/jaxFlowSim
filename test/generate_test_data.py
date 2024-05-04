import jax
import sys
sys.path.append('/home/diego/studies/uni/thesis_maths/jaxFlowSim')
from src.model import configSimulation, simulationLoop, simulationLoopUnsafe
import time
import os
from functools import partial
from jax import block_until_ready, jit
import numpy as np

os.chdir(os.path.dirname(__file__)+"/..")

test_data_path = "test/test_data"
if not os.path.exists(test_data_path):
    os.mkdir(test_data_path)

jax.config.update("jax_enable_x64", True)

modelnames = ["single-artery", 
                   "tapering",
                   "conjunction",
                   "bifurcation",
                   "aspirator",
                   "adan56",
                   "0007_H_AO_H",
                   "0029_H_ABAO_H",
                   "0053_H_CERE_H"]

for modelname in modelnames:
    config_filename = "test/" + modelname + "/" + modelname + ".yml"
    verbose = True
    (N, B, J, 
     sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
     timepoints, conv_tol, Ccfl, edges, input_data, 
                rho, nodes, 
                starts, ends,
                indices_1, indices_2,
                vessel_names, cardiac_T) = configSimulation(config_filename, verbose)#, junction_functions) = configSimulation(config_filename, verbose)

    if verbose:
        starting_time = time.time_ns()
    sim_loop_old_jit = partial(jit, static_argnums=(0, 1, 2))(simulationLoop)
    sim_dat, t, P  = block_until_ready(sim_loop_old_jit(N, B, J, 
                                          sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
                                          timepoints, conv_tol, Ccfl, edges, input_data, 
                                          rho, nodes, 
                                          starts, ends,
                                          indices_1, indices_2)) #, junction_functions))

    if verbose:
        ending_time = (time.time_ns() - starting_time) / 1.0e9
        print(f"elapsed time = {ending_time} seconds")

    np.savetxt("test/test_data/" + modelname + "_sim_dat.dat", sim_dat)
    np.savetxt("test/test_data/" + modelname + "_t.dat", t)
    np.savetxt("test/test_data/" + modelname + "_P.dat", P)

for modelname in modelnames:
    config_filename = "test/" + modelname + "/" + modelname + ".yml"
    verbose = True
    (N, B, J, 
     sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
     timepoints, conv_toll, Ccfl, edges, input_data, 
                rho, nodes, 
                starts, ends,
                indices_1, indices_2,
                vessel_names, cardiac_T) = configSimulation(config_filename, verbose)

    if verbose:
        starting_time = time.time_ns()

    sim_loop_old_jit = partial(jit, static_argnums=(0, 1, 15))(simulationLoopUnsafe)
    sim_dat, P_t, t_t = block_until_ready(sim_loop_old_jit(N, B,
                                          sim_dat, sim_dat_aux, sim_dat_const, sim_dat_const_aux, 
                                          Ccfl, edges, input_data, 
                                          rho, nodes, 
                                          starts, ends,
                                          indices_1, indices_2, upper=120000))

    if verbose:
        ending_time = (time.time_ns() - starting_time) / 1.0e9
        print(f"elapsed time = {ending_time} seconds")

    np.savetxt("test/test_data/" + modelname + "_sim_dat_unsafe.dat", sim_dat)
    np.savetxt("test/test_data/" + modelname + "_t_unsafe.dat", t)
    np.savetxt("test/test_data/" + modelname + "_P_unsafe.dat", P)