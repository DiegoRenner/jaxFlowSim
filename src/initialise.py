import numpy as np
import jax.numpy as jnp
import yaml
import os.path
import shutil
from src.utils import waveSpeed, pressureSA
from src.components import Heart, Blood, Vessel, Vessel_const, Edges

VCS = None
CCFL = None
HEART = None
TOTAL_TIME = None
CONV_TOLL = None
EDGES = None
BLOOD = None
JUMP = None
MESH_SIZE_TOT = None
MESH_SIZES = None
NUM_VESSELS = None


def loadSimulationFiles(input_filename):
    data = loadYamlFile(input_filename)

    checkInputFile(data)

    return data


def loadYamlFile(filename):
    if not os.path.isfile(filename):
        raise ValueError(f"missing file {filename}")

    with open(filename, "r") as file:
        return yaml.safe_load(file)


def checkInputFile(data):
    checkSections(data)
    checkNetwork(data["network"])


def checkSections(data):
    keys = ["project name", "network", "blood", "solver"]
    for key in keys:
        if key not in data:
            raise ValueError(f"missing section {key} in YAML input file")

    checkSection(data, "blood", ["mu", "rho"])
    checkSection(data, "solver", ["Ccfl", "cycles", "convergence tolerance"])

    if "jump" not in data["solver"]:
        data["solver"]["jump"] = 100


def checkSection(data, section, keys):
    for key in keys:
        if key not in data[section]:
            raise ValueError(f"missing {key} in {section} section")


def checkNetwork(network):
    has_inlet = False
    inlets = set()
    has_outlet = False
    nodes = {}

    for i, vessel in enumerate(network, start=1):
        checkVessel(i, vessel)

        if "inlet" in vessel:
            has_inlet = True
            inlet_node = vessel["sn"]
            if inlet_node in inlets:
                raise ValueError(f"inlet {inlet_node} used multiple times")
            inlets.add(vessel["sn"])
        if "outlet" in vessel:
            has_outlet = True

        # check max number of vessels per node
        if vessel["sn"] not in nodes:
            nodes[vessel["sn"]] = 1
        else:
            nodes[vessel["sn"]] += 1
        if vessel["tn"] not in nodes:
            nodes[vessel["tn"]] = 1
        else:
            nodes[vessel["tn"]] += 1
        if nodes[vessel["sn"]] > 3:
            raise ValueError(f"too many vessels connected at node {vessel['sn']}")
        elif nodes[vessel["tn"]] > 3:
            raise ValueError(f"too many vessels connected at node {vessel['tn']}")

    # outlet nodes must be defined
    for i, vessel in enumerate(network, start=1):
        if nodes[vessel["tn"]] == 1:
            if "outlet" not in vessel:
                raise ValueError(f"outlet not defined for vessel {vessel['label']}, check connectivity")

    if not has_inlet:
        raise ValueError("missing inlet(s) definition")

    if not has_outlet:
        raise ValueError("missing outlet(s) definition")

def checkVessel(i, vessel):
    keys = ["label", "sn", "tn", "L", "E"]
    for key in keys:
        if key not in vessel:
            raise ValueError(f"vessel {i} is missing {key} value")

    if vessel["sn"] == vessel["tn"]:
        raise ValueError(f"vessel {i} has same sn and tn")

    if "R0" not in vessel:
        if "Rp" not in vessel and "Rd" not in vessel:
            raise ValueError(f"vessel {i} is missing lumen radius value(s)")
    else:
        if vessel["R0"] > 0.05:
            print(f"{vessel['label']} radius larger than 5cm!")

    if "inlet" in vessel:
        if "inlet file" not in vessel:
            raise ValueError(f"inlet vessel {i} is missing the inlet file path")
        elif not os.path.isfile(vessel["inlet file"]):
            file_path = vessel["inlet file"]
            raise ValueError(f"vessel {i} inlet file {file_path} not found")

        if "inlet number" not in vessel:
            raise ValueError(f"inlet vessel {i} is missing the inlet number")

    if "outlet" in vessel:
        outlet = vessel["outlet"]
        if outlet == "wk3":
            if "R1" not in vessel or "Cc" not in vessel:
                raise ValueError(f"outlet vessel {i} is missing three-element windkessel values")
        elif outlet == "wk2":
            if "R1" not in vessel or "Cc" not in vessel:
                raise ValueError(f"outlet vessel {i} is missing two-element windkessel values")
        elif outlet == "reflection":
            if "Rt" not in vessel:
                raise ValueError(f"outlet vessel {i} is missing reflection coefficient value")





