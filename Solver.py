import pulp
from highspy import Highs
from highspy._core import HighsModelStatus  # Импортируем константы статуса
import math

import NetProductPath
import Math


class SolverResult:
    def __init__(self):
        self.resultPrice = -1
        self.edgeVehicleCount = {}
        self.productPathFlow = {}
        self.solvingTime = 0

class SolverResultEdge:
    def __init__(self):
        self.resultPrice = -1
        self.resultPriceRound = -1
        self.edgeVehicleCount = []
        self.edgeProductFlow = []
        self.solvingTime = 0
"""
def SolveMIP(net: NetProductPath.NetProducts, solverData, maxTime = 7200):
    problem = Problem("MIP")

    # Определяем переменные

    # Переменные для путей продуктов
    flowProductPath = {}
    for (productId, info) in net.products.items():
        flowProductPath[productId] = []
        demand = info["demand"]
        for pathI in range(len(solverData[productId])):
            flowProductPath[productId].append(problem.addVariable(lb=0, ub=demand, name="path_"+str(productId)+"_"+str(pathI)))

    # Переменные для количества транспорта на каждом ребре 
    vehicleCount = {edge : problem.addVariable(lb=0, vtype=INTEGER, name="edge_"+str(edge[0])+"_"+str(edge[1])) for edge in net.edges}

    # Вводим целевую функцию
    objectiveExpr = 0

    # Вводим ограничения
    # 1. Удовлетворение запроса для каждого товара
    demandExpr = {productId : 0 for productId in net.productId}
    # 2. Связь между потоком через ребро и количеством ТС
    edgeExpr = {edge : 0 for edge in net.edges}
    # 3. Максимальный перегруз на складе
    storageExpr = {storageId : None for storageId in net.storageId}

    # Теперь заполняем ограничения и целевую функцию, так как они все выражаються примерно одинакого
    # Сначала добавим часть с переменными путей
    for (productId, paths) in solverData.items():
        for pathI, p in enumerate(paths):
            path = p.path
            pathVar = flowProductPath[productId][pathI]
            demandExpr[productId] += pathVar
            for storageI in range(len(path)-1):
                pathEdge = (path[storageI], path[storageI+1])
                if storageI>0:
                    if not storageExpr[pathEdge[0]]:
                        storageExpr[pathEdge[0]] = 0
                    storageExpr[pathEdge[0]] += pathVar
                    objectiveExpr += net.storages[pathEdge[0]]["overloadPrice"] * pathVar
                edgeExpr[pathEdge] += pathVar

    # Затем добавим часть для каждого ребра
    for (edge, edgeVar) in vehicleCount.items():
        edgeExpr[edge] += -net.vehicleCapacity * edgeVar
        objectiveExpr += net.edgesPrices[edge] * edgeVar
    
    # Добавляем ограничения и целевую функцию в модель
    for (productId, dExpr) in demandExpr.items():
        problem.addConstraint(dExpr == float(net.products[productId]["demand"]), name="cDemand_"+str(productId))
    for (edge, eExpr) in edgeExpr.items():
        problem.addConstraint(eExpr <= 0, name="cEdge_"+str(edge[0])+"_"+str(edge[1]))
    for (storageId, sExpr) in storageExpr.items():
        if sExpr:
            problem.addConstraint(sExpr <= float(net.storages[storageId]["maxOverload"]), name="cStorage_"+str(storageId))
    problem.setObjective(objectiveExpr, sense=MINIMIZE)

    # Устанавливаем ограничение времени
    settings = SolverSettings()
    settings.set_parameter("log_to_console", False)
    settings.set_parameter("time_limit", maxTime)

    # Решаем задачу
    problem.solve(settings)

    result = SolverResult()
    if problem.Status.name == "Optimal" or problem.Status.name == "FeasibleFound":
        result.resultPrice = problem.ObjValue
        result.solvingTime = problem.SolveTime
        for (productId, pathsVar) in flowProductPath.items():
            result.productPathFlow[productId] = {}
            for pathI, var in enumerate(pathsVar):
                value = var.getValue()
                if not Math.Eq(0, value):
                    result.productPathFlow[productId][pathI] = value
        result.edgeVehicleCount = {edge : edgeVar.getValue() for (edge, edgeVar) in vehicleCount.items()}

    return result
"""

