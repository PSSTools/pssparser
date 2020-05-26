from pssparser.model.type_identifier_elem import TypeIdentifierElem
from pssparser.model.expr_id import ExprId
import pickle

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
from typing import Tuple
from pssparser.model.type_scope import TypeScope
from pssparser.model.type_identifier import TypeIdentifier

class CompositeType(TypeScope):
    
    def __init__(self, name : ExprId, template_params, super_type:TypeIdentifier):
        super().__init__(name)
        self.template_params = template_params
        self.super_type = super_type
        self.children = []
        self.srcinfo = None
        
    def add_child(self, c):
        if c is not None:
            c.parent = self
            self.children.append(c)
        return c
            
    def add_type(self, c):
        self.add_child(c)
        return c
        
    def getTypeIdentifier(self):
        ret = TypeIdentifier(False)
        ret.target = self
        # TODO: Should probably form a qualified identifier
        ret.path.append(TypeIdentifierElem(self.name, None))
        return ret
            
        
