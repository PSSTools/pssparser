'''
Created on Apr 20, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class CompileIf(object):
    
    def __init__(self, cond : ExprType):
        self.cond = cond
        
        self.statements_true = []
        self.statements_false = []

    def accept(self, v):
        v.visit_compile_if(self)
        