def SolveMIP_HIGHS(net: NetProductPath.NetProducts, solverData, maxTime = 7200, initSolution : SolverResult = None):
    problem = pulp.LpProblem('MinCostFlow', pulp.LpMinimize)

    # Определяем переменные

    # Переменные для путей продуктов
    flowProductPath = {}
    for (productId, info) in net.products.items():
        flowProductPath[productId] = []
        demand = info["demand"]
        for pathI in range(len(solverData[productId])):
            flowProductPath[productId].append(pulp.LpVariable(lowBound=0, upBound=demand, name="path_"+str(productId)+"_"+str(pathI), cat='Continuous'))

    # Переменные для количества транспорта на каждом ребре 
    vehicleCount = {edge : pulp.LpVariable(lowBound=0, cat='Integer', name="edge_"+str(edge[0])+"_"+str(edge[1])) for edge in net.edges}

    if initSolution:
        for (productId, pathVars) in flowProductPath.items():
            resultFlow = initSolution.productPathFlow[productId]
            for pathI, var in enumerate(pathVars):
                var.setInitialValue(resultFlow[pathI] if pathI in resultFlow else 0)
        
        for (edge, edgeVar) in vehicleCount.items():
            edgeVar.setInitialValue(initSolution.edgeVehicleCount[edge])

    # Вводим целевую функцию
    objectiveExpr = 0

    # Вводим ограничения
    # 1. Удовлетворение запроса для каждого товара
    demandExpr = {productId : 0 for productId in net.productId}
    # 2. Связь между потоком через ребро и количеством ТС
    edgeExpr = {edge : 0 for edge in net.edges}
    # 3. Максимальный перегруз на складе
    storageExpr = {storageId : None for storageId in net.storageId}

    # Теперь заполняем ограничения и целевую функцию, так как они все выражаються примерно одинакого
    # Сначала добавим часть с переменными путей
    for (productId, paths) in solverData.items():
        for pathI, p in enumerate(paths):
            path = p.path
            pathVar = flowProductPath[productId][pathI]
            demandExpr[productId] += pathVar
            for storageI in range(len(path)-1):
                pathEdge = (path[storageI], path[storageI+1])
                if storageI>0:
                    if not storageExpr[pathEdge[0]]:
                        storageExpr[pathEdge[0]] = 0
                    storageExpr[pathEdge[0]] += pathVar
                    objectiveExpr += net.storages[pathEdge[0]]["overloadPrice"] * pathVar
                edgeExpr[pathEdge] += pathVar

    # Затем добавим часть для каждого ребра
    for (edge, edgeVar) in vehicleCount.items():
        edgeExpr[edge] += -net.vehicleCapacity * edgeVar
        objectiveExpr += net.edgesPrices[edge] * edgeVar
    
    # Добавляем ограничения и целевую функцию в модель
    for (productId, dExpr) in demandExpr.items():
        problem.addConstraint(dExpr == float(net.products[productId]["demand"]), name="cDemand_"+str(productId))
    for (edge, eExpr) in edgeExpr.items():
        problem.addConstraint(eExpr <= 0, name="cEdge_"+str(edge[0])+"_"+str(edge[1]))
    for (storageId, sExpr) in storageExpr.items():
        if sExpr:
            problem.addConstraint(sExpr <= float(net.storages[storageId]["maxOverload"]), name="cStorage_"+str(storageId))
    problem.setObjective(objectiveExpr)

    # Решаем задачу
    solver = pulp.HiGHS(
        msg=False,
        mip=True,              
        timeLimit=maxTime,
        warmStart=True,
        mip_rel_gap = 0.01)
        #parallel = 1)   
    problem.solve(solver)

    result = SolverResult()
    if pulp.LpStatus[problem.status] == "Optimal":
        result.resultPrice = pulp.value(problem.objective)
        result.solvingTime = problem.solutionTime
        for (productId, pathsVar) in flowProductPath.items():
            result.productPathFlow[productId] = {}
            for pathI, var in enumerate(pathsVar):
                value = round(var.varValue,6)
                if not Math.Eq(0, value):
                    result.productPathFlow[productId][pathI] = value
        result.edgeVehicleCount = {edge : int(edgeVar.varValue) for (edge, edgeVar) in vehicleCount.items()}

    return result

