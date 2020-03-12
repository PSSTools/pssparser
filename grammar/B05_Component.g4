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

grammar Component;

// == PSS-1.1
component_declaration:
	'component' component_identifier template_param_decl_list? 
	(component_super_spec)? '{'
		component_body_item*
	'}' 
;

component_super_spec :
	':' type_identifier
;

component_body_item:
	overrides_declaration
	| component_field_declaration
	| action_declaration
	| object_bind_stmt
	| exec_block
// >>= PSS 1.1 -- replace package_body_item
	| abstract_action_declaration
	| struct_declaration
	| enum_declaration
	| covergroup_declaration
	| function_decl
	| import_class_decl
	| pss_function_defn
	| function_qualifiers
	| target_template_function
	| export_action
	| typedef_declaration
	| import_stmt
	| extend_stmt
	| const_field_declaration
	| static_const_field_declaration	
	| compile_assert_stmt
// <<= PSS 1.1
	| attr_group
	| component_body_compile_if
// >>= PSS 1.1
 	| ';'
// <<= PSS 1.1
;

component_field_declaration:
	component_data_declaration |
	component_pool_declaration
;

component_data_declaration:
	('static' 'const')? data_declaration
;

component_pool_declaration:
	'pool' ('[' expression ']')? type_identifier identifier ';'
;

object_bind_stmt:
	'bind' hierarchical_id object_bind_item_or_list ';'
;

object_bind_item_or_list:
	component_path 
	| ('{' component_path (',' component_path)* '}')
;

// TODO: I believe component_identifier should allow array
component_path:
	 (component_identifier ('.' component_path_elem)*) 
	 | is_wildcard='*'
; 

// TODO: Arrayed flow-object references require arrayed access
component_path_elem:
	component_action_identifier ('[' constant_expression ']')?
	| is_wildcard='*'
;

