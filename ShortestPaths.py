import networkx as nx
import random as rand

import NetProductPath

intiShortestPathCount = 20

class ShortestPaths:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.productsShortestPaths = {}

    class ShortestPathsForProduct:
        def __init__(self):
            self.paths = []
            self.maxCount = -1
            self.unusedPaths = set()

    def PrepareData(self, netProduct: NetProductPath.NetProducts):
        for edge, price in netProduct.edgesPrices.items():
            self.graph.add_edge(edge[0], edge[1], weight = netProduct.storages[edge[0]]["overloadPrice"] + netProduct.storages[edge[1]]["overloadPrice"] + price/netProduct.vehicleCapacity)
        
        self.productsShortestPaths =  { productId : self.ShortestPathsForProduct() for productId in netProduct.productId}

        for (productId, info) in netProduct.products.items():
            paths = nx.shortest_simple_paths(self.graph, info["source"], info["destination"], weight='weight')
            sPaths = self.productsShortestPaths[productId]
            for i, path in enumerate(paths):
                if i == intiShortestPathCount:
                    break;
                sPaths.paths.append(NetProductPath.Path(id = i, path = path))
                sPaths.unusedPaths.add(i)
            
            if i != intiShortestPathCount:
                sPaths.maxCount = i+1

    def FindPathInData(self, path, productId, data):
        if data:
            for solverPath in data[productId]:
                if solverPath == path:
                    return solverPath
        return None

    def GetNewShortestPath(self, productId, random, data):
        sPaths = self.productsShortestPaths[productId]
        resultPath = None
        while not resultPath:
            if len(sPaths.unusedPaths) == 0:
                if sPaths.maxCount == -1:
                    pathCount = len(sPaths.paths)
                    source = sPaths.paths[0].path[0]
                    destination = sPaths.paths[0].path[-1]
                    paths = nx.shortest_simple_paths(self.graph, source, destination, weight='weight')
                    for i, path in enumerate(paths):
                        if i < pathCount:
                            continue
                        if i == pathCount*2:
                            break

                        sPaths.paths.append(NetProductPath.Path(id = i, path = path))
                        sPaths.unusedPaths.add(i)
                    
                    if i != pathCount*2:
                        paths.maxCount = i+1
                else:
                    return None
            ind = -1
            if random:
                ind = rand.choice(tuple(sPaths.unusedPaths))
                sPaths.unusedPaths.remove(ind)
            else:
                ind = min(sPaths.unusedPaths)
                sPaths.unusedPaths.remove(ind)

            findedPath = self.FindPathInData(sPaths.paths[ind], productId, data)
            if findedPath:
                findedPath.id = ind
            else:
                resultPath = sPaths.paths[ind]
  
        return resultPath
    
    def GetNewShortestPaths(self, productId, random, count, data):
        resultPaths = []
        while len(resultPaths)<count:
            newPath = self.GetNewShortestPath(productId, random, data)
            if newPath:
                resultPaths.append(newPath)
            else:
                break
        return resultPaths
    
    def RemoveShortestPath(self, productId, pathId):
        if pathId!=-1 and pathId < len(self.productsShortestPaths[productId].paths):
            self.productsShortestPaths[productId].unusedPaths.add(pathId)
    
    def InitTempGraphAvodingStorages(self, avoidedStorages):
        self.tempGraph = self.graph.copy()
        self.tempGraph.remove_nodes_from(avoidedStorages)

    def RemoveNodeFromTempGraph(self, storage):
        self.tempGraph.remove_node(storage)

    def AddNodeToTempGraph(self, storage):
        def processSuccessors(v):
            self.tempGraph.add_node(v)
            for u in self.graph.successors(v):
                if self.tempGraph.has_node(u):
                    self.tempGraph.add_edge(v, u, weight = self.graph[v][u]["weight"])

        def processPredecessors(v):
            self.tempGraph.add_node(v)
            for u in self.graph.predecessors(v):
                if self.tempGraph.has_node(u):
                    self.tempGraph.add_edge(u, v, weight = self.graph[u][v]["weight"])

        def process(v):
            processSuccessors(v)
            processPredecessors(v)
        
        process(storage)

    def InitTempGraph(self, edgesPrices):
        self.tempGraph = nx.DiGraph()
        for (edge, price) in edgesPrices.items():
            self.tempGraph.add_edge(edge[0], edge[1], weight = price)
        
    def ClearTempGraph(self):
        self.tempGraph = None

    def GetShortestPathsFromTempGraph(self, productId, source, destination, data, anotherData = None, count = None, needNext = None):
        if count:
            c = 0
            def needNextFunc(path):
                nonlocal c
                c += 1
                return c < count
        elif needNext:
            needNextFunc = needNext
        else:
            return []


        sourceDeleted = not self.tempGraph.has_node(source)
        destinationDeleted = not self.tempGraph.has_node(destination)

        if sourceDeleted:
            self.AddNodeToTempGraph(source)

        if destinationDeleted:
            self.AddNodeToTempGraph(destination)

        resultPaths = []
        paths = nx.shortest_simple_paths(self.tempGraph, source, destination, weight='weight')

        for i, path in enumerate(paths):
            newPath = NetProductPath.Path(path = path)
            if not self.FindPathInData(newPath, productId, data) and not(anotherData and self.FindPathInData(newPath, productId, anotherData)):
                resultPaths.append(newPath)
                if not needNextFunc(newPath):
                    break

        if sourceDeleted:
            self.tempGraph.remove_node(source)

        if destinationDeleted:
            self.tempGraph.remove_node(destination)

        return resultPaths
    
    