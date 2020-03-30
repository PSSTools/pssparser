'''
Created on Mar 30, 2020

@author: ballance
'''
from enum import Enum, auto


class ScalarType(Enum):
    Bit = auto()
    Bool = auto()
    Chandle = auto()
    Integer = auto()
    String = auto()
    
    
class DataTypeScalar(object):
    
    def __init__(self, 
        scalar_type : ScalarType, 
        lhs,
        rhs,
        in_range):
        self.scalar_type = scalar_type
        self.lhs = lhs
        self.rhs = rhs
        self.in_range = in_range
        
    def accept(self, v):
        v.visit_data_type_scalar(self)
    