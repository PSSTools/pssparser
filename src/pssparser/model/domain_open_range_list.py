'''
Created on Apr 22, 2020

@author: ballance
'''

class DomainOpenRangeList(object):
    
    def __init__(self):
        self.rangelist = []
        
    def accept(self, v):
        v.visit_domain_open_range_list(self)
        