'''
Created on Apr 13, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtWhile(ActivityStmtBase):
    
    def __init__(self, e, s):
        self.e = e
        self.s = s
        
    def accept(self, v):
        v.visit_activity_stmt_while(self)