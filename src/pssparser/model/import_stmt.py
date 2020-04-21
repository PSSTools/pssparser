
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

from pssparser.model.reference import Reference
from pssparser.model.StmtBase import StmtBase


class ImportStmt(StmtBase):
    
    def __init__(self, 
                 ref : Reference,
                 is_wildcard : bool):
        super().__init__()
        self.ref = ref
        self.is_wildcard = is_wildcard

    def accept(self, v):
        v.visit_import_stmt(self)
        