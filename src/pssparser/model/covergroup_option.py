'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType

class CovergroupOption(object):
    
    def __init__(self, 
                 name : ExprId,
                 value : ExprType):
        self.name = name
        self.value = value
        
    def accept(self, v):
        v.visit_covergroup_option(self)