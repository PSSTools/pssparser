'''
Created on Mar 30, 2020

@author: ballance
'''

class Typedef(object):
    
    def __init__(self, data_type, identifier):
        self.data_type = data_type
        self.identifier = identifier
        
    def accept(self, v):
        v.visit_typedef(self)