def SolveMIP_HIGHS_Edge(net: NetProductPath.NetProducts, maxTime = 7200):
    problem = pulp.LpProblem('MinCostFlow', pulp.LpMinimize)

    # Определяем переменные

    # Переменные для потоков продуктов по ребрам
    flowProductEdge = {edge : {productId : pulp.LpVariable(lowBound=0, upBound=info["demand"], name="flow_"+str(edge[0])+"_"+str(edge[1])+"_"+str(productId), cat='Continuous') for productId, info in net.products.items()} for edge in net.edges}

    # Переменные для количества транспорта на каждом ребре 
    vehicleCount = {edge : pulp.LpVariable(lowBound=0, cat='Integer', name="edge_"+str(edge[0])+"_"+str(edge[1])) for edge in net.edges}

    # Вводим целевую функцию
    objectiveExpr = 0

    # Вводим ограничения
    # 1. Удовлетворение запроса для каждого товара
    demandExpr = {storageId : {productId : 0 for productId in net.productId} for storageId in net.storageId}
    # 2. Связь между потоком через ребро и количеством ТС
    edgeExpr = {edge : 0 for edge in net.edges}
    # 3. Максимальный перегруз на складе
    storageExpr = {storageId : None for storageId in net.storageId}

    # Теперь заполняем ограничения и целевую функцию, так как они все выражаються примерно одинакого
    # Сначала добавим часть с переменными потоков
    for edge, edgeVars in flowProductEdge.items():
        for productId, flowVar  in edgeVars.items():
            demandExpr[edge[0]][productId] += flowVar
            demandExpr[edge[1]][productId] -= flowVar
            edgeExpr[edge]+=flowVar
            if (edge[1]!=net.products[productId]["source"] and edge[1]!=net.products[productId]["destination"]):
                storageExpr[edge[1]]+=flowVar
                objectiveExpr+=flowVar*net.storages[edge[1]]["overloadPrice"]

    # Затем добавим часть для каждого ребра
    for (edge, edgeVar) in vehicleCount.items():
        edgeExpr[edge] += -net.vehicleCapacity * edgeVar
        objectiveExpr += net.edgesPrices[edge] * edgeVar
    
    # Добавляем ограничения и целевую функцию в модель
    for (storageId, dExprs) in demandExpr.items():
        for productId, dExpr in dExprs.items():
            dem = 0
            if(storageId==net.products[productId]["source"]):
                dem = float(net.products[productId]["demand"])
            if(storageId==net.products[productId]["destination"]):
                dem = -float(net.products[productId]["demand"])
            problem.addConstraint(dExpr == dem, name="cDemand_"+str(storageId)+"_"+str(productId))
    for (edge, eExpr) in edgeExpr.items():
        problem.addConstraint(eExpr <= 0, name="cEdge_"+str(edge[0])+"_"+str(edge[1]))
    for (storageId, sExpr) in storageExpr.items():
        if sExpr:
            problem.addConstraint(sExpr <= float(net.storages[storageId]["maxOverload"]), name="cStorage_"+str(storageId))
    problem.setObjective(objectiveExpr)

    # Решаем задачу
    solver = pulp.HiGHS(
        msg=False,
        mip=True,              
        timeLimit=maxTime,
        warmStart=True,
        mip_rel_gap = 0.01)
        #parallel = 1)   
    problem.solve(solver)

    result = SolverResultEdge()
    if pulp.LpStatus[problem.status] == "Optimal":
        result.resultPrice = pulp.value(problem.objective)
        result.resultPriceRound = result.resultPrice
        result.solvingTime = problem.solutionTime
        for edge, edgeVars in flowProductEdge.items():
            for (productId, flowVar) in edgeVars.items():
                if not Math.Eq(0, flowVar.varValue):
                    result.edgeProductFlow.append({"edge_src":edge[0], "edge_dst":edge[1], "productId":productId, "flow": int(flowVar.varValue)})
        result.edgeVehicleCount = [{"edge_src":edge[0], "edge_dst":edge[1], "vehicle": int(edgeVar.varValue)} for (edge, edgeVar) in vehicleCount.items()]

    return result

