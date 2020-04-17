'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_base import ActivityStmtBase

class ActivityStmtScope(ActivityStmtBase):
    
    def __init__(self):
        super().__init__()
        self.statements = []