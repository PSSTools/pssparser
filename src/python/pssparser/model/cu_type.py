
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
Created on Feb 24, 2020

@author: ballance
'''
from typing import List, Dict, Tuple
from pssparser.model.type_scope import TypeScope
from pssparser.model.composite_type import CompositeType

class CUType(CompositeType):
    
    def __init__(self, filename):
        super().__init__(None, None, None)
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
