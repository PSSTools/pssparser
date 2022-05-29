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
parser grammar PSSParser;

options {tokenVocab=PSSLexer;}


compilation_unit : 
	portable_stimulus_description* EOF
	;

portable_stimulus_description : 
	package_body_item 
	| package_declaration
	| component_declaration
	;

/**
 * Annotations allow meta-data to be associated with model elements
 */	
annotation:
	TOK_AT identifier (TOK_LPAREN
		annotation_values?
	TOK_RPAREN)?
	;
	
annotation_values:
	annotation_value (TOK_COMMA annotation_value)*
	;
	
annotation_value:
	identifier TOK_SINGLE_EQ expression
	;


package_declaration:
	annotation*
	TOK_PACKAGE name=package_identifier TOK_LCBRACE
		package_body_item*
	TOK_RCBRACE
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
	| TOK_SEMICOLON
	;

import_stmt:
	TOK_IMPORT package_import_pattern TOK_SEMICOLON
;

package_import_pattern:
	type_identifier (TOK_DOUBLE_COLON wildcard=TOK_ASTERISK)?
;

extend_stmt:
		(
			(TOK_EXTEND ext_type=TOK_ACTION type_identifier TOK_LCBRACE
				action_body_item*
				TOK_RCBRACE
			) | 
			(TOK_EXTEND ext_type=TOK_COMPONENT type_identifier TOK_LCBRACE
				component_body_item*
				TOK_RCBRACE
			) |
			(TOK_EXTEND struct_kind type_identifier TOK_LCBRACE
				struct_body_item*
				TOK_RCBRACE
			) |
			(TOK_EXTEND ext_type=TOK_ENUM type_identifier TOK_LCBRACE
				(enum_item (TOK_COMMA enum_item)*)?
				TOK_RCBRACE
			)
		)
;

const_field_declaration :
	TOK_CONST const_data_declaration
;

const_data_declaration:
	scalar_data_type const_data_instantiation (TOK_COMMA const_data_instantiation)* TOK_SEMICOLON 
;

const_data_instantiation:	
	identifier TOK_SINGLE_EQ init=constant_expression
;

static_const_field_declaration :
	TOK_STATIC TOK_CONST const_data_declaration
;

action_declaration:
	annotation*
	TOK_ACTION action_identifier template_param_decl_list? (action_super_spec)? 
	TOK_LCBRACE
		action_body_item*
	TOK_RCBRACE 
;

abstract_action_declaration :
	annotation*
	TOK_ABSTRACT TOK_ACTION action_identifier template_param_decl_list? (action_super_spec)?
	TOK_LCBRACE
		action_body_item*
	TOK_RCBRACE 
;

action_super_spec:
	TOK_COLON type_identifier
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
	| TOK_SEMICOLON
// <<= PSS 1.1
;

activity_declaration: TOK_ACTIVITY TOK_LCBRACE activity_stmt* TOK_RCBRACE 
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
	(is_input=TOK_INPUT | is_output=TOK_OUTPUT) flow_object_type object_ref_field (TOK_COMMA object_ref_field)* TOK_SEMICOLON
	;
	
resource_ref_declaration:
	(lock=TOK_LOCK | share=TOK_SHARE) resource_object_type object_ref_field (TOK_COMMA object_ref_field)* TOK_SEMICOLON
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
	access_modifier? rand=TOK_RAND? declaration=data_declaration
;

access_modifier:
	TOK_PUBLIC | TOK_PROTECTED | TOK_PRIVATE
	;
	
attr_group:
	access_modifier TOK_COLON
	;

// NOTE: refactored grammar
action_handle_declaration:
	action_type_identifier action_instantiation (TOK_COMMA action_instantiation)* TOK_SEMICOLON
	;
	
action_instantiation:
	action_identifier array_dim?
	;
	
//action_instantiation:
//	ids+=action_identifier (array_dim)? (TOK_COMMA ids+=action_identifier (array_dim)? )*
//	;


activity_data_field:
	TOK_ACTION data_declaration
;

// TODO: BNF has hierarchical_id
action_scheduling_constraint:
	TOK_CONSTRAINT (is_parallel=TOK_PARALLEL | is_sequence=TOK_SEQUENCE) TOK_LCBRACE
		variable_ref_path TOK_COMMA variable_ref_path (TOK_COMMA variable_ref_path)* TOK_RCBRACE TOK_SEMICOLON
	;

// Exec

exec_block_stmt:
	target_file_exec_block
	| exec_block 
	| target_code_exec_block 
	;
	
