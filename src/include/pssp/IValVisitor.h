/**
 * IValVisitor.h
 *
 * Copyright 2023 Matthew Ballance and Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may 
 * not use this file except in compliance with the License.  
 * You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software 
 * distributed under the License is distributed on an "AS IS" BASIS, 
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
 * See the License for the specific language governing permissions and 
 * limitations under the License.
 *
 * Created on:
 *     Author: 
 */
#pragma once

namespace pssp {


class IVal;
class IValInt;
class IValStr;
class IValStruct;
class IValArray;


class IValVisitor {
public:

    virtual ~IValVisitor() { }

    virtual void visitVal(IVal *v) = 0;
    
    virtual void visitValInt(IValInt *v) = 0;

    virtual void visitValStr(IValStr *v) = 0;

    virtual void visitValStruct(IValStruct *v) = 0;

    virtual void visitValArray(IValArray *v) = 0;

};

} /* namespace pssp */


