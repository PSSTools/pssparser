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
from pssparser.model.expr_id import ExprId
from pssparser.model.field_attr import FieldAttr, FieldAttrFlags
from pssparser.model.data_type_user import DataTypeUser
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.data_type_scalar import DataTypeScalar, ScalarType
from portaskela.expr.expr_literalint_type import ExprLiteralIntType
from pssparser.model.expr_num_literal import ExprNumLiteral
from portaskela.pss.component import component

'''
Created on Feb 24, 2020

@author: ballance
'''
from typing import Tuple
from pssparser.model.type_scope import TypeScope
from pssparser.model.composite_type import CompositeType

class ActionType(CompositeType):
    
    def __init__(
            self, 
            name : ExprId,
            component_type, # 
            template_params,
            super_type):
        super().__init__(name, template_params, super_type)
        self.is_abstract = component_type is None
        
        if component_type is not None and super_type is None:
            # Populate core fields
            self.comp = FieldAttr(
                ExprId("comp"),
                FieldAttrFlags.CompHndl|FieldAttrFlags.Builtin,
                DataTypeUser(component_type.getTypeIdentifier()),
                None,
                None)
            self.add_child(self.comp)
            self.comp_id = FieldAttr(
                ExprId("comp_id"),
                FieldAttrFlags.Rand|FieldAttrFlags.Builtin,
                DataTypeScalar(
                    ScalarType.Bit, 
                    ExprNumLiteral(32, "32"), None, None),
                None,
                None)
            self.add_child(self.comp_id)
        else:
            self.comp = None
            self.comp_id = None
        
    def accept(self, v):
        v.visit_action(self)
        
        
    
        