exec_block:
	TOK_EXEC exec_kind_identifier TOK_LCBRACE exec_stmt* TOK_RCBRACE 
;

exec_kind_identifier:
	TOK_PRE_SOLVE 
	| TOK_POST_SOLVE 
	| TOK_BODY
	| TOK_HEADER
	| TOK_DECLARATION 
	| TOK_RUN_START
	| TOK_RUN_END
	| TOK_INIT
// >>= PSS 1.1
	| TOK_INIT_UP
	| TOK_INIT_DOWN
// <<= PSS 1.1
;	

exec_stmt:
	procedural_stmt
	| exec_super_stmt
	;
	
exec_super_stmt:
	TOK_SUPER TOK_SEMICOLON
	;

assign_op:
	TOK_SINGLE_EQ | TOK_PLUS_EQ | TOK_MINUS_EQ | TOK_SHL_EQ | TOK_SHR_EQ | TOK_OR_EQ | TOK_AND_EQ
;

target_code_exec_block:
	TOK_EXEC exec_kind_identifier language_identifier TOK_SINGLE_EQ string TOK_SEMICOLON
;

target_file_exec_block:
	TOK_EXEC TOK_FILE filename_string TOK_SINGLE_EQ string TOK_SEMICOLON
;

// == PSS-1.1
struct_declaration: 
	annotation*
	struct_kind identifier template_param_decl_list? (struct_super_spec)? TOK_LCBRACE
		struct_body_item*
	TOK_RCBRACE 
;

struct_kind:
	img=TOK_STRUCT 
	| object_kind
;

object_kind:
	img=TOK_BUFFER 
	| img=TOK_STREAM 
	| img=TOK_STATE 
	| img=TOK_RESOURCE
	;

struct_super_spec : TOK_COLON type_identifier
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
    | TOK_SEMICOLON
// <<= PSS 1.1
;

function_decl:
	TOK_FUNCTION method_prototype TOK_SEMICOLON
;

method_prototype:
	method_return_type method_identifier method_parameter_list_prototype
;

method_return_type:
	TOK_VOID
	| data_type
;

method_parameter_list_prototype: 
	TOK_LPAREN
		(
			method_parameter (TOK_COMMA method_parameter)*
		)?
	TOK_RPAREN
;

method_parameter:
	method_parameter_dir? data_type identifier
;

method_parameter_dir:
	TOK_INPUT
	|TOK_OUTPUT
	|TOK_INOUT
;

function_qualifiers:
	(TOK_IMPORT import_function_qualifiers? TOK_FUNCTION type_identifier TOK_SEMICOLON)
	| (TOK_IMPORT import_function_qualifiers? TOK_FUNCTION method_prototype TOK_SEMICOLON)
	;
	
import_function_qualifiers:
	method_qualifiers (language_identifier)? 
	| language_identifier
;

method_qualifiers: 
	TOK_TARGET
	| TOK_SOLVE
;

target_template_function:
	TOK_TARGET language_identifier TOK_FUNCTION method_prototype TOK_SINGLE_EQ string TOK_SEMICOLON
	;

// TODO: method_parameter_list appears unused	
method_parameter_list: 
	TOK_LPAREN (expression (TOK_COMMA expression)*)? TOK_RPAREN
;

// >>= PSS 1.1
pss_function_defn:
	annotation*
	method_qualifiers? TOK_FUNCTION method_prototype TOK_LCBRACE procedural_stmt* TOK_RCBRACE
	;
	
procedural_stmt:
	procedural_block_stmt
	| procedural_expr_stmt
	| procedural_return_stmt
	| procedural_if_else_stmt
	| procedural_match_stmt
	| procedural_repeat_stmt
	| procedural_foreach_stmt
	| procedural_break_stmt
	| procedural_continue_stmt
	| procedural_var_decl_stmt // TODO: positioning this first causes assign to be incorrectly recognized as data_declaration
	| TOK_SEMICOLON // TODO: need to incorporate
	;
	
procedural_block_stmt:
	(annotation* TOK_SEQUENCE)? TOK_LCBRACE procedural_stmt* TOK_RCBRACE
	;
	
procedural_var_decl_stmt:
	data_declaration
	;
	
procedural_expr_stmt:
	(expression TOK_SEMICOLON)
	| (variable_ref_path assign_op expression TOK_SEMICOLON)
	;
	
procedural_return_stmt:
	TOK_RETURN expression? TOK_SEMICOLON
	;
	
procedural_if_else_stmt:
	TOK_IF TOK_LPAREN expression TOK_RPAREN procedural_stmt ( TOK_ELSE procedural_stmt )?
	;
	
