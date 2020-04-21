'''
Created on Apr 20, 2020

@author: ballance
'''

class OverrideBlock(object):
    
    def __init__(self):
        self.statements = []
        
    def accept(self, v):
        v.visit_override_block(self)
        