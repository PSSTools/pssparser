#****************************************************************************
#* symbol_scope_util.py
#*
#* Copyright 2023 Matthew Ballance and Contributors
#*
#* Licensed under the Apache License, Version 2.0 (the "License"); you may 
#* not use this file except in compliance with the License.  
#* You may obtain a copy of the License at:
#*
#*   http://www.apache.org/licenses/LICENSE-2.0
#*
#* Unless required by applicable law or agreed to in writing, software 
#* distributed under the License is distributed on an "AS IS" BASIS, 
#* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
#* See the License for the specific language governing permissions and 
#* limitations under the License.
#*
#* Created on:
#*     Author: 
#*
#****************************************************************************
import dataclasses as dc
import pssparser.ast as zsp_ast
from .symbol_children_scope_util import SymbolChildrenScopeUtil

@dc.dataclass
class SymbolScopeUtil(SymbolChildrenScopeUtil):

    def getRoot(self):
        obj = self.obj
        while obj.getUpper() is not None:
            obj = obj.getUpper()
        return obj
    
    def getQname(self, name):
        name_l = name.split("::")
        obj = self.obj
        for i,name_e in enumerate(name_l):
            if obj.symtabHas(name_e):
                obj = obj.getChild(obj.symtabAt(name_e))
            else:
                raise Exception("Scope %s does not contain element %s" % (
                    "::".join(name_l[:i]), name_e))
        return obj
    
    def getExtensions(self):
        extensions_s = set()
        extensions = []
        init_def_target = self.obj.getTarget()
        
        for c in self.obj.children():
            parent = c.getParent()
            if parent != init_def_target and parent not in extensions_s:
                extensions_s.add(parent)
                extensions.append(parent)
        return extensions