procedural_match_stmt:
	TOK_MATCH TOK_LPAREN expression TOK_RPAREN TOK_LCBRACE procedural_match_choice procedural_match_choice* TOK_RCBRACE
	;

procedural_match_choice:
	(TOK_LSBRACE open_range_list TOK_RSBRACE TOK_COLON procedural_stmt)
	| (TOK_DEFAULT TOK_COLON procedural_stmt)
	;

procedural_repeat_stmt:
	(is_while=TOK_WHILE TOK_LPAREN expression TOK_RPAREN procedural_stmt)
	| (is_repeat=TOK_REPEAT TOK_LPAREN (identifier TOK_COLON)? expression TOK_RPAREN procedural_stmt)
	| (is_repeat_while=TOK_REPEAT procedural_stmt TOK_WHILE TOK_LPAREN expression TOK_RPAREN TOK_SEMICOLON)
	;
	
procedural_foreach_stmt:
	TOK_FOREACH TOK_LPAREN (iterator_identifier TOK_COLON)? expression (TOK_LSBRACE index_identifier TOK_RSBRACE)? TOK_RPAREN procedural_stmt
	;
	
procedural_break_stmt:
	TOK_BREAK TOK_SEMICOLON
	;

procedural_continue_stmt:
	TOK_CONTINUE TOK_SEMICOLON
	;
	
// <<= PSS 1.1

// == PSS-1.1
component_declaration:
	TOK_COMPONENT component_identifier template_param_decl_list? 
	(component_super_spec)? TOK_LCBRACE
		component_body_item*
	TOK_RCBRACE 
;

component_super_spec :
	TOK_COLON type_identifier
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
 	| TOK_SEMICOLON
// <<= PSS 1.1
;

component_field_declaration:
	component_data_declaration |
	component_pool_declaration
;

component_data_declaration:
	(is_static=TOK_STATIC is_const=TOK_CONST)? data_declaration
;

component_pool_declaration:
	TOK_POOL (TOK_LSBRACE expression TOK_RSBRACE)? type_identifier identifier (TOK_COMMA identifier)* TOK_SEMICOLON
;

object_bind_stmt:
	TOK_BIND hierarchical_id object_bind_item_or_list TOK_SEMICOLON
;

object_bind_item_or_list:
	component_path 
	| (TOK_LCBRACE component_path (TOK_COMMA component_path)* TOK_RCBRACE)
;

// TODO: I believe component_identifier should allow array
component_path:
	 (component_identifier (TOK_DOT component_path_elem)*) 
	 | is_wildcard=TOK_ASTERISK
; 

// TODO: Arrayed flow-object references require arrayed access
component_path_elem:
	component_action_identifier (TOK_LSBRACE constant_expression TOK_RSBRACE)?
	| is_wildcard=TOK_ASTERISK
;

activity_stmt: 
	(identifier TOK_COLON)? labeled_activity_stmt
	| activity_data_field
	| activity_bind_stmt
	| action_handle_declaration
	| activity_constraint_stmt
	| action_scheduling_constraint
// >>= PSS 1.1
	| activity_replicate_stmt
// <<= PSS 1.1
;

labeled_activity_stmt:
	activity_if_else_stmt
	| activity_repeat_stmt
	| activity_foreach_stmt
	| activity_action_traversal_stmt
	| activity_sequence_block_stmt
	| activity_select_stmt
	| activity_match_stmt
	| activity_parallel_stmt
	| activity_schedule_stmt
	| activity_super_stmt
	| function_symbol_call
// >>= PSS 1.1
	// TODO: need to change align-semicolon spec 
	| TOK_SEMICOLON
// <<= PSS 1.1
;

activity_if_else_stmt:
	TOK_IF TOK_LPAREN expression TOK_RPAREN activity_stmt 
	(TOK_ELSE activity_stmt)?
;

activity_repeat_stmt:
	 (
		(is_while=TOK_WHILE TOK_LPAREN expression TOK_RPAREN activity_stmt) |
		(is_repeat=TOK_REPEAT TOK_LPAREN (loop_var=identifier TOK_COLON)? expression TOK_RPAREN activity_stmt) |
		(is_do_while=TOK_REPEAT activity_stmt is_do_while=TOK_WHILE TOK_LPAREN expression TOK_RPAREN TOK_SEMICOLON)
		)
;

activity_replicate_stmt:
	TOK_REPLICATE TOK_LPAREN (index_identifier TOK_COLON)? expression TOK_RPAREN ( identifier TOK_LSBRACE TOK_RSBRACE TOK_COLON)? 
		labeled_activity_stmt
	;

