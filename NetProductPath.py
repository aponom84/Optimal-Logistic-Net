import pandas as pd

class NetProducts:
    def __init__(self, vehicleCapacity, folder):
        self.storageCount = 0
        self.edgeCount = 0
        self.productCount = 0

        self.edges = [] # список ребер
        self.edgesPrices = {} # словарь ребро - стоимость
        
        self.storageId = [] # список складов
        self.storages = {} # словарь склад - информация о складе

        self.productId = [] # список товаров
        self.products = {} # словарь товар - информация о товаре
        
        self.vehicleCapacity = vehicleCapacity

        df_offices = pd.read_csv(folder+'offices.csv', usecols=['office_id','transfer_price','transfer_max'], dtype={'office_id':int,'transfer_price':float, 'transfer_max':float})
        df_reqs = pd.read_csv(folder+'reqs.csv', dtype={'src':int,'dst':int,'volume':float})
        df_distance_matrix = pd.read_csv(folder+'distance_matrix.csv', usecols =['src','dst','price'], dtype={'src':int,'dst':int, 'price':float})

        for (i, row) in df_offices.iterrows():
            self.storageId.append(int(row['office_id']))
            self.storages[int(row['office_id'])] = {"overloadPrice": row['transfer_price'], "maxOverload": row['transfer_max']}

        for (i, row) in df_reqs.iterrows():
            self.productId.append(i)
            self.products[i] = {"source":int(row['src']), "destination":int(row['dst']), "demand":row['volume']}

        for (i, row) in df_distance_matrix.iterrows():
            if(row['src'] != row['dst'] and row['price']>0):
                edge = (int(row['src']), int(row['dst']))
                self.edges.append(edge)
                self.edgesPrices[edge] = row['price']
        
        self.storageCount = len(self.storageId)
        self.edgeCount = len(self.edges)
        self.productCount = len(self.products)

class Path:
    def __init__(self, id = -1, path = []):
        self.id = id
        self.path = path

    def __eq__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return self.path == other.path

