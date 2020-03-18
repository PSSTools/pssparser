'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from typing import List
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId

class ExprHierarchicalIdList(ExprType):
    
    def __init__(self, hid_l : List[ExprHierarchicalId]=None):
        self.hid_l = hid_l if hid_l is not None else []
        
    def accept(self, v):
        v.visit_expr_hierarchial_id_list(self)