from time import time

from NetProductPath import NetProducts, Path
from Solver import SolverResult, SolveMIP_HIGHS
from ShortestPaths import ShortestPaths
import Math

class VNS:
    def __init__(self, net: NetProducts):
        self.net = net
        self.data = {}
        self.shortestPaths = ShortestPaths()
        self.result = None
        self.initRes = None

    def Solve(self, maxSolvingTime):
        startTime = time()
        self.shortestPaths.PrepareData(self.net)
        self.InitSolution()
        print("Init:", str(self.result.resultPrice))
        k=1
        sameResult = -1
        while k < 4 and  time() - startTime < maxSolvingTime:
            time1 = self.net.storageCount
            currRes = self.result.resultPrice
            if k == 1:
                self.ProccessAddNewShortestPathsNeighborhood(5, True, 10+time1) 
            elif k == 2:
                self.ProccessAddNewShortestPathsThroughUsedEdgesNeighborhood(3, 5, 100+time1*2)
            elif k == 3:
                self.ProccessAddNewShortestPathsAvoidingStoragesNeighborhood(3, 0.5, self.net.storageCount//4, self.net.storageCount//3, 100+time1*2)

            same = not(sameResult == -1 or Math.Sm(self.result.resultPrice, sameResult))
            sameResult = self.result.resultPrice
            self.ClearData()
            print("After shake", k, ":", str(self.result.resultPrice))
            self.VND(startTime, maxSolvingTime, same)

            if Math.Bg(currRes, self.result.resultPrice):
                k=1
            else: k+=1
        
        self.result.solvingTime = time() - startTime



    def VND(self, startTime, maxSolvingTime, same = False):
        proceed = True
        firstCount = 0
        time1 = self.net.storageCount//2
        time1 = 10 if self.net.storageCount == 100 else 20 
        while proceed and time() - startTime < maxSolvingTime:
            first = self.ProccessAddNewShortestPathsNeighborhood(firstCount % 3 + 1, firstCount % 2, 5+time1)
            firstCount += 1
            print("after first:", str(self.result.resultPrice))
            if not first:
                if same:
                    proceed = False
                    self.ClearData()
                    continue
                second = self.ProccessAddNewShortestPathsThroughUsedEdgesNeighborhood(2, 1, 30 + time1*2)
                print("after second:", str(self.result.resultPrice))
                if not second:
                    proceed = self.ProccessAddNewShortestPathsAvoidingStoragesNeighborhood(1, 0.75, self.net.storageCount//5, self.net.storageCount//4, 30 + time1*2)
                    print("after third:", str(self.result.resultPrice))
                self.ClearData()
            else:
                same = False

    def InitSolution(self):
        self.data = {productId : [Path(path = [info["source"], info["destination"]])] for (productId, info) in self.net.products.items()}
        self.result = SolveMIP_HIGHS(self.net, self.data, 300)
        self.initRes = self.result.resultPrice

    def ClearData(self):
        for (productId, paths) in self.data.items():
            newPaths = []
            newResult = {}
            pathFlow = self.result.productPathFlow[productId]
            for pathI, path  in enumerate(paths):
                if pathI in pathFlow:
                    newPaths.append(path)
                    newResult[len(newPaths)-1] = pathFlow[pathI]
                else:
                    if path.id != -1:
                        self.shortestPaths.RemoveShortestPath(productId, path.id)
            self.data[productId] = newPaths
            self.result.productPathFlow[productId] = newResult


    def AddNewPathsToData(self, newPaths):
        for (productId, paths) in newPaths.items():
            productData = self.data[productId]
            productFlow = self.result.productPathFlow[productId]
            pathI = len(productData)
            for i, path in enumerate(paths):
                if pathI+i in productFlow:
                    productData.append(path)
                    flow = productFlow[pathI+i]
                    productFlow.remove(pathI+i)
                    productFlow[len(productData)-1] = flow
                elif path.id != -1:
                    self.shortestPaths.RemoveShortestPath(productId, path.id)

    def ProcessNewPaths(self, newPaths, maxTime):
        success = any(newPaths.values())

        if success:
            newData = self.data.copy()
                
            for (productId, paths) in newData.items():
                paths += newPaths[productId]
                
            newResult = SolveMIP_HIGHS(self.net, newData, maxTime, initSolution=self.result)
            success = newResult.resultPrice != -1 and (not self.result or Math.Sm(newResult.resultPrice, self.result.resultPrice))
            if success:
                self.result = newResult
                self.AddNewPathsToData(newPaths)
        return success

    def ProccessAddNewShortestPathsNeighborhood(self, newPathsCount, random, maxTime):
        newPaths = {productId : self.shortestPaths.GetNewShortestPaths(productId, random,newPathsCount, self.data) for productId in self.net.productId}
        return self.ProcessNewPaths(newPaths, maxTime)

    def ProccessAddNewShortestPathsAvoidingStoragesNeighborhood(self, newPathsCount, minCount, overloadTreshold, maxStoragesCount, maxTime):
        sumOverload = {storage : 0 for storage in self.net.storageId}
        for (productId, flows) in self.result.productPathFlow.items():
            for (pathI, volume) in flows.items():
                path = self.data[productId][pathI].path
                for storageI in range(1, len(path)-1):
                    sumOverload[path[storageI]]+=volume
        
        overload = [(sumOverload[storageId]/info["maxOverload"], info["overloadPrice"], storageId) for (storageId, info) in self.net.storages.items()] 
        overload.sort(key = lambda x: (x[0],x[1]), reverse=True)
        endI = 1
        for i in range(len(overload)):
            if Math.Bg(overload[i][0],overloadTreshold):
                endI = i+1
            else:
                break
        endI = max(endI, minCount)

        startI = next((i for i, info in enumerate(overload) if Math.Sm(info[0], 1)), len(overload))//2
        maxSize = max(1, min(endI, maxStoragesCount))
        if endI-startI>maxSize:
            endI = startI+maxSize
        else:
            startI = endI-maxSize
        
        avoidedStorages = [info[2] for info in overload[:startI]]
        self.shortestPaths.InitTempGraphAvodingStorages(avoidedStorages)

        newPaths = {productId : [] for productId in self.net.productId}
        
        for i in range(startI, endI):
            self.shortestPaths.RemoveNodeFromTempGraph(overload[i][2])
            for (productId, info) in self.net.products.items():
                newPaths[productId] += self.shortestPaths.GetShortestPathsFromTempGraph(productId, info["source"], info["destination"], self.data, anotherData=newPaths, count = newPathsCount)

        self.shortestPaths.ClearTempGraph()
        
        return self.ProcessNewPaths(newPaths, maxTime)
    
    def ProccessAddNewShortestPathsThroughUsedEdgesNeighborhood(self, newPathsCount, vehicleCoeff, maxTime):
        edgeFlow = {edge : 0 for edge in self.net.edges}
        for (productId, flows) in self.result.productPathFlow.items():
            for (pathI, volume) in flows.items():
                path = self.data[productId][pathI].path
                for storageI in range(len(path)-1):
                    edgeFlow[(path[storageI], path[storageI+1])]+=volume

        edgeFlow = {edge : flow % self.net.vehicleCapacity if Math.Bg(flow % self.net.vehicleCapacity, 0) else self.net.vehicleCapacity for (edge, flow) in edgeFlow.items()}
        
        #newEdgesPrices = {edge : self.net.storages[edge[0]]["overloadPrice"] + self.net.storages[edge[1]]["overloadPrice"] + (flow if Math.Sm(flow, self.net.vehicleCapacity) else self.net.edgesPrices[edge]/self.net.vehicleCapacity) for (edge, flow) in edgeFlow.items()}
        newEdgesPrices = {edge : self.net.storages[edge[0]]["overloadPrice"] + self.net.storages[edge[1]]["overloadPrice"] + (flow/self.net.vehicleCapacity * (self.net.edgesPrices[edge]/self.net.vehicleCapacity)**0.5 if Math.Sm(flow, self.net.vehicleCapacity) else self.net.edgesPrices[edge]/self.net.vehicleCapacity) for (edge, flow) in edgeFlow.items()}
        
        self.shortestPaths.InitTempGraph(newEdgesPrices)

        count = 0
        sumFlow = 0
        
        def needNext(p):
            nonlocal count, sumFlow
            maxFlow = 0
            path = p.path
            for storageI in range(len(path)-1):
                maxFlow = max(maxFlow, edgeFlow[(path[storageI], path[storageI+1])])
            if Math.Eq(maxFlow, self.net.vehicleCapacity):
                count += 1
            else:
                sumFlow += self.net.vehicleCapacity - maxFlow
            return count<newPathsCount and Math.Sm(sumFlow, self.net.vehicleCapacity*vehicleCoeff)

        newPaths = {}
        for (productId, info) in self.net.products.items():
            count = 0
            sumFlow = 0
            newPaths[productId] = self.shortestPaths.GetShortestPathsFromTempGraph(productId, info["source"], info["destination"], self.data, needNext=needNext)
        
        self.shortestPaths.ClearTempGraph()

        return self.ProcessNewPaths(newPaths, maxTime)


