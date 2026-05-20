from VNS import VNS
from Solver import SolveMIP_HIGHS_Edge, SolveMIP_HIGHS_Relaxed
from NetProductPath import NetProducts
from Write import SaveResult, SaveResultEdge
from Generator import GenerateData, generate

from datetime import datetime
import numpy as np

def RunVNS(folder, savingFolder, maxSolvingTime, vehicleCapacity):
    net = NetProducts(vehicleCapacity, folder)
    if net.storageCount > 0:
        vns = VNS(net)
        vns.Solve(maxSolvingTime)
        SaveResult(savingFolder, vns.data, vns.result)
        print("Result:",vns.result.resultPrice)
        print("Solving time:", vns.result.solvingTime)

def RunOptimal1():

    folder = "Generated_Data/Synthetic/"
    result = "Results/Synthetic/Optimal/test"
    vehicleCapacity = 50
    #graphs_to_generate = {10: 10, 20:7, 30:7, 50:5, 100:3, 150:3}
    #graphs_to_generate = {20:7, 30:7, 50:5, 100:3, 150:3}
    graphs_to_generate = {10: 1}
 
    for storage_count, graphs_count in graphs_to_generate.items():
        for i in range(1, graphs_count+1):
            print("Start", storage_count, i, datetime.now())
            folder_name = str(storage_count)+"_nodes_"+str(i)
            net = NetProducts(vehicleCapacity, folder+folder_name+"/")
            solution = SolveMIP_HIGHS_Edge(net, storage_count*60)
            print(storage_count, i, solution.resultPrice, solution.solvingTime)
            SaveResultEdge(result+folder_name, solution)

def RunVNSAndOptimal(folder, savingFolder, maxSolvingTime, vehicleCapacity):
    net = NetProducts(vehicleCapacity, folder+"/")
    if net.storageCount > 0:
        if maxSolvingTime is None:
            maxSolvingTime = 2*net.storageCount*60
        print("Limit time:", maxSolvingTime)
        vns = VNS(net)
        vns.Solve(maxSolvingTime)
        SaveResult(savingFolder, vns.data, vns.result)
        print("VNS Result:",vns.result.resultPrice)
        print("VNS Solving time:", vns.result.solvingTime)
        optimalSolution = SolveMIP_HIGHS_Edge(net, vns.result.solvingTime)
        print("Optimal Result:", optimalSolution.resultPrice)
        with open(savingFolder+"/data.txt", "w", encoding="utf-8") as f:
            f.write(f"result price = {vns.result.resultPrice} \n")
            f.write(f"optimal result price = {optimalSolution.resultPrice} \n")
            f.write(f"init price = {vns.initRes} \n")
            f.write(f"solving time = {vns.result.solvingTime} \n")

def RunOptimal(folder, maxSolvingTime, vehicleCapacity):
    net = NetProducts(vehicleCapacity, folder+"/")
    if net.storageCount > 0:
        print("Start", net.storageCount, 1, datetime.now())
        
        optimalSolution = SolveMIP_HIGHS_Edge(net, maxSolvingTime)
        print("Optimal Result:", optimalSolution.resultPrice)

def GenerateGraphs(folder):
    graphs_to_generate = {10: 10, 20:7, 30:7, 50:5, 100:3, 150:1}
    for storage_count, graphs_count in graphs_to_generate.items():
        for i in range(1, graphs_count+1):
            generate(GenerateData(storage_count, np.random.randint(1,1000)), folder+"/"+str(storage_count)+"_nodes_"+str(i))
            
    
def main():
    #folder = "20_nodes"
    #RunVNS("Data/"+folder+"/", "Results/"+folder+".csv", 10800, 90)
    GenerateGraphs("GeneratedData1")

if __name__ == "__main__":
    main()
