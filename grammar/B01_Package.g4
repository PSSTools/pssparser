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
grammar Package;


package_declaration:
	'package' name=package_identifier '{'
		package_body_item*
	'}'
;	

package_body_item:
	abstract_action_declaration
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
	| package_body_compile_if
// >>= PSS 1.1
	| component_declaration
// <<= PSS 1.1
	| ';'
	;

import_stmt:
	'import' package_import_pattern ';'
;

package_import_pattern:
	type_identifier ('::' wildcard='*')?
;

extend_stmt:
		(
			('extend' ext_type='action' type_identifier '{'
				action_body_item*
				'}'
			) | 
			('extend' ext_type='component' type_identifier '{'
				component_body_item*
				'}'
			) |
			('extend' struct_kind type_identifier '{'
				struct_body_item*
				'}'
			) |
			('extend' ext_type='enum' type_identifier '{'
				(enum_item (',' enum_item)*)?
				'}'
			)
		)
;

const_field_declaration :
	'const' const_data_declaration
;

const_data_declaration:
	scalar_data_type const_data_instantiation (',' const_data_instantiation)* ';' 
;

const_data_instantiation:	
	identifier '=' init=constant_expression
;

static_const_field_declaration :
	'static' 'const' const_data_declaration
;