activity_sequence_block_stmt:
	(TOK_SEQUENCE)? TOK_LCBRACE  activity_stmt* TOK_RCBRACE 
;

activity_constraint_stmt:
	TOK_CONSTRAINT constraint_set 
;

activity_foreach_stmt:
	TOK_FOREACH TOK_LPAREN (it_id=iterator_identifier)? expression (TOK_LSBRACE idx_id=index_identifier TOK_RSBRACE)? TOK_RPAREN
		activity_stmt
;

activity_action_traversal_stmt:
	(identifier (TOK_LSBRACE expression TOK_RSBRACE)? TOK_SEMICOLON)
	| (identifier (TOK_LSBRACE expression TOK_RSBRACE)? TOK_WITH constraint_set)
	| (is_do=TOK_DO type_identifier TOK_SEMICOLON)
	| (is_do=TOK_DO type_identifier TOK_WITH constraint_set)
;

activity_select_stmt:
	TOK_SELECT TOK_LCBRACE
		select_branch
		select_branch
		select_branch*
	TOK_RCBRACE
;

select_branch:
	(
		(TOK_LPAREN guard=expression TOK_RPAREN (TOK_LSBRACE weight=expression TOK_RSBRACE)? TOK_COLON) 
		| (TOK_LSBRACE weight=expression TOK_RSBRACE TOK_COLON)
	)? activity_stmt
	;

activity_match_stmt:
	TOK_MATCH TOK_LPAREN expression TOK_RPAREN TOK_LCBRACE
		match_choice
		match_choice
		match_choice*
	TOK_RCBRACE
	;
	
match_choice:
	(TOK_LSBRACE open_range_list TOK_RSBRACE TOK_COLON activity_stmt)
	| (is_default=TOK_DEFAULT TOK_COLON activity_stmt)
	;
	
activity_parallel_stmt:
	 TOK_PARALLEL activity_join_spec? TOK_LCBRACE
		activity_stmt*
	TOK_RCBRACE 
;

activity_schedule_stmt:
	 TOK_SCHEDULE activity_join_spec? TOK_LCBRACE
		activity_stmt*
	TOK_RCBRACE 
;

// >>= PSS 1.1
activity_join_spec:
	activity_join_branch_spec
	| activity_join_select_spec
	| activity_join_none_spec
	| activity_join_first_spec
	;
	
activity_join_branch_spec:
	TOK_JOIN_BRANCH TOK_LPAREN label_identifier (TOK_COMMA label_identifier)* TOK_RPAREN
	;
	
activity_join_select_spec:
	TOK_JOIN_SELECT TOK_LPAREN expression TOK_RPAREN
	;
	
activity_join_none_spec:
	TOK_JOIN_NONE
	;
	
activity_join_first_spec:
	TOK_JOIN_FIRST TOK_LPAREN expression TOK_RPAREN
	;
	
// <<= PSS 1.1

activity_bind_stmt:
	TOK_BIND hierarchical_id activity_bind_item_or_list TOK_SEMICOLON
;

activity_bind_item_or_list:
	hierarchical_id 
	| (TOK_LCBRACE hierarchical_id (TOK_COMMA hierarchical_id)* TOK_RCBRACE)
;

symbol_declaration:
	TOK_SYMBOL identifier (TOK_LPAREN symbol_paramlist TOK_RPAREN)? TOK_LCBRACE activity_stmt* TOK_RCBRACE
;

symbol_paramlist:
	 (symbol_param (TOK_COMMA symbol_param)*)?
;

symbol_param:
	data_type identifier
;

activity_super_stmt:
	TOK_SUPER TOK_SEMICOLON
	;

overrides_declaration:
	 TOK_OVERRIDE TOK_LCBRACE override_stmt* TOK_RCBRACE
;

override_stmt:
	type_override 
	| instance_override
// >>= PSS 1.1
	| TOK_SEMICOLON
// <<= PSS 1.1
;

type_override:
	TOK_TYPE target=type_identifier TOK_WITH override=type_identifier TOK_SEMICOLON
;


instance_override:
	TOK_INSTANCE target=hierarchical_id TOK_WITH override=type_identifier TOK_SEMICOLON
;


data_declaration:
	data_type data_instantiation (TOK_COMMA data_instantiation)* TOK_SEMICOLON 
;

data_instantiation:
	identifier (array_dim)? (TOK_SINGLE_EQ constant_expression)?
	;

