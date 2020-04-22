'''
Created on Apr 22, 2020

@author: ballance
'''
from pssparser.model.data_type import DataType

class DataTypeString(DataType):
    
    def __init__(self, in_spec):
        super().__init__()
        self.in_spec = in_spec
        
    def accept(self, v):
        v.visit_data_type_string(self)
        