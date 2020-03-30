'''
Created on Mar 30, 2020

@author: ballance
'''

class DataTypeEnum(object):
    
    def __init__(self, identifier, rangelist):
        self.identifier = identifier
        self.rangelist = rangelist
        
    def accept(self, v):
        v.visit_data_type_enum(self)
        