def makeResultsFolder(data, input_filename):
    project_name = data["project name"]

    if "results folder" not in data:
        r_folder = project_name + "_results"
    else:
        r_folder = data["results folder"]

    # delete existing folder and results!
    if os.path.isdir(r_folder):
        shutil.rmtree(r_folder)
    os.mkdir(r_folder)

    shutil.copy2(input_filename, r_folder + "/")
    copyInletFiles(data, r_folder)

    os.chdir(r_folder)


def copyInletFiles(data, r_folder):
    for vessel in data["network"]:
        if "inlet file" in vessel:
            shutil.copy2(vessel["inlet file"], r_folder + "/")


def buildBlood(blood_data):
    mu = blood_data["mu"]
    rho = blood_data["rho"]
    rho_inv = 1.0 / rho

    global BLOOD
    BLOOD = Blood(mu, rho, rho_inv)


def buildArterialNetwork(network):
    vessel0, vessel_const0 = buildVessel(1, network[0], BLOOD, JUMP)
    vessels = [vessel0]
    vessels_const = [vessel_const0]
    edges = np.zeros((len(network), 3), dtype=np.int32)
    ID = int(vessels_const[0].ID)
    sn = int(vessels_const[0].sn)
    tn = int(vessels_const[0].tn)
    edges[0, 0] = ID
    edges[0, 1] = sn
    edges[0, 2] = tn

    for i in range(1, len(network)):
        vessel, vessel_const = buildVessel(i + 1, network[i], BLOOD, JUMP)
        vessels.append(vessel)
        vessels_const.append(vessel_const)
        ID = int(vessel_const.ID)
        sn = int(vessel_const.sn)
        tn = int(vessel_const.tn)
        edges[i, 0] = ID
        edges[i, 1] = sn
        edges[i, 2] = tn

    inlets = np.zeros((len(network),3), dtype=np.int32)
    outlets = np.zeros((len(network),4), dtype=np.int32)
    for j in np.arange(0,edges.shape[0],1):
        i = edges[j,0]-1
        if vessels_const[i].outlet == "none":
            t = edges[j,2]
            inlets[j,0] = jnp.where(edges[:, 1] == t,jnp.ones_like(edges[:,1]), jnp.zeros_like(edges[:,1])).sum().astype(int)
            outlets[j,0] = jnp.where(edges[:, 2] == t,jnp.ones_like(edges[:,2]), jnp.zeros_like(edges[:,2])).sum().astype(int)
            if inlets[j,0] == 2:
                inlets[j,1] = jnp.where(edges[:, 1] == t)[0][0]
                inlets[j,2] = jnp.where(edges[:, 1] == t)[0][1]

            elif outlets[j,0] == 1:
                outlets[j,1] = jnp.where(edges[:, 1] == t)[0][0]

            elif outlets[j,0] == 2:
                temp1 = jnp.where(edges[:, 2] == t)[0][0]
                temp2 = jnp.where(edges[:, 2] == t)[0][1]
                outlets[j,1] = jnp.minimum(temp1,temp2)#jnp.where(edges[:, 2] == t)[0][0]
                outlets[j,2] = jnp.maximum(temp1,temp2)#jnp.where(edges[:, 2] == t)[0][1]
                outlets[j,3] = jnp.where(edges[:, 1] == t)[0][0]

    global VCS 
    VCS = vessels_const
    global EDGES
    EDGES = Edges(edges, inlets, outlets)
    global HEART
    HEART = vessels_const[0].heart

    mesh_size = 0 
    for v in vessels_const:
        mesh_size += v.M

    global MESH_SIZE_TOT
    MESH_SIZE_TOT = mesh_size
    global NUM_VESSELS
    NUM_VESSELS = len(vessels)
    global MESH_SIZES
    MESH_SIZES = np.zeros(len(vessels)+1,dtype=np.int32)
    sim_dat = jnp.zeros((5, MESH_SIZE_TOT), dtype=jnp.float64)
    sim_dat_aux = jnp.zeros((10, NUM_VESSELS), dtype=jnp.float64)
    
    
    mesh_count = 0

    for i in range(len(vessels)):
        new_mesh_count = mesh_count + vessels_const[i].M
        MESH_SIZES[i+1] = new_mesh_count

        sim_dat = sim_dat.at[0,mesh_count:new_mesh_count].set(vessels[i].u)
        sim_dat = sim_dat.at[1,mesh_count:new_mesh_count].set(vessels[i].Q)
        sim_dat = sim_dat.at[2,mesh_count:new_mesh_count].set(vessels[i].A)
        sim_dat = sim_dat.at[3,mesh_count:new_mesh_count].set(vessels[i].c)
        sim_dat = sim_dat.at[4,mesh_count:new_mesh_count].set(vessels[i].P)
        sim_dat_aux = sim_dat_aux.at[0,i].set(vessels[i].W1M0)
        sim_dat_aux = sim_dat_aux.at[1,i].set(vessels[i].W2M0)
        sim_dat_aux = sim_dat_aux.at[2,i].set(vessels[i].U00Q)
        sim_dat_aux = sim_dat_aux.at[3,i].set(vessels[i].U00A)
        sim_dat_aux = sim_dat_aux.at[4,i].set(vessels[i].U01Q)
        sim_dat_aux = sim_dat_aux.at[5,i].set(vessels[i].U01A)
        sim_dat_aux = sim_dat_aux.at[6,i].set(vessels[i].UM1Q)
        sim_dat_aux = sim_dat_aux.at[7,i].set(vessels[i].UM1A)
        sim_dat_aux = sim_dat_aux.at[8,i].set(vessels[i].UM2Q)
        sim_dat_aux = sim_dat_aux.at[9,i].set(vessels[i].UM2A)

        mesh_count = new_mesh_count

    return vessels, sim_dat, sim_dat_aux


