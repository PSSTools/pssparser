
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
Created on Mar 30, 2020

@author: ballance
'''
from enum import Enum, auto
from pssparser.model.template_param_decl import TemplateParamDecl
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier

class TemplateTypeCategory(Enum):
    Action = auto()
    Component = auto()
    Struct = auto()
    Buffer = auto()
    Stream = auto()
    State = auto()
    Resource = auto()

class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    
    def __init__(self, 
                 name : ExprId,
                 category : TemplateTypeCategory,
                 type_restriction : TypeIdentifier,
                 default_type : TypeIdentifier ):
        super().__init__(name)
        self.category = category
        self.type_restriction = type_restriction
        self.default_type = default_type
        
    def accept(self, v):
        v.visit_template_category_type_param_decl(self)