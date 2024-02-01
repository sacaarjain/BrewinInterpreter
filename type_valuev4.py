import copy

from enum import Enum
from intbase import InterpreterBase, ErrorType


# Enumerated type for our different language data types
class Type(Enum):
    INT = 1
    BOOL = 2
    STRING = 3
    CLOSURE = 4
    NIL = 5
    OBJECT = 6

class Object:
    def __init__(self):
        self.objectEnv = {}
        self.proto = None

    def getProto(self):
        return self.proto

    def setProto(self, proto):
        self.proto = proto

    def addOrUpdate(self, symbol, value):
        self.objectEnv[symbol] = value

    def getObj(self, symbol):
        if symbol in self.objectEnv:
            return self.objectEnv[symbol]
        
        if self.getProto() is not None:
            prototype = self.getProto()
            objVal = prototype.value().getObj(symbol)
            return objVal

        return None
    
    def getObjectEnv(self):
        return self.objectEnv



class Closure:
    def __init__(self, func_ast, env):
        self.captured_env = copy.deepcopy(env)
        self.func_ast = func_ast
        self.type = Type.CLOSURE


# Represents a value, which has a type and its value
class Value:
    def __init__(self, t, v=None):
        self.t = t
        self.v = v

    def value(self):
        return self.v

    def type(self):
        return self.t

    def set(self, other):
        self.t = other.t
        self.v = other.v

def create_value(val):
    if val == InterpreterBase.TRUE_DEF:
        return Value(Type.BOOL, True)
    elif val == InterpreterBase.FALSE_DEF:
        return Value(Type.BOOL, False)
    elif isinstance(val, int):
        return Value(Type.INT, val)
    elif val == InterpreterBase.NIL_DEF:
        return Value(Type.NIL, None)
    elif isinstance(val, str):
        return Value(Type.STRING, val)


def get_printable(val):
    if val.type() == Type.INT:
        return str(val.value())
    if val.type() == Type.STRING:
        return val.value()
    if val.type() == Type.BOOL:
        if val.value() is True:
            return "true"
        return "false"
    return None