def buildVessel(ID, vessel_data, blood, jump):
    vessel_name = vessel_data["label"]
    sn = int(vessel_data["sn"])
    tn = int(vessel_data["tn"])
    L = float(vessel_data["L"])
    E = float(vessel_data["E"])

    Rp, Rd = computeRadii(vessel_data)
    Pext = getPext(vessel_data)
    M, dx, invDx, halfDx, invDxSq = meshVessel(vessel_data, L)
    h0 = initialiseThickness(vessel_data, M)
    outlet, Rt, R1, R2, Cc = addOutlet(vessel_data)
    viscT = computeViscousTerm(vessel_data, blood)
    inlet, heart = buildHeart(vessel_data)
    phi = getPhi(vessel_data)

    Q = jnp.zeros(M, dtype=jnp.float64)
    P = jnp.zeros(M, dtype=jnp.float64)
    A = jnp.zeros(M, dtype=jnp.float64)
    u = jnp.zeros(M, dtype=jnp.float64)
    c = jnp.zeros(M, dtype=jnp.float64)
    A0 = np.zeros(M, dtype=jnp.float64)
    R0 = np.zeros(M, dtype=jnp.float64)
    s_A0 = np.zeros(M, dtype=jnp.float64)
    beta = np.zeros(M, dtype=jnp.float64)
    wallE = np.zeros(M, dtype=jnp.float64)
    gamma = np.zeros(M, dtype=jnp.float64)
    wallVa = np.zeros(M, dtype=jnp.float64)
    wallVb = np.zeros(M, dtype=jnp.float64)
    inv_A0 = np.zeros(M, dtype=jnp.float64)
    s_inv_A0 = np.zeros(M, dtype=jnp.float64)
    #Q_t = jnp.zeros((jump, 6), dtype=jnp.float64)
    P_t = jnp.zeros((jump, 6), dtype=jnp.float64)
    #A_t = jnp.zeros((jump, 6), dtype=jnp.float64)
    #u_t = jnp.zeros((jump, 6), dtype=jnp.float64)
    #c_t = jnp.zeros((jump, 6), dtype=jnp.float64)
    #Q_l = jnp.zeros((jump, 6), dtype=jnp.float64)
    P_l = jnp.zeros((jump, 6), dtype=jnp.float64)
    #A_l = jnp.zeros((jump, 6), dtype=jnp.float64)
    #u_l = jnp.zeros((jump, 6), dtype=jnp.float64)
    #c_l = jnp.zeros((jump, 6), dtype=jnp.float64)
    s_15_gamma = np.zeros(M, dtype=jnp.float64)
    gamma_ghost = np.zeros(M + 2, dtype=jnp.float64)

    s_pi = np.sqrt(np.pi)
    s_pi_E_over_sigma_squared = s_pi * E / 0.75
    one_over_rho_s_p = 1.0 / (3.0 * blood.rho * s_pi)
    radius_slope = computeRadiusSlope(Rp, Rd, L)

    ah = 0.2802
    bh = -5.053e2
    ch = 0.1324
    dh = -0.1114e2

    if h0 == 0.0:
        Rmean = 0.5 * (Rp + Rd)
        h0 = computeThickness(Rmean, ah, bh, ch, dh)
    
    Cv = 0.5 * s_pi * phi * h0 / (blood.rho * 0.75)

    for i in range(0,M):
        R0[i] = radius_slope * i * dx + Rp
        A0[i] = np.pi * R0[i] * R0[i]
        s_A0[i] = np.sqrt(A0[i])
        inv_A0[i] = 1.0 / A0[i]
        s_inv_A0[i] = np.sqrt(inv_A0[i])
        A = A.at[i].set(A0[i])
        beta[i] = s_inv_A0[i] * h0 * s_pi_E_over_sigma_squared
        gamma[i] = beta[i] * one_over_rho_s_p / R0[i]
        s_15_gamma[i] = np.sqrt(1.5 * gamma[i])
        gamma_ghost[i+1] = gamma[i]
        c = c.at[i].set(waveSpeed(A[i], gamma[i]))
        wallE[i] = 3.0 * beta[i] * radius_slope * inv_A0[i] * s_pi * blood.rho_inv
        if phi != 0.0:
            wallVb[i] = Cv * s_inv_A0[i] * invDxSq
            wallVa[i] = wallVa.at[i].set(0.5 * wallVb[i])
    P = P.at[0:M].set(pressureSA(jnp.ones(M,jnp.float64), beta, Pext))
    

    gamma_ghost[0] = gamma[0]
    gamma_ghost[-1] = gamma[-1]

    if outlet == "wk2":
        R1, R2 = computeWindkesselInletImpedance(R2, blood, A0, gamma)
        outlet = "wk3"

    U00A = A0[0]
    U01A = A0[1]
    UM1A = A0[-1]
    UM2A = A0[-2]

    U00Q = 0.0
    U01Q = 0.0
    UM1Q = 0.0
    UM2Q = 0.0

    W1M0 = u[-1] - 4.0 * c[-1]
    W2M0 = u[-1] + 4.0 * c[-1]

    node2 = int(jnp.floor(M * 0.25)) - 1
    node3 = int(jnp.floor(M * 0.5)) - 1
    node4 = int(jnp.floor(M * 0.75)) - 1

    Pcn = 0.0

    last_A_name = f"{vessel_name}_A.last"
    last_Q_name = f"{vessel_name}_Q.last"
    last_u_name = f"{vessel_name}_u.last"
    last_c_name = f"{vessel_name}_c.last"
    last_P_name = f"{vessel_name}_P.last"

    out_A_name = f"{vessel_name}_A.out"
    out_Q_name = f"{vessel_name}_Q.out"
    out_u_name = f"{vessel_name}_u.out"
    out_c_name = f"{vessel_name}_c.out"
    out_P_name = f"{vessel_name}_P.out"

    return Vessel( A, Q, u, c, P,
                  #A_t, Q_t, u_t, c_t, P_t,
                  #A_l, Q_l, u_l, c_l, P_l,
                  P_t, P_l, W1M0, W2M0,
                  U00A, U00Q, U01A, U01Q, UM1A, UM1Q, UM2A, UM2Q,
                  ), Vessel_const(Pcn,
                  vessel_name, ID, sn, tn, inlet, heart,
                  M, dx, invDx, halfDx,
                  beta, gamma, s_15_gamma, gamma_ghost,
                  A0, s_A0, inv_A0, s_inv_A0, Pext,
                  viscT, wallE, wallVa, wallVb,
                  last_P_name, last_Q_name, last_A_name,
                  last_c_name, last_u_name,
                  out_P_name, out_Q_name, out_A_name,
                  out_c_name, out_u_name,
                  node2, node3, node4,
                  Rt, R1, R2, Cc,
                  outlet)


