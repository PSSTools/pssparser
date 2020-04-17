'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_scope import ActivityStmtScope

class ActivityStmtSelect(ActivityStmtScope):
    
    def __init__(self):
        super().__init__()
        
        
    def accept(self, v):
        v.visit_activity_stmt_select(self)