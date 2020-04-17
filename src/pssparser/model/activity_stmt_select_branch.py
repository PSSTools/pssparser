'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_scope import ActivityStmtScope
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtSelectBranch(ActivityStmtBase):
    
    def __init__(self,
            guard,
            weight,
            s):
        super().__init__()
    
    def accept(self, v):
        v.visit_activity_stmt_select_branch(self)
        