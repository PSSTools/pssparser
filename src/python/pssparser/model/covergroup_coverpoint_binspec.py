'''
Created on May 1, 2020

@author: ballance
'''
from enum import Enum, auto
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType


class BinsType(Enum):
    Bins = auto()
    IllegalBins = auto()
    IgnoreBins = auto()
    
class CovergroupCoverpointBinspec(object):
    
    def __init__(self,
                 bins_type : BinsType,
                 name : ExprId,
                 array_spec : ExprType):
        self.bins_type = bins_type
        self.name = name
        self.array_spec = array_spec
        
    def accept(self, v):
        v.visit_covergroup_coverpoint_binspec(self)
        
    