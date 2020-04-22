'''
Created on Apr 22, 2020

@author: ballance
'''

class DomainOpenRangeValue(object):
    
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
        
    def accept(self, v):
        v.visit_domain_open_range_value(self)
    