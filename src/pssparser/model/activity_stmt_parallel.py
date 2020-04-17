'''
Created on Apr 17, 2020

@author: ballance
'''
from pssparser.model.activity_stmt_scope import ActivityStmtScope

class ActivityStmtParallel(ActivityStmtScope):
    
    def __init__(self, join_spec):
        self.join_spec = join_spec
        super().__init__()
        
    def accept(self, v):
        v.visit_activity_stmt_parallel(self)