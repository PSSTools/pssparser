'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from enum import Enum, auto

class UnaryOp(Enum):
    Plus = auto()
    Minus = auto()
    BoolNot = auto()
    BitNot = auto()
    BitAnd = auto()
    BitOr = auto()
    BitXor = auto()

class ExprUnary(ExprType):
    
    def __init__(self, expr, op):
        super().__init__()
        self.expr = expr
        self.op = op
        
    def accept(self, v):
        v.visit_expr_unary(self)
    
    