import networkx as nx
import NetProductPath

intiShortestPathCount = 10

class ShortestPaths:
    def __init__(self, data):
        self.data = data
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
        
        self.productsShortestPaths =  { productId : ShortestPaths() for profuctId in netProduct.productId}

        for (productId, info) in netProduct.products:
            paths = nx.shortest_simple_paths(self.graph, info["source"], info["destination"], weight='weight')
            sPaths = self.ShortestPathsForProduct[productId]
            for i, path in enumerate(paths):
                if i == intiShortestPathCount:
                    break;
                sPaths.paths.append(NetProductPath.Path(id = i, path = path))
                sPaths.unusedPaths.add(i)
            
            if i != intiShortestPathCount:
                paths.maxCount = i+1


    def FindPathInData(self, path, productId):
        if self.data:
            for solverPath in self.data[productId]:
                if solverPath == path:
                    return solverPath
        return None

    def GetNewShortestPath(self, productId, random):
        sPaths = self.ShortestPathsForProduct[productId]
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

                        sPaths.paths += NetProductPath.Path(id = i, path = path)
                        sPaths.unusedPaths.add(i)
                    
                    if i != pathCount*2:
                        paths.maxCount = i+1
                else:
                    return None
            ind = -1
            if random:
                ind = sPaths.unusedPaths.pop()
            else:
                ind = min(paths.unusedPaths)
                sPaths.unusedPaths.remove(ind)

            findedPath = self.FindPathInData(sPaths.paths[ind], productId)
            if not findedPath:
                findedPath.id = ind
            else:
                resultPath = sPaths.paths[ind]
  
        return resultPath
    
    def GetNewShortestPaths(self, productId, random, count):
        resultPaths = []
        while len(resultPaths)<count:
            newPath = self.GetNewShortestPath(productId, random)
            if not newPath:
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

    def InitTempGraph(self, edgesPrices):
        self.tempGraph = nx.DiGraph()
        for (edge, price) in edgesPrices.items():
            self.tempGraph.add_edge(edge[0], edge[1], weight = price)
        
    def ClearTempGraph(self):
        self.tempGraph = None

    def GetShortestPathsFromTempGraph(self, productId, source, destination, count = None, needNext = None):

        if not count:
            c = 0
            def needNextFunc(path):
                c += 1
                return c < count
        elif not needNext:
            needNextFunc = needNext
        else:
            return []

        resultPaths = []
        paths = nx.shortest_simple_paths(self.tempGraph, source, destination, weight='weight')

        for i, path in enumerate(paths):
            if not self.FindPathInData(productId, path):
                resultPaths.append(path)
                if not needNextFunc(path):
                    break

        return resultPaths
    
    