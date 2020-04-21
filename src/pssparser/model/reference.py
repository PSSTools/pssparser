
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
Created on Mar 9, 2020

@author: ballance
'''

from typing import List, Tuple
from pssparser.model.source_info import SourceInfo

class Reference(object):
    """Captures a fully- or partially-qualified type reference"""
    
    def __init__(self, 
                 ref : Tuple[str],
                 is_global = False):
        self.ref = ref
        self.is_global = is_global # Indicates whether this is a rooted reference
        self.target = None # Pointer to a type declaration
        self.srcinfo : SourceInfo = None
        
    def get_target(self):
        if isinstance(self.target, Reference):
            return self.target.get_target()
        else:
            return self.target
        
    def qname(self) -> str:
        return "::".join(self.ref)
        
    def accept(self, v):
        v.visit_reference(self)
