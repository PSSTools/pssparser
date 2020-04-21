
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
from pssparser.model.type_model_visitor import TypeModelVisitor
from enum import Enum, auto
from typing import Set

class TypeCategory(Enum):
    Action = auto()
    Component = auto()
    Struct = auto()

class FindTypesVisitor(TypeModelVisitor):
    
    def __init__(self, types : Set[TypeCategory]):
        self.types = types
        self.type_l = []
        
    def visit_action(self, a):
        if len(self.types) == 0 or TypeCategory.Action in self.types:
            self.type_l.append(a)
        super().visit_action(a)
        
    def visit_component(self, c):
        if len(self.types) == 0 or TypeCategory.Component in self.types:
            self.type_l.append(c)
        super().visit_component(c)
        
            
            