/*	
covergroup_portmap_list:
	(
		// Name-mapped port binding
		(covergroup_portmap (TOK_COMMA covergroup_portmap)*) 
		// Positional port binding
		| (hierarchical_id (TOK_COMMA hierarchical_id)*)
	)?
;

covergroup_portmap:
	TOK_DOT identifier TOK_LPAREN hierarchical_id TOK_RPAREN
;
 */

array_dim:
	 TOK_LSBRACE constant_expression TOK_RSBRACE
;


data_type:
	scalar_data_type 
// >>= PSS 1.1
	| container_type
// <<= PSS 1.1
	| user_defined_datatype
;

// >>= PSS 1.1
container_type:
	| (TOK_ARRAY TOK_LT container_elem_type TOK_COMMA array_size_expression TOK_GT)
	| (TOK_LIST TOK_LT container_elem_type TOK_GT)
	| (TOK_MAP TOK_LT container_key_type TOK_COMMA container_elem_type TOK_GT)
	| (TOK_SET TOK_LT container_key_type TOK_GT)
	;
	
array_size_expression:
	constant_expression
	;
	
container_elem_type:
	container_type
	| scalar_data_type
	| type_identifier
	;
	
container_key_type:
	scalar_data_type
	| enum_identifier
	;
// <<= PSS 1.1

scalar_data_type:
	chandle_type 	|
	integer_type 	|
	string_type  	|
	bool_type
;

chandle_type:
	 TOK_CHANDLE
;

integer_type:
	integer_atom_type (TOK_LSBRACE lhs=expression (TOK_COLON rhs=expression)? TOK_RSBRACE)?
		(is_in=TOK_IN TOK_LSBRACE domain=domain_open_range_list TOK_RSBRACE)?
;

integer_atom_type:
	TOK_INT
	| TOK_BIT
;

domain_open_range_list:
	domain_open_range_value (TOK_COMMA domain_open_range_value)*
;

domain_open_range_value:
	lhs=expression (limit_high=TOK_ELIPSIS (rhs=expression)?)?
	| lhs=expression limit_high=TOK_ELIPSIS
	| (limit_low=TOK_ELIPSIS rhs=expression)
	| lhs=expression
;

string_type: TOK_STRING ( TOK_IN TOK_LSBRACE DOUBLE_QUOTED_STRING (TOK_COMMA DOUBLE_QUOTED_STRING)* TOK_RSBRACE)? 
;  

bool_type:
	 TOK_BOOL
;

user_defined_datatype:
	type_identifier
;

enum_declaration:
  	TOK_ENUM enum_identifier TOK_LCBRACE 
  		(enum_item (TOK_COMMA enum_item)*)?
  		TOK_RCBRACE 
  ;
  
enum_item:
	identifier (TOK_SINGLE_EQ constant_expression)?
;

enum_type:
	enum_type_identifier (TOK_IN TOK_LSBRACE open_range_list TOK_RSBRACE)?
;

enum_type_identifier:
	type_identifier
	;
	
typedef_declaration:
 	TOK_TYPEDEF data_type type_identifier TOK_SEMICOLON 
;

// >>= PSS-1.1

template_param_decl_list: 
	TOK_LT template_param_decl ( TOK_COMMA template_param_decl )* TOK_GT
	;

template_param_decl:
	type_param_decl 
	| value_param_decl
	;

type_param_decl: 
	generic_type_param_decl 
	| category_type_param_decl
	;

generic_type_param_decl: 
	TOK_TYPE identifier ( TOK_SINGLE_EQ type_identifier )?
	;

category_type_param_decl: 
	type_category identifier ( type_restriction )? ( TOK_SINGLE_EQ type_identifier )?
	;

type_restriction: 
	TOK_COLON type_identifier
	;

type_category:
    TOK_ACTION
  | TOK_COMPONENT
  | struct_kind
  ;

value_param_decl: 
	data_type identifier ( TOK_SINGLE_EQ constant_expression )?
	;

template_param_value_list: 
	TOK_LT ( template_param_value ( TOK_COMMA template_param_value )* )? TOK_GT
	;

template_param_value: 
	constant_expression 
	| type_identifier
	;

// <<= PSS-1.1

constraint_declaration:
	(
		// Note: 1.0 doesn't allow a semicolon after the block constraint forms,
		// despite examples showing this
		((is_dynamic=TOK_DYNAMIC)? TOK_CONSTRAINT identifier TOK_LCBRACE constraint_body_item* TOK_RCBRACE ) 
		| (TOK_CONSTRAINT constraint_set )
	)
;

