from pssparser.model.component_type import ComponentType
from pssparser.model.action_type import ActionType
from pssparser.model.struct_type import StructType
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId
from pssparser.model.field_attr import FieldAttrFlags, FieldAttr
from pssparser.model.data_type_user import DataTypeUser
from pssparser.model.activity_stmt_traverse_handle import ActivityStmtTraverseHandle
from pssparser.model.activity_stmt_traverse_type import ActivityStmtTraverseType
from pssparser.model.expr_hierarchical_id_elem import ExprHierarchicalIdElem

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''
Created on Mar 13, 2020

@author: ballance
'''
from enum import Enum, auto
from typing import Dict, List

from pssparser.model.cu_type import CUType
from pssparser.model.expr_static_ref_path import ExprStaticRefPath
from pssparser.model.reference import Reference
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.type_model_visitor import TypeModelVisitor
from pssparser.model.field import Field
from pssparser.model.expr_var_ref_path import ExprVarRefPath


class LinkPhase(Enum):
    GlobalDecls = auto()
    LocalDecls = auto()
    LocalLink = auto()
    
class DeclScope(object):
    
    def __init__(self, linker=None):
        self.decl_m : Dict[str, object] = {}
        self.linker = linker
        
    def add_decl(self, d):
        if isinstance(d, Field):
            self.decl_m[str(d.name)] = d
        else:
            self.decl_m[d.name.toString()] = d
        
        
class LinkVisitor(TypeModelVisitor):
    """Implements linking from references to relevant declarations"""
    
    def __init__(self, cu_l):
        super().__init__()
        self.phase = LinkPhase.GlobalDecls
        self.scope_s = []
        self.depth = 0
        self.target_depth = 0
        self.changes = 0
        self.cu : CUType = None
        self.error_limit = 0
        self.num_errors = 0
        self.children = cu_l
        pass
    
    def link(self):
        for cu in self.children:
            self.push_scope(cu)
            for c in cu.children:
                c.accept(self)
            self.pop_scope()

    def visit_package(self, p):
        self.push_scope(p)
        for ch in p.children:
            ch.accept(self)
        self.pop_scope()
        
    def visit_action(self, a : ActionType):
        if a.super_type is not None:
            a.super_type.accept(self)

        self.push_scope(a)            
        for ch in a.children:
            ch.accept(self)
        self.pop_scope()
        
    def visit_activity_stmt_traverse_handle(self, h : ActivityStmtTraverseHandle):
        # Get things resolved first
        h.path.accept(self)
        if h.constraint is not None:
            field = h.path.hid.path_l[-1].target
            if field is None:
                raise Exception("Failed to resolve ref")
#            ftype = field.ftype.tid.target
            self.push_scope(field)
            h.constraint.accept(self)
            self.pop_scope()
            
    def visit_activity_stmt_traverse_type(self, t : ActivityStmtTraverseType):
        t.tid.accept(self)

        if t.constraint is not None:
            self.push_scope(t.tid.target)
            t.constraint.accept(self)
            self.pop_scope()        
        
    def visit_component(self, c : ComponentType):
        if c.super_type is not None:
            c.super_type.accept(self)
            
        self.push_scope(c)
        for ch in c.children:
            ch.accept(self)
        self.pop_scope()
        
    def visit_expr_hierarchical_id(self, e : ExprHierarchicalId):
        print("visit_expr_hierarchical_id: " + e.toString())
        s = self.scope()

        root_s = None        
        root_n = e.path_l[0].name.toString()
#         while s is not None:
#             print("s=" + str(s))
#             for c in s.children:
#                 print("c=" + str(c) + " root_n=" + root_n)
#                 if hasattr(c, "name") and c.name is not None and c.name.toString() == root_n:
#                     root_s = c
#                     break
#             if root_s is not None:
#                 e.path_l[0].target = root_s
#                 break
#             s = s.parent
        i = len(self.scope_s)-1
        while i>=0:
            print("s=" + str(s))
            s = self.scope_s[i]
            for c in s.children:
                print("c=" + str(c) + " root_n=" + root_n)
                if hasattr(c, "name") and c.name is not None and c.name.toString() == root_n:
                    print("    name=" + c.name.toString())
                    root_s = c
                    e.path_l[0].target = root_s
                    
                    if isinstance(s, FieldAttr):
                        # We're relative to a field, and need to 
                        # resolve this to be relative to a scope
                        e.path_l.insert(0, ExprHierarchicalIdElem(
                            s.name, None))
                        e.path_l[0].target = s
                    break
            if root_s is not None:
                break
            i-=1
            
            
        if root_s is None:
            raise Exception("Failed to find root " + root_n)

        # Now, search down
        for elem in e.path_l[1:]:
            name = elem.name.toString()            
            for c in root_s.children:
                if hasattr(c, "name") and c.name.toString() == name:
                    elem.target = c
                    break
            
            if elem.target is None:
                raise Exception("Failed to find element " + name)

            root_s = elem.target
    
    def visit_expr_var_ref_path(self, r):
        
        print("visit_expr_var_ref_path: " + r.toString())
        # Resolve the path
        r.hid.accept(self)
        
        if r.lhs is not None:
            r.lhs.accept(self)
            
        if r.rhs is not None:
            r.rhs.accept(self)
            
            
    def visit_expr_static_ref_path(self, r:ExprStaticRefPath):
        print("TODO: visit_static_ref_path")
        TypeModelVisitor.visit_expr_static_ref_path(self, r)
        
    def visit_field_attr(self, f):
        super().visit_field_attr(f)
        
        if isinstance(f.ftype, DataTypeUser):
            print("visit_field_attr: DataTypeUser - target=" + str(f.ftype.tid.target))
            if isinstance(f.ftype.tid.target, ComponentType):
                print("Adding in 'Component'")
                f.flags |= FieldAttrFlags.Component
        
        
    def visit_struct_type(self, s : StructType):
        if s.super_type is not None:
            s.super_type.accept(self)
            
        self.push_scope(s)
        for ch in s.children:
            ch.accept(self)
        self.pop_scope()

    def scope(self):
        return self.scope_s[-1]
    
    def push_scope(self, s):
        self.scope_s.append(s)
        
    def pop_scope(self):
        return self.scope_s.pop()
           
            
    def visit_field(self, f):
        if self.phase == LinkPhase.LocalDecls:
            self.scope().add_decl(f)
    
    def visit_reference(self, r):
        pass
    
        
    def find_type_in_scope(self, s, name : str):
        scope = None
        for c in s.children:
            # TODO: need to search imports
            if hasattr(c, "name") and c.name is not None:
                if isinstance(c.name, str):
                    print("Error: c.name is string (" + c.name + ")")
                if c.name is None:
                    print("Name is None for " + str(c))
                print("name: " + c.name.toString())
                if hasattr(c, "name") and c.name.toString() == name:
                    scope = c
                    break
                
        if scope is None and s.super_type is not None:
            if s.super_type.target is None:
                s.super_type.target = self.find_type(s.super_type)

            # Search super-scope
            scope = self.find_type_in_scope(s.super_type.target, name)
            
        return scope

    def visit_type_identifier(self, tid:TypeIdentifier):
        print("--> visit_type_identifier: " + tid.toString())
        tid.target = self.find_type(tid)
        print("<-- visit_type_identifier: " + tid.toString() + " " + str(tid.target))
        
    def find_type(self, tid : TypeIdentifier):
        scope = None
        
        # First, find the root
        if tid.is_global:
            # Start at global scope
            scope = self.scope_s[0]
        else:
            # Go up the stack until we find the name
            i=len(self.scope_s)-1

            scope = None            
            while i>=0:
                s = self.scope_s[i]
                
                scope = self.find_type_in_scope(s, tid.path[0].ref.toString())
                
                if scope is not None:
                    break
                i -= 1
                
        if scope is None:
            raise Exception("Failed to resolve type: " + tid.toString())
        
        # Now, we need to work our way back down
        for e in tid.path[1:]:
            n = None
            for c in scope.children:
                if hasattr(c, "name") and c.name.toString() == e.ref.toString():
                    n = c
                    break
                
            if n is None:
                raise Exception("Failed to resolve type: " + tid.toString() + " (elem " + e.toString + ")")

            scope = n
            
        return scope
        
        
        
    def _resolve_ref(self, ref : ExprVarRefPath):
        scope = self.scope()
        
        target = None
        
        for id in ref.hid.path_l:
            if id.name.toString() in scope.decl_m.keys():
                target = scope.decl_m[str(id.name)]
            else:
                target = None
                break
            
        ref.target = target
        
        
    def _resolve_type(self, ref : TypeIdentifier):
        target = None
        
        ref_i = 0
        
        # First, find the root of the reference
        if ref.is_global:
            if ref.path[ref_i].ref.id in self.scope_s[0].decl_m.keys():
                target = self.scope_s[0].decl_m[ref.path[ref_i].ref.id]
        else:
            # Work up the scope stack searching.
            for si in range(1,len(self.scope_s)+1):
                if ref.path[ref_i].ref.id in self.scope_s[-si].decl_m.keys():
                    # Found it!
                    target = self.scope_s[-si].decl_m[ref.path[ref_i].ref.id]
                    break
            
        if target is None:
            # TODO: Add marker to active CU
            self.num_errors += 1
            if self.error_limit != 0 and self.num_errors > self.error_limit:
                raise Exception("Exceeded error limit")
            return None
            
        if target is not None and len(ref.path) > 1:
            ref_i += 1
            
            while ref_i < len(ref.path):
                new_target = None
                ref_name = ref.path[ref_i].ref.id
                
                for c in target.children:
                    if hasattr(c, "name") and c.name.toString() == ref_name:
                        new_target = c
                        break
                if new_target is None:
                    print("Error: failed to find " + ref.qname() + " in " + target.qname())
                    # TODO: add marker to active CU
                    break
                else:
                    target = new_target
                    
                ref_i += 1
                
        print("Resolve ref=" + ref.toString() + " => " + str(target))

        ref.target = target
        
        return target