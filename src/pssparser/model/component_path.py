'''
Created on Apr 22, 2020

@author: ballance
'''

class ComponentPath(object):
    
    def __init__(self, is_wildcard):
        self.is_wildcard = is_wildcard
        self.path_elements = []
        
    def accept(self, v):
        v.visit_component_path(self)
        