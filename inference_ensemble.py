from os import listdir
from os.path import isfile, join
import numpy as np

mypath = "results/inference_ensemble_sgd/"
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

count = 1e20
print(onlyfiles)
filename_best = ""
for filename in onlyfiles:
    results = np.nan_to_num(np.loadtxt(mypath + filename))/1e8
    print(filename) 
    val = np.sqrt(np.sum(np.square(results[1,:]-results[2,:])))/np.sqrt(np.sum(np.square(results[2,:])))

    if val < count and not np.isnan(val) and not np.isneginf(val) and not np.isposinf(val):
        count = np.sqrt(np.sum(np.square(results[1,:]-results[2,:])))/np.sqrt(np.sum(np.square(results[2,:])))
        filename_best = filename
        print("update")


print(filename_best)