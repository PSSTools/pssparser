'''
Created on Apr 13, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtIfElse(ActivityStmtBase):
    
    def __init__(self, e, true_s, false_s):
        self.e = e
        self.true_s = true_s
        self.false_s = false_s
        
    
    def accept(self, v):
        v.visit_activity_stmt_if_else(self)