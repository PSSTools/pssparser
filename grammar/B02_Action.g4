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

grammar Action;

action_declaration:
	'action' action_identifier template_param_decl_list? (action_super_spec)? 
	'{'
		action_body_item*
	'}' 
;

abstract_action_declaration :
	'abstract' 'action' action_identifier template_param_decl_list? (action_super_spec)?
	'{'
		action_body_item*
	'}' 
;

action_super_spec:
	':' type_identifier
;

action_body_item:
	activity_declaration
	| overrides_declaration
	| constraint_declaration
	| action_field_declaration
	| symbol_declaration
	| covergroup_declaration
	| exec_block_stmt
	| static_const_field_declaration
	| action_scheduling_constraint
//TODO	| attr_group
	| compile_assert_stmt
	| covergroup_instantiation
	| action_body_compile_if
	| inline_covergroup
// >>= PSS 1.1
	| ';'
// <<= PSS 1.1
;

activity_declaration: 'activity' '{' activity_stmt* '}' 
	;

action_field_declaration:
// >>= PSS 1.1
	object_ref_declaration
// <<= PSS 1.1
	| attr_field
	| activity_data_field
	| attr_group
	| action_handle_declaration
	| activity_data_field
;

// >>= PSS 1.1
object_ref_declaration:
	flow_ref_declaration
	| resource_ref_declaration
	;
// <<= PSS 1.1
	
// >>= PSS 1.1
flow_ref_declaration:
	(is_input='input' | is_output='output') flow_object_type object_ref_field (',' object_ref_field)* ';'
	;
	
resource_ref_declaration:
	(lock='lock' | share='share') resource_object_type object_ref_field (',' object_ref_field)* ';'
	;
	
object_ref_field:
	identifier array_dim?
	;
// <<= PSS 1.1
	
flow_object_type:
	type_identifier
	;
	
resource_object_type:
	type_identifier
	;
	
attr_field:
	access_modifier? rand='rand'? declaration=data_declaration
;

access_modifier:
	'public' | 'protected' | 'private'
	;
	
attr_group:
	access_modifier ':'
	;
	
action_handle_declaration:
	action_type_identifier action_instantiation ';'
	;
	
action_instantiation:
	ids+=action_identifier (array_dim)? (',' ids+=action_identifier (array_dim)? )*
	;

activity_data_field:
	'action' data_declaration
;

// TODO: BNF has hierarchical_id
action_scheduling_constraint:
	'constraint' (is_parallel='parallel' | is_sequence='sequence') '{'
		variable_ref_path ',' variable_ref_path (',' variable_ref_path)* '}' ';'
	;

// Exec

exec_block_stmt:
	exec_block 
	| target_code_exec_block 
	| target_file_exec_block
// >>= PSS 1.1
    | ';'
// <<= PSS 1.1
	;
	
exec_block:
	'exec' exec_kind_identifier '{' exec_stmt* '}' 
;

exec_kind_identifier:
	'pre_solve' 
	| 'post_solve' 
	| 'body' 
	| 'header' 
	| 'declaration' 
	| 'run_start' 
	| 'run_end' 
	| 'init'
// >>= PSS 1.1
	| 'init_up'
	| 'init_down'
// <<= PSS 1.1
;	

exec_stmt:
	procedural_stmt
	| exec_super_stmt
	;
	
exec_super_stmt:
	'super' ';'
	;

assign_op:
	'=' | '+=' | '-=' | '<<=' | '>>=' | '|=' | '&='
;

target_code_exec_block:
	'exec' exec_kind_identifier language_identifier '=' string ';'
;

target_file_exec_block:
	'exec' 'file' filename_string '=' string ';'
;

	