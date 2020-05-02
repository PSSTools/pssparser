'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.data_type import DataType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType

class CovergroupCoverpoint(object):
    
    def __init__(self,
                 data_type : DataType,
                 name : ExprId,
                 target : ExprType,
                 iff : ExprType):
        self.data_type = data_type
        self.name = name
        self.target = target
        self.iff = iff 
        self.bins = []
        
    def accept(self, v):
        v.visit_covergroup_coverpoint(self)
        