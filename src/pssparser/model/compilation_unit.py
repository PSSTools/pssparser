'''
Created on Feb 17, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope

class CompilationUnit(TypeScope):
    
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.elements = []
        self.markers = []
        pass
   
    def add_marker(self, m):
        self.markers.append(m)
    
    
    