//constraint_declaration ::=
//       [ dynamic ] constraint identifier { { constraint_body_item } }
//     | constraint constraint_set


constraint_body_item:
	expression_constraint_item
	| implication_constraint_item
	| foreach_constraint_item
	| if_constraint_item
	| unique_constraint_item
// >>= PSS 1.1
	| default_constraint_item
	| forall_constraint_item
	| TOK_SEMICOLON
// <<= PSS 1.1
;

// >>= PSS 1.1
default_constraint_item:
	default_constraint
	| default_disable_constraint
	;
	
default_constraint:
	TOK_DEFAULT hierarchical_id TOK_DOUBLE_EQ constant_expression TOK_SEMICOLON
	;

default_disable_constraint:
	TOK_DEFAULT TOK_DISABLE hierarchical_id TOK_SEMICOLON
	;	
	
forall_constraint_item:
	TOK_FORALL TOK_LPAREN identifier TOK_COLON type_identifier (TOK_IN variable_ref_path)? TOK_RPAREN constraint_set
	;
// <<= PSS 1.1

expression_constraint_item:
	expression TOK_SEMICOLON
;

implication_constraint_item:
	expression TOK_IMPLIES constraint_set
;

constraint_set:
	constraint_body_item | 
	constraint_block
;

constraint_block:
	 TOK_LCBRACE constraint_body_item* TOK_RCBRACE
;

foreach_constraint_item:
	TOK_FOREACH TOK_LPAREN (it_id=iterator_identifier TOK_COLON)? expression (TOK_LSBRACE idx_id=index_identifier TOK_RSBRACE)? TOK_RPAREN constraint_set
;

if_constraint_item:
	TOK_IF TOK_LPAREN expression TOK_RPAREN constraint_set (TOK_ELSE constraint_set )? 
;

unique_constraint_item:
	TOK_UNIQUE TOK_LCBRACE hierarchical_id_list TOK_RCBRACE TOK_SEMICOLON
;

single_stmt_constraint:
	expression_constraint_item |
	unique_constraint_item
;


covergroup_declaration:
	TOK_COVERGROUP name=covergroup_identifier (TOK_LPAREN covergroup_port (TOK_COMMA covergroup_port)* TOK_RPAREN)? TOK_LCBRACE
		covergroup_body_item*
	TOK_RCBRACE 
;

covergroup_port:
	data_type identifier
;

covergroup_body_item:
	covergroup_option
	| covergroup_coverpoint
	| covergroup_cross
// >>= PSS 1.1
	| TOK_SEMICOLON
// <<= PSS 1.1
;

covergroup_option:
	TOK_OPTION TOK_DOT identifier TOK_SINGLE_EQ constant_expression TOK_SEMICOLON
;

covergroup_instantiation:
	covergroup_type_instantiation
	| inline_covergroup
	;
	
inline_covergroup:
	TOK_COVERGROUP TOK_LCBRACE
		covergroup_body_item*
	TOK_RCBRACE identifier TOK_SEMICOLON
;

covergroup_type_instantiation:
	covergroup_type_identifier covergroup_identifier
	TOK_LPAREN covergroup_portmap_list TOK_RPAREN (TOK_WITH TOK_LCBRACE (covergroup_option)? TOK_RCBRACE)? TOK_SEMICOLON
	;
	
covergroup_portmap_list:
	(
		(covergroup_portmap (TOK_COMMA covergroup_portmap)?)
		| hierarchical_id_list
	)
	;
	
covergroup_portmap:
	TOK_DOT identifier TOK_LPAREN hierarchical_id TOK_RPAREN
	;
		
covergroup_coverpoint: 
		(data_type? coverpoint_identifier TOK_COLON)? TOK_COVERPOINT target=expression (TOK_IFF TOK_LPAREN iff=expression TOK_RPAREN)?
			bins_or_empty
;

bins_or_empty:
		(TOK_LCBRACE covergroup_coverpoint_body_item* TOK_RCBRACE ) 
		| TOK_SEMICOLON
;

covergroup_coverpoint_body_item:
	covergroup_option
	| covergroup_coverpoint_binspec
;

covergroup_coverpoint_binspec: (
		(bins_keyword identifier (is_array=TOK_LSBRACE constant_expression? TOK_RSBRACE)? TOK_SINGLE_EQ coverpoint_bins)
	)
;

coverpoint_bins:
	(
		(TOK_LSBRACE covergroup_range_list TOK_RSBRACE (TOK_WITH TOK_LPAREN covergroup_expression TOK_RPAREN)? TOK_SEMICOLON)
		| (coverpoint_identifier TOK_WITH TOK_LPAREN covergroup_expression TOK_RPAREN TOK_SEMICOLON)
		| is_default=TOK_DEFAULT TOK_SEMICOLON
	)
