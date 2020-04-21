'''
Created on Apr 20, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class CompileAssert(object):
    
    def __init__(self, cond : ExprType, msg):
        self.cond = cond
        self.msg = msg
        
    def accept(self, v):
        v.visit_compile_assert(self)