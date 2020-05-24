
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
Created on Apr 21, 2020

@author: ballance
'''
from enum import Enum, auto


class ExecKind(Enum):
    pre_solve = auto()
    post_solve = auto()
    body = auto()
    header = auto()
    declaration = auto()
    run_start = auto()
    run_end = auto()
    init = auto()
    init_up = auto()
    init_down = auto()

    
    