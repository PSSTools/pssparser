#****************************************************************************
#* symbol_type_scope_util.py
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
from .symbol_scope_util import SymbolScopeUtil
import pssparser.core as zspp

@dc.dataclass
class SymbolTypeScopeUtil(SymbolScopeUtil):

    def getSuper(self):
        super_ref = self.obj.getTarget().getSuper_t()
        if super_ref is not None:
            super_ref = zspp.resolveSymbolPathRef(
                self.getRoot(),
                super_ref.getTarget())
        return super_ref


