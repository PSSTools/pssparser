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

from typing import Tuple

from pssparser.model.composite_type import CompositeType
from pssparser.model.data_type_scalar import DataTypeScalar, ScalarType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_num_literal import ExprNumLiteral
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.type_scope import TypeScope


class ComponentType(CompositeType):
    
    def __init__(self, name : ExprId, template_params, super_type:TypeIdentifier):
        from pssparser.model.field_attr import FieldAttr, FieldAttrFlags
        
        super().__init__(name, template_params, super_type)
        
        if super_type is None:
            self.comp_id = self.add_child(FieldAttr(
                ExprId("comp_id"), 
                FieldAttrFlags.Builtin, 
                DataTypeScalar(ScalarType.Bit, ExprNumLiteral(32), None, None), 
                None,
                None))
        else:
            self.comp_id = None
        
    def accept(self, v):
        v.visit_component(self)
