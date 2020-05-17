'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId
from pssparser.model.expr_var_ref_path import ExprVarRefPath

class ActivityStmtTraverseHandle(ActivityStmtBase):
    
    def __init__(self, path : ExprVarRefPath, constraint):
        super().__init__()
        self.path = path
        self.constraint = constraint
        
    def accept(self, v):
        v.visit_activity_stmt_traverse_handle(self)
        