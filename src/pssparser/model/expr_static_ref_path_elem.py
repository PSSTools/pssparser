
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
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList

class ExprStaticRefPathElem(ExprType):
    
    def __init__(self, id : ExprId, templ:ExprTemplateParamValueList=None):
        self.id = id
        self.templ_param_values = templ