def computeRadiusSlope(Rp, Rd, L):
    return (Rd - Rp) / L

def computeThickness(R0i, ah, bh, ch, dh):
    return R0i * (ah * jnp.exp(bh * R0i) + ch * jnp.exp(dh * R0i))

def computeRadii(vessel):
    if "R0" not in vessel:
        Rp = float(vessel["Rp"])
        Rd = float(vessel["Rd"])
        return Rp, Rd
    else:
        R0 = float(vessel["R0"])
        return R0, R0

def getPext(vessel):
    if "Pext" not in vessel:
        return 0.0
    else:
        return vessel["Pext"]

def getPhi(vessel):
    if "phi" not in vessel:
        return 0.0
    else:
        return vessel["phi"]

def meshVessel(vessel, L):
    if "M" not in vessel:
        M = max([5, int(jnp.ceil(L * 1e3))])
    else:
        M = vessel["M"]
        M = max([5, M, int(jnp.ceil(L * 1e3))])

    dx = jnp.float64(L) / jnp.float64(M)
    invDx = jnp.float64(M) / jnp.float64(L)
    halfDx = 0.5 * dx
    invDxSq = invDx * invDx

    return M, dx, invDx, halfDx, invDxSq

def initialiseThickness(vessel, M):
    if "h0" not in vessel:
        return 0.0
    else:
        return vessel["h0"]

