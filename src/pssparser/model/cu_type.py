'''
Created on Feb 24, 2020

@author: ballance
'''
from typing import List, Dict, Tuple
from pssparser.model.type_scope import TypeScope
from pssparser.model.composite_type import CompositeType

class CUType(CompositeType):
    
    def __init__(self, filename):
        super().__init__(None, None)
        self.filename = filename
        
        self.type_decl_m : Dict[Tuple[str], 'TypeDecl'] = {}
        self.type_ref_m : Dict[Tuple[str], 'TypeRef'] = {}
        self.package_m : Dict[Tuple[str], 'PackageType'] = {}
        self.markers = []
        
    def add_marker(self, m):
        self.markers.append(m)
        
    def add_package(self, pkg):
        self.package_m[pkg.name] = pkg
        
    def accept(self, v):
        v.visit_compilation_unit(self)
