'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintDefaultDisable(object):
    
    def __init__(self, hid):
        self.hid = hid
        
    def accept(self, v):
        v.visit_constraint_default_disable(self)