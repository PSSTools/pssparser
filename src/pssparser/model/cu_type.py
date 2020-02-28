'''
Created on Feb 24, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope

class CUType(TypeScope):
    
    def __init__(self, filename):
        super().__init__("")
        self.filename = filename
        
        self.type_decl_m = {}
        self.type_ref_m = {}
        self.markers = []
        
    def add_marker(self, m):
        self.markers.append(m)
