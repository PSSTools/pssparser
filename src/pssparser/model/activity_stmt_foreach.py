'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtForeach(ActivityStmtBase):
    
    def __init__(self, 
            it_id,
            e,
            idx_id,
            s):
        super().__init__()
        self.it_id = it_id
        self.e = e
        self.idx_id = idx_id
        self.s = s
        
    def accept(self, v):
        v.visit_activity_stmt_foreach(self)