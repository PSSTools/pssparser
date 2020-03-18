'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_id import ExprId

class ExprHierarchicalIdElem(ExprType):
    
    def __init__(self, name:ExprId, lhs=None):
        super().__init__()
        self.name = name
        self.lhs = lhs
        
    def accept(self, v):
        v.visit_expr_hierarchical_id_elem(self)