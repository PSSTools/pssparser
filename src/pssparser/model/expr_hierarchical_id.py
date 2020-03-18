'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from typing import List
from pssparser.model.expr_hierarchical_id_elem import ExprHierarchicalIdElem

class ExprHierarchicalId(ExprType):
    
    def __init__(self, p:List[ExprHierarchicalIdElem]=None):
        super().__init__()
        self.path_l = p if p is not None else []
        
    def accept(self, v):
        v.visit_expr_hierarchical_id(self)
        