;

covergroup_range_list:
	covergroup_value_range (TOK_COMMA covergroup_value_range)*
	;

covergroup_value_range:
	expression
	| (expression TOK_ELIPSIS expression?)
	| (expression?	TOK_ELIPSIS expression)
	;

bins_keyword:
	TOK_BINS
	| TOK_ILLEGAL_BINS
	| TOK_IGNORE_BINS 
;

covergroup_cross: 
	identifier TOK_COLON TOK_CROSS coverpoint_identifier (TOK_COMMA coverpoint_identifier)*
		(TOK_IFF TOK_LPAREN iff=expression TOK_RPAREN)? cross_item_or_null
;

cross_item_or_null:
	(TOK_LCBRACE covergroup_cross_body_item* TOK_RCBRACE )
	| TOK_SEMICOLON
;

covergroup_cross_body_item:
	covergroup_option
	| covergroup_cross_binspec
	;
	

covergroup_cross_binspec:
	bins_type=bins_keyword name=identifier  
		TOK_SINGLE_EQ covercross_identifier TOK_WITH TOK_LPAREN expr=covergroup_expression TOK_RPAREN TOK_SEMICOLON
	;

// TODO: no definition in the BNF	
covergroup_expression:
	expression
	;
	
	
package_body_compile_if:
	TOK_COMPILE TOK_IF TOK_LPAREN cond=constant_expression TOK_RPAREN true_body=package_body_compile_if_item
	(TOK_ELSE false_body=package_body_compile_if_item)?
;

package_body_compile_if_item:
	package_body_item
	| (TOK_LCBRACE package_body_item* TOK_RCBRACE)
;

action_body_compile_if:
	TOK_COMPILE TOK_IF TOK_LPAREN cond=constant_expression TOK_RPAREN true_body=action_body_compile_if_item
	(TOK_ELSE false_body=action_body_compile_if_item)?
;

action_body_compile_if_item:
	action_body_item
	| (TOK_LCBRACE action_body_item* TOK_RCBRACE)
;

component_body_compile_if:
	TOK_COMPILE TOK_IF TOK_LPAREN cond=constant_expression TOK_RPAREN true_body=component_body_compile_if_item
	(TOK_ELSE false_body=component_body_compile_if_item)?
;

component_body_compile_if_item:
	component_body_item
	| (TOK_LCBRACE component_body_item* TOK_RCBRACE)
	;
	
struct_body_compile_if:
	TOK_COMPILE TOK_IF TOK_LPAREN cond=constant_expression TOK_RPAREN true_body=struct_body_compile_if_item
	(TOK_ELSE false_body=struct_body_compile_if_item)?
;

struct_body_compile_if_item:
	struct_body_item
	| (TOK_LCBRACE struct_body_item* TOK_RCBRACE)
;

// == PSS 1.1 -- replace static_ref with static_ref_path
compile_has_expr:
	TOK_COMPILE TOK_HAS TOK_LPAREN static_ref_path TOK_RPAREN
	;
	
compile_assert_stmt :
	TOK_COMPILE TOK_ASSERT TOK_LPAREN cond=constant_expression (TOK_COMMA msg=string)? TOK_RPAREN TOK_SEMICOLON
;

constant_expression: expression;


expression:
	unary_op lhs=expression								|
	lhs=expression exp_op rhs=expression 				|
	lhs=expression mul_div_mod_op rhs=expression 		|
	lhs=expression add_sub_op rhs=expression			|
	lhs=expression shift_op rhs=expression				|
	lhs=expression inside_expr_term						|
    lhs=expression logical_inequality_op rhs=expression	|
    lhs=expression eq_neq_op rhs=expression				|
    lhs=expression binary_and_op rhs=expression			|
    lhs=expression binary_xor_op rhs=expression			|
    lhs=expression binary_or_op rhs=expression			|
    lhs=expression logical_and_op rhs=expression		|
    lhs=expression logical_or_op rhs=expression			|
    lhs=expression conditional_expr						|
	primary
	;

conditional_expr :
	TOK_COND true_expr=expression TOK_COLON false_expr=expression
	; 

logical_or_op : TOK_DOUBLE_OR;
logical_and_op : TOK_DOUBLE_AND;
binary_or_op : TOK_SINGLE_OR;
binary_xor_op : TOK_CARET;
binary_and_op : TOK_SINGLE_AND;

