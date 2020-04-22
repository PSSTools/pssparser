'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtMatchBranch(ActivityStmtBase):
    
    def __init__(self, rangelist, stmt):
        self.rangelist = rangelist
        self.stmt = stmt
        
    def accept(self, v):
        v.visit_activity_stmt_match_branch(self)