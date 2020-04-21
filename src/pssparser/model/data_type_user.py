'''
Created on Apr 20, 2020

@author: ballance
'''
from pssparser.model.data_type import DataType

class DataTypeUser(DataType):
    
    def __init__(self, typeid):
        super().__init__()
        self.typeid = typeid
        
    def accept(self, v):
        v.visit_data_type_user(self)