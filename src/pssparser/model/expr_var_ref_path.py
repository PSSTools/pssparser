'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId

class ExprVarRefPath(ExprType):
    
    def __init__(self, hid : ExprHierarchicalId):
        self.hid = hid
        self.lhs : ExprType = None
        self.rhs : ExprType = None
        
    def accept(self, v):
        v.visit_expr_var_ref_path(self)
        
        