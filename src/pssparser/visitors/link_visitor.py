'''
Created on Mar 13, 2020

@author: ballance
'''
from pssparser.model.type_model_visitor import TypeModelVisitor
from enum import Enum, auto
from typing import Dict, List
from pssparser.model.reference import Reference
from pssparser.model.cu_type import CUType

class LinkPhase(Enum):
    GlobalDecls = auto()
    LocalDecls = auto()
    
class DeclScope(object):
    
    def __init__(self, linker=None):
        self.decl_m : Dict[str, object] = {}
        self.linker = linker
        
    def add_decl(self, d):
        self.decl_m[d.name[-1]] = d
        
        
    
class LinkVisitor(TypeModelVisitor):
    """Implements linking from references to relevant declarations"""
    
    def __init__(self, cu_l):
        self.phase = LinkPhase.GlobalDecls
        self.scope_s : List[DeclScope] = [DeclScope(self)]
        self.cu_l = cu_l
        self.cu : CUType = None
        self.error_limit = 0
        self.num_errors = 0
        pass
    
    def link(self):
        
        # First, gather all global declarations
        self.phase = LinkPhase.GlobalDecls
        for cu in self.cu_l:
            self.cu = cu
            cu.accept(self)
            
        self.phase = LinkPhase.LocalDecls
        for cu in self.cu_l:
            self.cu = cu
            cu.accept(self)
        
        pass
    
    def visit_composite_type(self, t):
        # If the composite type has a base type, try to resolve now
        
        if t.super_type is not None:
            target = self._resolve_type(t.super_type)
            
        super().visit_composite_type(t)
   
    def visit_component(self, c):
        # Add an entry to the active declaration scope
        self.scope_s[-1].add_decl(c)
        
        # Bail out if we're only collecting global names
        if self.phase == LinkPhase.GlobalDecls:
            return
        
        super().visit_component(c)
    
    def visit_action(self, a):
        # Add an entry to the active declaration scope
        self.scope_s[-1].add_decl(a)
        
        super().visit_action(a)
        
    def visit_reference(self, r):
        pass
        
    def _resolve_type(self, ref : Reference):
        target = None

        ref_i = 0
        
        # First, find the root of the reference
        if ref.is_global:
            if ref.ref[ref_i] in self.scope_s[0].decl_m.keys():
                target = self.scope_s[0].decl_m[ref.ref[ref_i]]
        else:
            # Work up the scope stack searching.
            for si in range(1,len(self.scope_s)+1):
                if ref.ref[ref_i] in self.scope_s[-si].decl_m.keys():
                    # Found it!
                    target = self.scope_s[-si].decl_m[ref.ref[ref_i]]
                    break
            
        if target is None:
            # TODO: Add marker to active CU
            self.num_errors += 1
            if self.error_limit != 0 and self.num_errors > self.error_limit:
                raise Exception("Exceeded error limit")
            return None
            
        if target is not None and len(ref.ref) > 1:
            ref_i += 1
            
            while ref_i < len(ref.ref):
                new_target = None
                ref_name = ref.ref[ref_i]
                
                for c in target.children:
                    if hasattr(c, "name") and c.name[-1] == ref_name:
                        new_target = c
                        break
                if new_target is None:
                    print("Error: failed to find " + ref.qname() + " in " + target.qname())
                    # TODO: add marker to active CU
                    break
                else:
                    target = new_target
                    
                ref_i += 1
                
        ref.target = target
        
        return target