inside_expr_term :
	TOK_IN TOK_LSBRACE open_range_list TOK_RSBRACE
;

open_range_list:
	open_range_value (TOK_COMMA open_range_value)*
;

open_range_value:
	lhs=expression (TOK_ELIPSIS rhs=expression)?
;

logical_inequality_op:
	TOK_LT|TOK_LTE|TOK_GT|TOK_GTE
;

unary_op: TOK_PLUS | TOK_MINUS | TOK_NOT | TOK_NEG | TOK_SINGLE_AND | TOK_SINGLE_OR | TOK_CARET;

exp_op: TOK_EXP;


primary: 
	number 					
	| bool_literal			
	| paren_expr
	| string
	| variable_ref_path
	| method_function_symbol_call
	| static_ref_path
	| is_super=TOK_SUPER TOK_DOT variable_ref_path
	| compile_has_expr
	| cast_expression // TODO: File Jama issue
	;
	
paren_expr:
	TOK_LPAREN expression TOK_RPAREN
;

// TODO: casting_type is undefined
cast_expression:
	TOK_LPAREN casting_type TOK_RPAREN expression
	;
	
casting_type:
	data_type
	;
	
variable_ref_path:
	hierarchical_id (TOK_LSBRACE expression (TOK_COLON expression)? TOK_RSBRACE)?
;

method_function_symbol_call:
	method_call
	| function_symbol_call
	;

// TODO: trailing TOK_SEMICOLON is incorrect
method_call:
	hierarchical_id method_parameter_list /*TOK_SEMICOLON*/
	;

// TODO: trailing TOK_SEMICOLON is incorrect
function_symbol_call:
	function_symbol_id method_parameter_list /*TOK_SEMICOLON*/
	;
	
function_symbol_id:
	function_id
	| symbol_identifier
	;

function_id:
	identifier (TOK_DOUBLE_COLON identifier)*
	;	


static_ref_path:
	is_global=TOK_DOUBLE_COLON? static_ref_path_elem (TOK_DOUBLE_COLON static_ref_path_elem)*
	;
	
static_ref_path_elem: 
	identifier template_param_value_list?
	;

mul_div_mod_op: TOK_ASTERISK | TOK_DIV | TOK_MOD;

add_sub_op: TOK_PLUS | TOK_MINUS;

// Note: Implementation difference vs spec
// shift_op: '<<' | '>>';
shift_op: TOK_DOUBLE_LT | TOK_GT TOK_GT;

eq_neq_op: TOK_DOUBLE_EQ | TOK_NE;


constant: 
	number 
	| identifier
	;
	
identifier: 
	ID 
	| ESCAPED_ID
	;
	
hierarchical_id_list:
	hierarchical_id (TOK_COMMA hierarchical_id)*
	;
	
hierarchical_id:
	hierarchical_id_elem (TOK_DOT hierarchical_id_elem)*
;

hierarchical_id_elem:
	identifier (TOK_LSBRACE expression TOK_RSBRACE)?
	;
	
action_type_identifier: type_identifier;

// == PSS 1.1
type_identifier: 
	(is_global=TOK_DOUBLE_COLON)? type_identifier_elem (TOK_DOUBLE_COLON type_identifier_elem)* 
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
	TOK_TRUE|TOK_FALSE
;


number:
	based_hex_number
	| based_dec_number
	| based_bin_number
	| based_oct_number
	| dec_number
	| oct_number
	| hex_number
;

string: DOUBLE_QUOTED_STRING | TRIPLE_DOUBLE_QUOTED_STRING;

filename_string: DOUBLE_QUOTED_STRING;

based_hex_number: DEC_LITERAL? BASED_HEX_LITERAL;

based_dec_number: DEC_LITERAL? BASED_DEC_LITERAL;

dec_number: DEC_LITERAL;

based_bin_number: DEC_LITERAL? BASED_BIN_LITERAL;

based_oct_number: DEC_LITERAL? BASED_OCT_LITERAL;


oct_number: OCT_LITERAL;

hex_number: HEX_LITERAL;


export_action:
	TOK_EXPORT (method_qualifiers)? action_type_identifier method_parameter_list_prototype TOK_SEMICOLON
;

import_class_decl:
	TOK_IMPORT TOK_CLASS import_class_identifier (import_class_extends)? TOK_LCBRACE
		import_class_method_decl*
	TOK_RCBRACE 
	;

import_class_extends:
	TOK_COLON type_identifier (TOK_COMMA type_identifier)*
;
	
import_class_method_decl:
	method_prototype TOK_SEMICOLON
;

