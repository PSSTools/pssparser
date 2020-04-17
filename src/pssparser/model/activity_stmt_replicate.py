'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtReplicate(ActivityStmtBase):
    
    def __init__(self, 
                idx_id,
                e,
                arr_label,
                s):
        super().__init__()
        self.idx_id = idx_id
        self.e = e
        self.arr_label = arr_label
        self.s = s
        
    def accept(self, v):
        v.visit_activity_stmt_replicate(self)
    