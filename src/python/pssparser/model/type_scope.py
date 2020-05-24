
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
Created on Feb 17, 2020

@author: ballance
'''
from .expr_id import ExprId

class TypeScope(object):
    """Base for types in which types are declared"""
    
    def __init__(self, name : ExprId):
        self.parent = None
        self.name = name
        self.imports = []
        # Handle for processing-specific data
        self.data = None
        
    def add_import(self, imp):
        self.imports.append(imp)
        
    def qname(self) -> str:
        # TODO
        return "::".join(self.name.toString())
        
    def accept(self, v):
        raise NotImplementedError("accept not implemented for " + str(self))
        
        
