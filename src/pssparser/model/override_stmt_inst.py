'''
Created on Apr 20, 2020

@author: ballance
'''
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId
from pssparser.model.type_identifier import TypeIdentifier

class OverrideStmtInst(object):
    
    def __init__(self,
                 target : ExprHierarchicalId,
                 override : TypeIdentifier):
        self.target = target
        self.override = override
        
    def accept(self, v):
        v.visit_override_stmt_inst(self)