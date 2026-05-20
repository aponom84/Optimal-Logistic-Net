import pandas as pd
import os

from Solver import SolverResult, SolverResultEdge

def SaveResult (folder, data, result: SolverResult):
   os.makedirs(folder, exist_ok=True)
   rows = [{'src': data[productId][pathI].path[0], 'dst': data[productId][pathI].path[-1], 'volume': round(volume,6), 'path_nodes': list(map(int, data[productId][pathI].path))} for (productId, paths) in result.productPathFlow.items() for (pathI, volume) in paths.items()]
   df = pd.DataFrame(rows)
   df.to_csv(folder+"/result.scv", index=False, encoding='utf-8')
   vehicles = [{"edge_src":edge[0], "edge_dst":edge[1], "vehicle": int(vehicle)} for (edge, vehicle) in result.edgeVehicleCount.items()]
   df1 = pd.DataFrame(vehicles)
   df1.to_csv(folder+"/EdgeVehicleCount.scv", index=False, encoding='utf-8')
   with open(folder+"/data.txt", "w", encoding="utf-8") as f:
        f.write(f"result price = {result.resultPrice} \n")
        f.write(f"solving time = {result.solvingTime} \n")


def SaveResultEdge (folder, result: SolverResultEdge):
   os.makedirs(folder, exist_ok=True)
   df1 = pd.DataFrame(result.edgeProductFlow)
   df1.to_csv(folder+"/EdgeProductFlow.csv", index=False, encoding='utf-8')
   df2 = pd.DataFrame(result.edgeVehicleCount)
   df2.to_csv(folder+"/EdgeVehicleCount.csv", index=False, encoding='utf-8')
   with open(folder+"/results.txt", "w", encoding="utf-8") as f:
        f.write(f"result price = {result.resultPrice} \n")
        f.write(f"round result price = {result.resultPriceRound} \n")
        f.write(f"solving time = {result.solvingTime} \n")