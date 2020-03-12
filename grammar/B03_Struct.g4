/****************************************************************************
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 ****************************************************************************/

grammar Struct;

// == PSS-1.1
struct_declaration: struct_kind identifier template_param_decl_list? (struct_super_spec)? '{'
		struct_body_item*
	'}' 
;

struct_kind:
	img='struct' 
	| object_kind
;

object_kind:
	img='buffer' 
	| img='stream' 
	| img='state' 
	| img='resource'
	;

struct_super_spec : ':' type_identifier
;

struct_body_item:
	constraint_declaration
	| attr_field
	| typedef_declaration
	| covergroup_declaration
	| exec_block_stmt
	| static_const_field_declaration
	| attr_group
	| compile_assert_stmt
	| covergroup_instantiation
	| struct_body_compile_if
// >>= PSS 1.1
    | ';'
// <<= PSS 1.1
;