def SolveMIP_HIGHS_Relaxed(net: NetProductPath.NetProducts):
    problem = pulp.LpProblem('MinCostFlow', pulp.LpMinimize)

    # Определяем переменные

    # Переменные для потоков продуктов по ребрам
    flowProductEdge = {edge : {productId : pulp.LpVariable(lowBound=0, upBound=info["demand"], name="flow_"+str(edge[0])+"_"+str(edge[1])+"_"+str(productId), cat='Continuous') for productId, info in net.products.items()} for edge in net.edges}

    # Вводим целевую функцию
    objectiveExpr = 0

    # Вводим ограничения
    # 1. Удовлетворение запроса для каждого товара
    demandExpr = {storageId : {productId : 0 for productId in net.productId} for storageId in net.storageId}
    # 2. Связь между потоком через ребро и количеством ТС
    edgeExpr = {edge : 0 for edge in net.edges}
    # 3. Максимальный перегруз на складе
    storageExpr = {storageId : None for storageId in net.storageId}

    # Теперь заполняем ограничения и целевую функцию, так как они все выражаються примерно одинакого
    # Сначала добавим часть с переменными потоков
    for edge, edgeVars in flowProductEdge.items():
        for productId, flowVar  in edgeVars.items():
            demandExpr[edge[0]][productId] += flowVar
            demandExpr[edge[1]][productId] -= flowVar
            edgeExpr[edge]+=flowVar
            if (edge[1]!=net.products[productId]["source"] and edge[1]!=net.products[productId]["destination"]):
                storageExpr[edge[1]]+=flowVar
                objectiveExpr+=flowVar*net.storages[edge[1]]["overloadPrice"]

    # Затем добавим часть для каждого ребра
    for (edge, edgeExp) in edgeExpr.items():
        objectiveExpr += net.edgesPrices[edge] * edgeExp/net.vehicleCapacity
    
    # Добавляем ограничения и целевую функцию в модель
    for (storageId, dExprs) in demandExpr.items():
        for productId, dExpr in dExprs.items():
            dem = 0
            if(storageId==net.products[productId]["source"]):
                dem = float(net.products[productId]["demand"])
            if(storageId==net.products[productId]["destination"]):
                dem = -float(net.products[productId]["demand"])
            problem.addConstraint(dExpr == dem, name="cDemand_"+str(storageId)+"_"+str(productId))
    for (storageId, sExpr) in storageExpr.items():
        if sExpr:
            problem.addConstraint(sExpr <= float(net.storages[storageId]["maxOverload"]), name="cStorage_"+str(storageId))
    problem.setObjective(objectiveExpr)

    # Решаем задачу
    solver = pulp.HiGHS(
        msg=False,
        mip=True,              
        #timeLimit=maxTime,
        warmStart=True)
        #mip_rel_gap = 0.01,
        #parallel = 1)   
    problem.solve(solver)

    result = SolverResultEdge()
    if pulp.LpStatus[problem.status] == "Optimal":
        result.resultPrice = pulp.value(problem.objective)
        result.solvingTime = problem.solutionTime
        edgeResult = {edge : 0 for edge in net.edges}
        for edge, edgeVars in flowProductEdge.items():
            for (productId, flowVar) in edgeVars.items():
                if not Math.Eq(0, flowVar.varValue):
                    result.edgeProductFlow.append({"edge_src":edge[0], "edge_dst":edge[1], "productId":productId, "flow": int(flowVar.varValue)})
                    edgeResult[edge]+=flowVar.varValue
        result.resultPriceRound = 0
        for edge, price in net.edgesPrices.items():
            edgeResult[edge]/=float(net.vehicleCapacity)
            result.resultPriceRound += price*math.ceil(edgeResult[edge])
        result.edgeVehicleCount = [{"edge_src":edge[0], "edge_dst":edge[1], "vehicle": count} for (edge, count) in edgeResult.items()]
    return result







    