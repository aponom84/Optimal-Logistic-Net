eps = 10e-6

def Bg(a, b):
    return a-b>eps

def Sm(a,b):
    return b-a>eps

def Eq(a, b):
    return abs(a-b)<eps
