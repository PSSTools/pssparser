'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtBind(ActivityStmtBase):
    
    def __init__(self):
        super().__init__()
        self.targets = []
    
    def accept(self, v):
        v.visit_activity_stmt_bind(self)
        