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
        self.target = None
        
    def accept(self, v):
        v.visit_expr_var_ref_path(self)
        
    def __str__(self):
        ret = str(self.hid)
        
        if self.lhs is not None:
            ret += "." + str(self.rhs)
            
        return ret
        
        