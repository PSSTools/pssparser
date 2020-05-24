'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId
from pssparser.model.data_type import DataType

class CovergroupPort(object):
    
    def __init__(self, 
                 name : ExprId, 
                 data_type : DataType):
        self.name = name
        self.data_type = data_type
        
    def accept(self, v):
        v.visit_covergroup_port(self)
        