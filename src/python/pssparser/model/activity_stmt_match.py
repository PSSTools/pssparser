'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtMatch(ActivityStmtBase):
    
    def __init__(self, cond):
        super().__init__()
        self.cond = cond
        self.branches = []
        
    def accept(self, v):
        v.visit_activity_stmt_match(self)