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

grammar Identifiers;

constant: 
	number 
	| identifier
	;
	
identifier: 
	ID 
	| ESCAPED_ID
	;
	
hierarchical_id_list:
	hierarchical_id (',' hierarchical_id)*
	;
	
hierarchical_id:
	hierarchical_id_elem ('.' hierarchical_id_elem)*
;

hierarchical_id_elem:
	identifier ('[' expression ']')?
	;
	
action_type_identifier: type_identifier;

// == PSS 1.1
type_identifier: 
	(is_global='::')? type_identifier_elem ('::' type_identifier_elem)* 
	;
	
// >>= PSS 1.1
type_identifier_elem:
	identifier template_param_value_list?
	;
// <<= PSS 1.1 
	
package_identifier: 
	identifier 
	;

// TODO: unused?
covercross_identifier : identifier;

covergroup_identifier : identifier;

coverpoint_target_identifier : hierarchical_id;

action_identifier: identifier;

struct_identifier: identifier;

component_identifier: identifier;

component_action_identifier: identifier;

coverpoint_identifier : identifier;

enum_identifier: identifier;

import_class_identifier: identifier;

// >>= PSS 1.1
label_identifier: identifier;
// <<= PSS 1.1

language_identifier: identifier;

method_identifier: identifier;

symbol_identifier: identifier;

variable_identifier: identifier;

iterator_identifier: identifier;

index_identifier: identifier;

buffer_type_identifier: type_identifier;

covergroup_type_identifier: type_identifier;

resource_type_identifier: type_identifier;

state_type_identifier: type_identifier;

stream_type_identifier: type_identifier;

// Move to LexicalRules
//filename_string: DOUBLE_QUOTED_STRING;


bool_literal:
	'true'|'false'
;


