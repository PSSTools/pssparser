'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtConstraint(ActivityStmtBase):
    
    def __init__(self, cs):
        super().__init__()
        self.cs = cs
        
    def accept(self, v):
        v.visit_activity_stmt_constraint(self)
        