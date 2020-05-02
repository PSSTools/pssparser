'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExecTargetTemplateRef(object):
    
    def __init__(self,
                 start_idx : int,
                 end_idx : int,
                 expr : ExprType):
        self.start_idx = start_idx
        self.end_idx = end_idx
        self.expr = expr
        
    def accept(self, v):
        v.visit_exec_target_template_ref(self)