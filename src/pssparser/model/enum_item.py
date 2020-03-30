'''
Created on Mar 30, 2020

@author: ballance
'''

class EnumItem(object):
    
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def accept(self, v):
        v.visit_enum_item(self)