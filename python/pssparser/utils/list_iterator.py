#****************************************************************************
#* list_iterator.py
#*
#* Copyright 2023 Matthew Ballance and Contributors
#*
#* Licensed under the Apache License, Version 2.0 (the "License"); you may 
#* not use this file except in compliance with the License.  
#* You may obtain a copy of the License at:
#*
#*   http://www.apache.org/licenses/LICENSE-2.0
#*
#* Unless required by applicable law or agreed to in writing, software 
#* distributed under the License is distributed on an "AS IS" BASIS, 
#* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
#* See the License for the specific language governing permissions and 
#* limitations under the License.
#*
#* Created on:
#*     Author: 
#*
#****************************************************************************
import dataclasses as dc
from typing import Callable

@dc.dataclass
class ListIterator(object):
    n_children : int
    get_child : Callable
    index : int = 0

    def __next__(self):
        if self.index >= self.n_children:
            raise StopIteration()
        else:
            ret = self.get_child(self.index)
            self.index += 1
            return ret

    def __iter__(self):
        return self

