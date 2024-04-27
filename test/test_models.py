import unittest

class TestStringMethods(unittest.TestCase):

    def test_bifurcation(self):
        import jax
        import sys
        sys.path.append('/home/diego/studies/uni/thesis_maths/jaxFlowSim')
        print('Updated sys.path:', sys.path)
        from src.model import configSimulation, simulationLoop
        import time
        import os
        from functools import partial
        from jax import block_until_ready, jit
        import matplotlib.pyplot as plt
        import numpy as np

        #os.chdir(os.path.dirname(__file__))
        jax.config.update("jax_enable_x64", True)

        config_filename = "test/bifurcation/bifurcation.yml"

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

        P_base = np.loadtxt("test/test_data/bifurcation_P.dat")
        sim_dat_base = np.loadtxt("test/test_data/bifurcation_sim_dat.dat")
        t_base = np.loadtxt("test/test_data/bifurcation_t.dat")
                
        np.testing.assert_almost_equal(P, P_base)
        np.testing.assert_almost_equal(sim_dat,sim_dat_base)
        np.testing.assert_almost_equal(t, t_base)


if __name__ == '__main__':
    unittest.main()