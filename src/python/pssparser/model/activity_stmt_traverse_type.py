'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtTraverseType(ActivityStmtBase):
    
    def __init__(self, tid, constraint):
        super().__init__()
        self.tid = tid
        self.constraint = constraint
        
    def accept(self, v):
        v.visit_activity_stmt_traverse_type(self)
        
        