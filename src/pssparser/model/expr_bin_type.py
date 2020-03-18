'''
Created on Mar 17, 2020

@author: ballance
'''
from enum import Enum, auto

from pssparser.model.expr_type import ExprType


class ExprBinOp(Enum):
    LogOr = auto()
    LogAnd = auto()
    BinOr = auto()
    BinXor = auto()
    BinAnd = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    Exp = auto()
    Mul = auto()
    Div = auto()
    Mod = auto()
    Add = auto()
    Sub = auto()
    Sll = auto()
    Srl = auto()
    EqEq = auto()
    Neq = auto()
    
    
class ExprBinType(ExprType):
    
    def __init__(self, 
                 lhs : ExprType, 
                 op : ExprBinOp, 
                 rhs : ExprType):
        super().__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        
    def accept(self, v):
        v.visit_expr_bin(self)