def addOutlet(vessel):
    if "outlet" in vessel:
        outlet = vessel["outlet"]
        if outlet == "wk3":
            Rt = 0.0
            R1 = float(vessel["R1"])
            R2 = float(vessel["R2"])
            Cc = float(vessel["Cc"])
        elif outlet == "wk2":
            Rt = 0.0
            R1 = 0.0
            R2 = float(vessel["R1"])
            Cc = float(vessel["Cc"])
        elif outlet == "reflection":
            Rt = float(vessel["Rt"])
            R1 = 0.0
            R2 = 0.0
            Cc = 0.0
    else:
        outlet = "none"
        Rt = 0.0
        R1 = 0.0
        R2 = 0.0
        Cc = 0.0

    return outlet, Rt, R1, R2, Cc

def computeViscousTerm(vessel_data, blood):
    gamma_profile = vessel_data.get("gamma_profile", 9)
    return 2 * (gamma_profile + 2) * jnp.pi * blood.mu * blood.rho_inv

def buildHeart(vessel_data):
    if "inlet" in vessel_data:
        inlet_type = vessel_data["inlet"]
        input_data = loadInletData(vessel_data["inlet file"])
        cardiac_period = input_data[-1, 0]
        inlet_number = vessel_data["inlet number"]
        return True, Heart(inlet_type, cardiac_period, input_data, inlet_number)
    else:
        return False, Heart("none", 0.0, jnp.zeros((1, 2)), 0)


def loadInletData(inlet_file):
    numpy_array = np.loadtxt(inlet_file)
    jax_array = jnp.array(numpy_array)
    return jax_array


def computeWindkesselInletImpedance(R2, blood, A0, gamma):
    R1 = blood.rho * waveSpeed(A0[-1], gamma[-1]) / A0[-1]
    R2 -= R1

    return R1, R2

def parseCommandline():
    input_filename = ""
    verbose = False
    out_files = True
    conv_ceil = True

    return input_filename, verbose, out_files, conv_ceil

def buildConst(Ccfl, total_time, conv_toll):
    global CCFL
    CCFL = Ccfl
    global TOTAL_TIME
    TOTAL_TIME = total_time * float(HEART.cardiac_T)
    global CONV_TOLL
    CONV_TOLL = conv_toll
