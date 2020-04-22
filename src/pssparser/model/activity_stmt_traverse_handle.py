'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtTraverseHandle(ActivityStmtBase):
    
    def __init__(self, path, constraint):
        super().__init__()
        self.path = path
        self.constraint = constraint
        
    def accept(self, v):
        v.visit_activity_stmt_traverse_handle(self)
        