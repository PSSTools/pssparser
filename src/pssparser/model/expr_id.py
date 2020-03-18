'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprId(ExprType):
    
    def __init__(self, id):
        super().__init__()
        self.id = id
        
    def accept(self, v):
        v.visit_expr_id(self)