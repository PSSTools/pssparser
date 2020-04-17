'''
Created on Apr 13, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtRepeat(ActivityStmtBase):
    
    def __init__(self, loop_var, e, s):
        super().__init__()
        self.loop_var = loop_var
        self.e = e
        self.s = s
        
    def accept(self, v):
        v.visit_activity_stmt_repeat(self)