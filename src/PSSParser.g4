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
//	| package_declaration // Note: package_declaration is a package_body_item
//	| component_declaration // Note: ambiguous, since 'component' is also a package body item
	;

package_declaration:
	TOK_PACKAGE package_id_path TOK_LCBRACE
		package_body_item*
	TOK_RCBRACE
;

package_id_path:
	package_identifier ( TOK_DOUBLE_COLON package_identifier )*
	;

package_body_item:
	abstract_action_declaration
	| struct_declaration
	| enum_declaration
	| covergroup_declaration
	| function_decl
	| import_class_decl
	| procedural_function // FIXME
	| import_function
	| target_template_function
	| export_action
	| typedef_declaration
	| import_stmt
	| extend_stmt
	| const_field_declaration
	| component_declaration
	| package_declaration
	| compile_assert_stmt
	| package_body_compile_if
	| TOK_SEMICOLON // stmt_terminator
//	| static_const_field_declaration	
	;

import_stmt:
	TOK_IMPORT package_import_pattern TOK_SEMICOLON
;

package_import_pattern:
	type_identifier package_import_qualifier?
;

package_import_qualifier:
	package_import_wildcard
	| package_import_alias
	;

package_import_wildcard:
	TOK_DOUBLE_COLON TOK_ASTERISK
	;

package_import_alias: 
	TOK_AS package_identifier
	;

extend_stmt:
		(
			(TOK_EXTEND is_action=TOK_ACTION type_identifier TOK_LCBRACE
				action_body_item*
				TOK_RCBRACE
			) | 
			(TOK_EXTEND is_component=TOK_COMPONENT type_identifier TOK_LCBRACE
				component_body_item*
				TOK_RCBRACE
			) |
			(TOK_EXTEND struct_kind type_identifier TOK_LCBRACE
				struct_body_item*
				TOK_RCBRACE
			) |
			(TOK_EXTEND is_enum=TOK_ENUM type_identifier TOK_LCBRACE
				(enum_item (TOK_COMMA enum_item)*)?
				TOK_RCBRACE
			)
		)
;

const_field_declaration :
	TOK_STATIC? TOK_CONST data_declaration
;

/** FIXME
const_data_declaration:
	scalar_data_type const_data_instantiation (TOK_COMMA const_data_instantiation)* TOK_SEMICOLON 
;

const_data_instantiation:	
	identifier TOK_SINGLE_EQ init=constant_expression
;

static_const_field_declaration :
	TOK_STATIC TOK_CONST const_data_declaration
;
 */

/********************************************************************
 * B.2 Action declarations
 ********************************************************************/

action_declaration:
	TOK_ACTION action_identifier template_param_decl_list? action_super_spec? 
	TOK_LCBRACE
		action_body_item*
	TOK_RCBRACE 
;

/* Note: replace with a simpler form for improved performance
abstract_action_declaration :
	TOK_ABSTRACT TOK_ACTION action_identifier template_param_decl_list? action_super_spec?
	TOK_LCBRACE
		action_body_item*
	TOK_RCBRACE 
;
 */
abstract_action_declaration:
	TOK_ABSTRACT action_declaration
	;

action_super_spec:
	TOK_COLON type_identifier
;

action_body_item:
	activity_declaration
	| override_declaration
	| constraint_declaration
	| action_field_declaration
	| symbol_declaration
	| covergroup_declaration
	| exec_block_stmt
	| activity_scheduling_constraint
	| attr_group
	| compile_assert_stmt
	| covergroup_instantiation
	| action_body_compile_if
	| TOK_SEMICOLON
;

activity_declaration: 
	TOK_ACTIVITY 
	TOK_LCBRACE 
		activity_stmt* 
	TOK_RCBRACE 
	;

action_field_declaration:
	attr_field
	| activity_data_field
	// Note: This and attr_field can only be distinguished by the actual type
//	| action_handle_declaration
	| object_ref_field_declaration
;

object_ref_field_declaration:
	flow_ref_field_declaration
	| resource_ref_field_declaration
	;

flow_ref_field_declaration:
	(is_input=TOK_INPUT | is_output=TOK_OUTPUT) flow_object_type object_ref_field (TOK_COMMA object_ref_field)* TOK_SEMICOLON
	;
	
resource_ref_field_declaration:
	(lock=TOK_LOCK | share=TOK_SHARE) resource_object_type object_ref_field (TOK_COMMA object_ref_field)* TOK_SEMICOLON
	;

flow_object_type:
/* Note: refactored. All flow-object type identifiers
   are syntactically type_identifiers. Removing
   ambiguity increases performance.
	buffer_type_identifier
	| state_type_identifier
	| stream_type_identifier
 */
    type_identifier
	;

resource_object_type:
	resource_type_identifier
	;

object_ref_field:
	identifier array_dim?
	;

// NOTE: refactored grammar for improved AST
// action_handle_declaration:
// 	action_type_identifier action_instantiation TOK_SEMICOLON
// 	;

//action_instantiation:
//	action_identifier array_dim? (TOK_COMMA action_identifier array_dim?)* 
//	;

action_handle_declaration:
	action_type_identifier action_instantiation (TOK_COMMA action_instantiation)* TOK_SEMICOLON
	;

action_instantiation:
	action_identifier array_dim?
	;

activity_data_field:
	TOK_ACTION data_declaration
;

activity_scheduling_constraint:
	TOK_CONSTRAINT (is_parallel=TOK_PARALLEL | is_sequence=TOK_SEQUENCE) 
	TOK_LCBRACE
		hierarchical_id TOK_COMMA hierarchical_id (TOK_COMMA hierarchical_id)* 
	TOK_RCBRACE 
	TOK_SEMICOLON
	;

/********************************************************************
 * B.3 Struct declarations
 ********************************************************************/
struct_declaration:
	struct_kind identifier template_param_decl_list? struct_super_spec? 
	TOK_LCBRACE
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

struct_super_spec : 
	TOK_COLON type_identifier
	;

struct_body_item:
	constraint_declaration
	| attr_field
	| typedef_declaration
	| exec_block_stmt
	| attr_group
	| compile_assert_stmt
	| covergroup_declaration
	| covergroup_instantiation
	| struct_body_compile_if
    | TOK_SEMICOLON
;

/********************************************************************
 * B.4 Exec blocks
 ********************************************************************/
exec_block_stmt:
	exec_block 
	| target_code_exec_block 
	| target_file_exec_block
	| TOK_SEMICOLON
	;
	
exec_block:
	TOK_EXEC exec_kind
	TOK_LCBRACE 
		exec_stmt*
	TOK_RCBRACE 
	;

exec_kind:
	TOK_PRE_SOLVE 
	| TOK_POST_SOLVE 
	| TOK_BODY
	| TOK_HEADER
	| TOK_DECLARATION 
	| TOK_RUN_START
	| TOK_RUN_END
	| TOK_INIT_UP
	| TOK_INIT_DOWN
	| TOK_INIT
	;	

exec_stmt:
	procedural_stmt
	| exec_super_stmt
	;
	
exec_super_stmt:
	TOK_SUPER TOK_SEMICOLON
	;

target_code_exec_block:
	TOK_EXEC exec_kind language_identifier TOK_SINGLE_EQ string_literal TOK_SEMICOLON
	;

target_file_exec_block:
	TOK_EXEC TOK_FILE filename_string TOK_SINGLE_EQ string_literal TOK_SEMICOLON
	;

/********************************************************************
 * B.5 Functions
 ********************************************************************/

procedural_function:
	platform_qualifier? TOK_PURE? TOK_FUNCTION function_prototype
	TOK_LCBRACE
	procedural_stmt*
	TOK_RCBRACE
	;

function_decl:
	TOK_PURE? TOK_FUNCTION function_prototype TOK_SEMICOLON
	;

function_prototype:
	function_return_type function_identifier function_parameter_list_prototype
	;

function_return_type:
	TOK_VOID
	| data_type
	;


// TODO: refactor for performance
function_parameter_list_prototype:
	(
		(
			TOK_LPAREN (function_parameter (TOK_COMMA function_parameter)*)? TOK_RPAREN
		) | (
			is_varargs=TOK_LPAREN (function_parameter TOK_COMMA)* varargs_parameter TOK_RPAREN
		)
	)
	;

function_parameter:
	(
		function_parameter_dir? data_type identifier (TOK_SINGLE_EQ constant_expression)? 
	) | (
		(is_type=TOK_TYPE | is_ref=TOK_REF type_category | is_struct=TOK_STRUCT) identifier
	)
	;

function_parameter_dir:
	TOK_INPUT
	|TOK_OUTPUT
	|TOK_INOUT
	;

varargs_parameter:
	(data_type | is_type=TOK_TYPE | is_ref=TOK_REF type_category | is_struct=TOK_STRUCT) TOK_TRIPLE_ELIPSIS identifier
	;

/********************************************************************
 * B.6 Foreign procedural interface
 ********************************************************************/

// TODO: refactor for better performance
import_function:
	(
		(
			TOK_IMPORT platform_qualifier? language_identifier? TOK_FUNCTION type_identifier TOK_SEMICOLON
		) | (
			TOK_IMPORT platform_qualifier? language_identifier? TOK_FUNCTION function_prototype TOK_SEMICOLON
		)
	)
	;

platform_qualifier: 
	TOK_TARGET
	| TOK_SOLVE
	;

target_template_function:
	TOK_TARGET language_identifier TOK_FUNCTION function_prototype TOK_SINGLE_EQ string_literal TOK_SEMICOLON
	;

import_class_decl:
	TOK_IMPORT TOK_CLASS import_class_identifier (import_class_extends)? 
	TOK_LCBRACE
		import_class_function_decl*
	TOK_RCBRACE 
	;

import_class_extends:
	TOK_COLON type_identifier (TOK_COMMA type_identifier)*
	;
	
import_class_function_decl:
	function_prototype TOK_SEMICOLON
	;

export_action:
	TOK_EXPORT (platform_qualifier)? action_type_identifier function_parameter_list_prototype TOK_SEMICOLON
;


/********************************************************************
 * B.7 Procedural statements
 ********************************************************************/

procedural_stmt:
	procedural_sequence_block_stmt
	| procedural_assignment_stmt
	| procedural_void_function_call_stmt
	| procedural_return_stmt
	| procedural_repeat_stmt
	| procedural_foreach_stmt
	| procedural_if_else_stmt
	| procedural_match_stmt
	| procedural_break_stmt
	| procedural_continue_stmt
	| procedural_data_declaration // TODO: positioning this first causes assign to be incorrectly recognized as data_declaration
	| TOK_SEMICOLON
	;
	
procedural_sequence_block_stmt:
	TOK_SEQUENCE? 
	TOK_LCBRACE 
	    procedural_stmt*
	TOK_RCBRACE
	;

// EMPTYSTR: data_type may match empty string
procedural_data_declaration:
	data_type procedural_data_instantiation (TOK_COMMA procedural_data_instantiation)*
	;

procedural_data_instantiation:
	identifier array_dim? (TOK_SINGLE_EQ expression)?
	;

// TODO: does this assign function_call is part of expression"
procedural_assignment_stmt:
	ref_path assign_op expression TOK_SEMICOLON
	;

procedural_void_function_call_stmt:
	( TOK_LPAREN TOK_VOID TOK_RPAREN )? function_call TOK_SEMICOLON
	;

procedural_return_stmt:
	TOK_RETURN expression? TOK_SEMICOLON
	;
	
procedural_repeat_stmt:
    (
	    (is_repeat=TOK_REPEAT TOK_LPAREN (identifier TOK_COLON)? expression TOK_RPAREN procedural_stmt)
	    | (is_repeat_while=TOK_REPEAT procedural_stmt TOK_WHILE TOK_LPAREN expression TOK_RPAREN TOK_SEMICOLON)
	    | (is_while=TOK_WHILE TOK_LPAREN expression TOK_RPAREN procedural_stmt)
	)
	;

procedural_foreach_stmt:
	TOK_FOREACH TOK_LPAREN (iterator_identifier TOK_COLON)? expression 
		(TOK_LSBRACE index_identifier TOK_RSBRACE)? TOK_RPAREN procedural_stmt
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
	
procedural_break_stmt:
	TOK_BREAK TOK_SEMICOLON
	;

procedural_continue_stmt:
	TOK_CONTINUE TOK_SEMICOLON
	;
	
/********************************************************************
 * B.8 Component declarations
 ********************************************************************/
component_declaration:
	TOK_PURE? TOK_COMPONENT component_identifier template_param_decl_list?  (component_super_spec)?
	TOK_LCBRACE
		component_body_item*
	TOK_RCBRACE 
	;

component_super_spec :
	TOK_COLON type_identifier
	;

component_body_item:
	override_declaration
	| component_data_declaration
	| component_pool_declaration
	| action_declaration
	| abstract_action_declaration
	| object_bind_stmt
	| exec_block
	| struct_declaration
	| enum_declaration
	| covergroup_declaration
	| function_decl
	| import_class_decl
	| procedural_function
	| import_function
	| target_template_function
	| export_action
	| typedef_declaration
	| import_stmt
	| extend_stmt
	| compile_assert_stmt
	| attr_group
	| component_body_compile_if
 	| TOK_SEMICOLON
	;

component_data_declaration:
	access_modifier? (is_static=TOK_STATIC is_const=TOK_CONST)? data_declaration
	;

// Note: LRM only supports a single pool per declaration
// Enh: I believe we agreed to support a list
component_pool_declaration:
	TOK_POOL (TOK_LSBRACE expression TOK_RSBRACE)? type_identifier identifier TOK_SEMICOLON
	;

object_bind_stmt:
	TOK_BIND hierarchical_id object_bind_item_or_list TOK_SEMICOLON
	;

object_bind_item_or_list:
	object_bind_item_path
	| (TOK_LCBRACE object_bind_item_path (TOK_COMMA object_bind_item_path)* TOK_RCBRACE)
	;

object_bind_item_path:
	(component_path_elem TOK_DOT)* object_bind_item
	;

component_path_elem:
	component_identifier ( TOK_LSBRACE constant_expression TOK_RSBRACE )?
	;

object_bind_item:
	(action_type_identifier TOK_DOT identifier ( TOK_LSBRACE constant_expression TOK_RSBRACE )?)
	| TOK_ASTERISK
	;

/********************************************************************
 * B.9 Activity statements
 ********************************************************************/

activity_stmt: 
	activity_labeled_stmt
	| activity_data_field
	| activity_bind_stmt
	| action_handle_declaration
	| activity_constraint_stmt
	| activity_scheduling_constraint
	| TOK_SEMICOLON
	;

// Note: this deviates from LRM BNF in order to provide
// a good intercept point for adding labels
activity_labeled_stmt:
	(identifier TOK_COLON)? labeled_activity_stmt
	;

labeled_activity_stmt:
	activity_action_traversal_stmt
	| activity_sequence_block_stmt
	| activity_parallel_stmt
	| activity_schedule_stmt
	| activity_repeat_stmt
	| activity_foreach_stmt
	| activity_select_stmt
	| activity_if_else_stmt
	| activity_match_stmt
	| activity_replicate_stmt
	| activity_super_stmt
	| symbol_call
	;

// PSS Extension: inline value initialization
activity_action_traversal_stmt:
	(identifier ( TOK_LSBRACE expression TOK_RSBRACE )? inline_constraints_or_empty)
	| (is_do=TOK_DO type_identifier inline_constraints_or_empty)
	;

inline_constraints_or_empty:
	(TOK_WITH constraint_set)
	| TOK_SEMICOLON
	;

activity_sequence_block_stmt:
	(TOK_SEQUENCE)? 
	TOK_LCBRACE  
		activity_stmt* 
	TOK_RCBRACE 
	;

activity_parallel_stmt:
	TOK_PARALLEL activity_join_spec? 
	TOK_LCBRACE
		activity_stmt*
	TOK_RCBRACE 
	;

activity_schedule_stmt:
	TOK_SCHEDULE activity_join_spec? 
	TOK_LCBRACE
		activity_stmt*
	TOK_RCBRACE 
	;

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

activity_repeat_stmt:
	(
		(is_repeat=TOK_REPEAT TOK_LPAREN (loop_var=identifier TOK_COLON)? expression TOK_RPAREN activity_stmt) 
		| (is_do_while=TOK_REPEAT activity_stmt is_do_while=TOK_WHILE TOK_LPAREN expression TOK_RPAREN TOK_SEMICOLON)
	)
	;	

activity_foreach_stmt:
	TOK_FOREACH 
		TOK_LPAREN 
			(it_id=iterator_identifier)? expression (TOK_LSBRACE idx_id=index_identifier TOK_RSBRACE)? 
		TOK_RPAREN
		activity_stmt
	;

// TODO: Select should accept 1+ user-specified
// branches to account for replicate
activity_select_stmt:
	TOK_SELECT TOK_LCBRACE
//		select_branch
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

activity_if_else_stmt:
	TOK_IF TOK_LPAREN expression TOK_RPAREN activity_stmt 
	(TOK_ELSE activity_stmt)?
	;

activity_match_stmt:
	TOK_MATCH TOK_LPAREN expression TOK_RPAREN 
	TOK_LCBRACE
		match_choice
		match_choice*
	TOK_RCBRACE
	;

match_choice:
	(TOK_LSBRACE open_range_list TOK_RSBRACE TOK_COLON activity_stmt)
	| (is_default=TOK_DEFAULT TOK_COLON activity_stmt)
	;

activity_replicate_stmt:
	TOK_REPLICATE TOK_LPAREN (index_identifier TOK_COLON)? expression TOK_RPAREN 
		( identifier TOK_LSBRACE TOK_RSBRACE TOK_COLON)? 
		labeled_activity_stmt
	;

activity_super_stmt:
	TOK_SUPER TOK_SEMICOLON
	;

activity_bind_stmt:
	TOK_BIND hierarchical_id activity_bind_item_or_list TOK_SEMICOLON
	;

activity_bind_item_or_list:
	hierarchical_id 
	| (TOK_LCBRACE hierarchical_id_list TOK_RCBRACE)
	;

activity_constraint_stmt:
	TOK_CONSTRAINT constraint_set 
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

/********************************************************************
 * B.10 Overrides
 ********************************************************************/

override_declaration:
	TOK_OVERRIDE TOK_LCBRACE override_stmt* TOK_RCBRACE
	;

override_stmt:
	type_override 
	| instance_override
	| TOK_SEMICOLON
	;

type_override:
	TOK_TYPE target=type_identifier TOK_WITH override=type_identifier TOK_SEMICOLON
	;


instance_override:
	TOK_INSTANCE target=hierarchical_id TOK_WITH override=type_identifier TOK_SEMICOLON
	;

/********************************************************************
 * B.11 Data declarations
 ********************************************************************/

data_declaration:
	data_type data_instantiation (TOK_COMMA data_instantiation)* TOK_SEMICOLON 
	;

data_instantiation:
	identifier (array_dim)? (TOK_SINGLE_EQ constant_expression)?
	;

array_dim:
	TOK_LSBRACE constant_expression TOK_RSBRACE
	;

attr_field:
	access_modifier? is_rand=TOK_RAND? (is_const=TOK_STATIC TOK_CONST)? data_declaration
	;

access_modifier:
	TOK_PUBLIC 
	| TOK_PROTECTED 
	| TOK_PRIVATE
	;
	
attr_group:
	access_modifier TOK_COLON
	;

/********************************************************************
 * B.12 Template types (AST)
 ********************************************************************/

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
// Note: type_identifier doesn't cover primitive types (eg bit, int, bool)
//	TOK_TYPE identifier ( TOK_SINGLE_EQ type_identifier )?
	TOK_TYPE identifier ( TOK_SINGLE_EQ data_type )?
	;

category_type_param_decl: 
	type_category identifier ( type_restriction )? ( TOK_SINGLE_EQ type_identifier )?
	;

type_restriction: 
	TOK_COLON type_identifier
	;

type_category:
    img=TOK_ACTION
	| img=TOK_COMPONENT
	| struct_kind
	;

value_param_decl: 
	data_type identifier ( TOK_SINGLE_EQ constant_expression )?
	;

template_param_value_list: 
	TOK_LT ( template_param_value ( TOK_COMMA template_param_value )* )? TOK_GT
	;

// Note: Added to provide a non-terminal matching a templated non-global type identifier
type_identifier_templ_elem:
	identifier template_param_value_list
	;

template_param_value: 
    data_type
    | constant_expression // Note: both expression and data_type cover 'identifier'
//	scalar_data_type
//	| (is_global=TOK_DOUBLE_COLON type_identifier_elem)
//	| type_identifier_templ_elem (TOK_DOUBLE_COLON type_identifier_elem)*
//	| constant_expression
	;

/********************************************************************
 * B.13 Data types
 ********************************************************************/
data_type:
	scalar_data_type 
//	| collection_type // Note: this parser treats collection types as parameterized classes
	| reference_type
	| type_identifier
	;

scalar_data_type:
	chandle_type
	| integer_type 	
	| string_type  	
	| bool_type
	| enum_type
	;

casting_type:
	integer_type
	| bool_type
	| enum_type
	| type_identifier
	;

chandle_type:
	TOK_CHANDLE
	;

// Note: this parser considers dual-interval widths to be unsupported
integer_type:
	integer_atom_type (TOK_LSBRACE lhs=expression /*(TOK_COLON rhs=expression)?*/ TOK_RSBRACE)?
		(is_in=TOK_IN TOK_LSBRACE domain=domain_open_range_list TOK_RSBRACE)?
	;

integer_atom_type:
	TOK_INT
	| TOK_BIT
	;

domain_open_range_list:
	domain_open_range_value (TOK_COMMA domain_open_range_value)*
	;

// Note: this is slightly different from the spec to simplify parsing
domain_open_range_value:
	lhs=expression limit_mid=TOK_ELIPSIS rhs=expression
	| lhs=expression limit_high=TOK_ELIPSIS
	| (limit_low=TOK_ELIPSIS rhs=expression)
	| lhs=expression
	;

string_type: 
	TOK_STRING ( has_range=TOK_IN TOK_LSBRACE DOUBLE_QUOTED_STRING (TOK_COMMA DOUBLE_QUOTED_STRING)* TOK_RSBRACE)? 
	;

bool_type:
	TOK_BOOL
	;

enum_declaration:
  	TOK_ENUM enum_identifier 
	TOK_LCBRACE 
  		(enum_item (TOK_COMMA enum_item)*)?
	TOK_RCBRACE 
	;

enum_item:
	identifier (TOK_SINGLE_EQ constant_expression)?
	;

// Note: from a parse perspective, there is ambiguity between
// any user-defined type (enum_type_identifier) and a user-defined
// enum type
// This parser changes the BNF to only consider an enum_type to
// require the range restriction
enum_type:
//	enum_type_identifier (TOK_IN TOK_LSBRACE open_range_list TOK_RSBRACE)?
	enum_type_identifier TOK_IN TOK_LSBRACE open_range_list TOK_RSBRACE
	;

// Note: this parser treats collection types as parameterized classes
// collection_type:
// 	| (TOK_ARRAY TOK_LT data_type TOK_COMMA array_size_expression TOK_GT)
// 	| (TOK_LIST TOK_LT data_type TOK_GT)
// 	| (TOK_MAP TOK_LT data_type TOK_COMMA data_type TOK_GT)
// 	| (TOK_SET TOK_LT data_type TOK_GT)
//  ;

array_size_expression:
	constant_expression
	;

reference_type:
	TOK_REF entity_type_identifier
	;

typedef_declaration:
 	TOK_TYPEDEF data_type type_identifier TOK_SEMICOLON 
;

/********************************************************************
 * B.14 Constraints
 ********************************************************************/
constraint_declaration:
	(
		(TOK_CONSTRAINT constraint_set)
		| ((is_dynamic=TOK_DYNAMIC)? TOK_CONSTRAINT identifier constraint_block)
	)
	;

constraint_set:
	constraint_body_item
	| constraint_block
	;

constraint_block:
	TOK_LCBRACE 
		constraint_body_item* 
	TOK_RCBRACE
	;

constraint_body_item:
	expression_constraint_item
	| foreach_constraint_item
	| forall_constraint_item
	| if_constraint_item
	| implication_constraint_item
	| unique_constraint_item
	| default_constraint_item
	| TOK_SEMICOLON
;

// Note: PSS LRM uses in-line tokens for default
// constraints. ANTLR doesn't really like this.
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

expression_constraint_item:
	expression TOK_SEMICOLON
	;

foreach_constraint_item:
	TOK_FOREACH TOK_LPAREN (it_id=iterator_identifier TOK_COLON)? 
		expression (TOK_LSBRACE idx_id=index_identifier TOK_RSBRACE)? TOK_RPAREN constraint_set
	;
	
forall_constraint_item:
	TOK_FORALL TOK_LPAREN identifier TOK_COLON 
		type_identifier (TOK_IN ref_path)? TOK_RPAREN constraint_set
	;

if_constraint_item:
	TOK_IF TOK_LPAREN expression TOK_RPAREN constraint_set (TOK_ELSE constraint_set )? 
	;

implication_constraint_item:
	expression TOK_IMPLIES constraint_set
	;

unique_constraint_item:
	TOK_UNIQUE TOK_LCBRACE hierarchical_id_list TOK_RCBRACE TOK_SEMICOLON
	;

/********************************************************************
 * B.15 Coverage specification
 ********************************************************************/
covergroup_declaration:
	TOK_COVERGROUP covergroup_identifier 
		(TOK_LPAREN covergroup_port (TOK_COMMA covergroup_port)* TOK_RPAREN)? 
		TOK_LCBRACE
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
	| TOK_SEMICOLON
	;

covergroup_option:
	TOK_OPTION TOK_DOT identifier TOK_SINGLE_EQ constant_expression TOK_SEMICOLON
	;

covergroup_instantiation:
	covergroup_type_instantiation
	| inline_covergroup
	;
	
inline_covergroup:
	TOK_COVERGROUP 
	TOK_LCBRACE
		covergroup_body_item*
	TOK_RCBRACE identifier TOK_SEMICOLON
	;

covergroup_type_instantiation:
	covergroup_type_identifier covergroup_identifier
		TOK_LPAREN covergroup_portmap_list TOK_RPAREN covergroup_options_or_empty
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

covergroup_options_or_empty:
	TOK_WITH TOK_LCBRACE covergroup_option* TOK_RCBRACE
	| TOK_SEMICOLON
	;
		
covergroup_coverpoint: 
	(data_type? coverpoint_identifier TOK_COLON)? TOK_COVERPOINT 
		target=expression (TOK_IFF TOK_LPAREN iff=expression TOK_RPAREN)?
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

covergroup_coverpoint_binspec: 
	bins_keyword identifier (is_array=TOK_LSBRACE constant_expression? TOK_RSBRACE)? TOK_SINGLE_EQ coverpoint_bins
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

covergroup_expression: 
	expression
	;

covergroup_cross: 
	covercross_identifier TOK_COLON TOK_CROSS coverpoint_identifier (TOK_COMMA coverpoint_identifier)*
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

/********************************************************************
 * B.16 Conditional compilation
 ********************************************************************/
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

compile_has_expr:
    // Note: replace static_ref_path with ref_path
//	TOK_COMPILE TOK_HAS TOK_LPAREN static_ref_path TOK_RPAREN
	TOK_COMPILE TOK_HAS TOK_LPAREN ref_path TOK_RPAREN
	;
	
compile_assert_stmt :
	TOK_COMPILE TOK_ASSERT TOK_LPAREN cond=constant_expression (TOK_COMMA msg=string_literal)? TOK_RPAREN TOK_SEMICOLON
	;

/********************************************************************
 * B.17 Expressions
 ********************************************************************/

constant_expression: expression;

// Note: the ANTLR BNF diverges from the LRM here due to a need to
// capture operator precedence within the grammar

expression:
	primary                                             | 
	unary_op lhs=expression								|
	lhs=expression exp_op rhs=expression 				|
	lhs=expression mul_div_mod_op rhs=expression 		|
	lhs=expression add_sub_op rhs=expression			|
	lhs=expression shift_op rhs=expression				|
	lhs=expression in_expression						|
    lhs=expression logical_inequality_op rhs=expression	|
    lhs=expression eq_neq_op rhs=expression				|
    lhs=expression binary_and_op rhs=expression			|
    lhs=expression binary_xor_op rhs=expression			|
    lhs=expression binary_or_op rhs=expression			|
    lhs=expression logical_and_op rhs=expression		|
    lhs=expression logical_or_op rhs=expression			|
    lhs=expression conditional_expr
	;

// Replaced: unary_operator
// Replaced: binary_operator

assign_op:
	TOK_SINGLE_EQ 
	| TOK_PLUS_EQ 
	| TOK_MINUS_EQ 
	| TOK_SHL_EQ 
	| TOK_SHR_EQ 
	| TOK_OR_EQ 
	| TOK_AND_EQ
	;

conditional_expr :
	TOK_COND true_expr=expression TOK_COLON false_expr=expression
	; 

logical_or_op : TOK_DOUBLE_OR;
logical_and_op : TOK_DOUBLE_AND;
binary_or_op : TOK_SINGLE_OR;
binary_xor_op : TOK_CARET;
binary_and_op : TOK_SINGLE_AND;

logical_inequality_op:
	TOK_LT
	| TOK_LTE	
	| TOK_GT
	| TOK_GTE
	;

unary_op: 
	TOK_PLUS 
	| TOK_MINUS 
	| TOK_NOT 
	| TOK_NEG 
	| TOK_SINGLE_AND 
	| TOK_SINGLE_OR 
	| TOK_CARET
	;

exp_op: 
	TOK_EXP
	;

mul_div_mod_op: 
	TOK_ASTERISK 
	| TOK_DIV 
	| TOK_MOD
	;

add_sub_op: 
	TOK_PLUS 
	| TOK_MINUS
	;

// Note: Implementation difference vs spec
// shift_op: '<<' | '>>';
shift_op: 
	TOK_DOUBLE_LT 
	| TOK_GT TOK_GT
	;

eq_neq_op: 
	TOK_DOUBLE_EQ 
	| TOK_NE
	;

in_expression:
	(TOK_IN TOK_LSBRACE open_range_list TOK_RSBRACE)
	| (TOK_IN collection_expression) 
	;

open_range_list:
	open_range_value (TOK_COMMA open_range_value)*
	;

open_range_value:
	lhs=expression (TOK_ELIPSIS rhs=expression)?
	;

collection_expression:
	expression
	;

primary: 
	number 					
	| ref_path
	| aggregate_literal
	| bool_literal
	| string_literal
	| null_ref
	| paren_expr
	| cast_expression
	| compile_has_expr
	;


//	| method_function_symbol_call
//	| static_ref_path
//	| is_super=TOK_SUPER TOK_DOT variable_ref_path
//	;
	
paren_expr:
	TOK_LPAREN expression TOK_RPAREN
	;

cast_expression:
	TOK_LPAREN casting_type TOK_RPAREN expression
	;
	
//ref_path:
////	(static_ref_path (TOK_DOT hierarchical_id)? bit_slice?)
////	| ( (TOK_SUPER TOK_DOT)? hierarchical_id bit_slice?)
//    (static_ref_path bit_slice?)
//    | (TOK_SUPER TOK_DOT hierarchical_id bit_slice?)
//	;

//hierarchical_id:
//	member_path_elem (TOK_DOT member_path_elem)*
//	;
//type_identifier_elem:
//	identifier template_param_value_list?
//	;
//member_path_elem:
//	identifier function_parameter_list? ( TOK_LSBRACE expression TOK_RSBRACE )?
//	;

// At minimum, this is an identifier

static_ref_path_prefix:
        (type_identifier_elem TOK_DOUBLE_COLON)
        | is_global=TOK_DOUBLE_COLON
        ;

static_ref_path:
        static_ref_path_prefix (type_identifier_elem TOK_DOUBLE_COLON )* member_path_elem
        ;

ref_path:
        static_ref_path ( TOK_DOT hierarchical_id )? bit_slice?
        | (is_super=TOK_SUPER TOK_DOT)? hierarchical_id bit_slice?
        ;

//static_ref_path:
////	is_global=TOK_DOUBLE_COLON? (type_identifier_elem TOK_DOUBLE_COLON)* member_path_elem
//	is_global=TOK_DOUBLE_COLON? (type_identifier_elem TOK_DOUBLE_COLON)* hierarchical_id
//	;

bit_slice:
	TOK_LSBRACE constant_expression TOK_COLON constant_expression TOK_RSBRACE
	;

function_call:
	(TOK_SUPER TOK_DOT function_ref_path)
	| (is_global=TOK_DOUBLE_COLON? (type_identifier_elem TOK_DOUBLE_COLON)* function_ref_path)
	;

function_ref_path:
	(member_path_elem TOK_DOT)* identifier function_parameter_list
	;

symbol_call:
	symbol_identifier function_parameter_list TOK_SEMICOLON
	;

function_parameter_list:
	TOK_LPAREN ( expression ( TOK_COMMA expression )* )? TOK_RPAREN
	;

/********************************************************************
 * B.18 Identifiers
 ********************************************************************/

identifier: 
	ID 
	| ESCAPED_ID
	;
	
hierarchical_id_list:
	hierarchical_id (TOK_COMMA hierarchical_id)*
	;
	
hierarchical_id:
	member_path_elem (TOK_DOT member_path_elem)*
	;

member_path_elem:
	identifier function_parameter_list? ( TOK_LSBRACE expression TOK_RSBRACE )?
	;


action_identifier: identifier;
component_identifier: identifier;
covercross_identifier: identifier;
covergroup_identifier: identifier;
coverpoint_identifier: identifier;
enum_identifier: identifier;
function_identifier: identifier;
import_class_identifier: identifier;
index_identifier: identifier;
iterator_identifier: identifier;
label_identifier: identifier;
language_identifier: identifier;
package_identifier: identifier;
struct_identifier: identifier;
symbol_identifier: identifier;

type_identifier: 
	(is_global=TOK_DOUBLE_COLON)? type_identifier_elem (TOK_DOUBLE_COLON type_identifier_elem)* 
	;
	
type_identifier_elem:
	identifier template_param_value_list?
	;

action_type_identifier: type_identifier;
buffer_type_identifier: type_identifier;
component_type_identifier: type_identifier; // Note: unused
covergroup_type_identifier: type_identifier;
enum_type_identifier: type_identifier;
resource_type_identifier: type_identifier;
state_type_identifier: type_identifier;
stream_type_identifier: type_identifier;

entity_type_identifier:
	action_type_identifier
	| component_type_identifier
	| flow_object_type
	| resource_object_type
	;

/********************************************************************
 * B.19 Numbers and literals
 ********************************************************************/

number:
	based_hex_number
	| based_dec_number
	| based_bin_number
	| based_oct_number
	| dec_number
	| oct_number
	| hex_number
	;

oct_number: OCT_LITERAL;

dec_number: DEC_LITERAL;

hex_number: HEX_LITERAL;

based_bin_number: DEC_LITERAL? BASED_BIN_LITERAL;

based_oct_number: DEC_LITERAL? BASED_OCT_LITERAL;

based_dec_number: DEC_LITERAL? BASED_DEC_LITERAL;

based_hex_number: DEC_LITERAL? BASED_HEX_LITERAL;

aggregate_literal:
	empty_aggregate_literal
	| value_list_literal
	| map_literal
	| struct_literal
	;

empty_aggregate_literal:
	TOK_LCBRACE TOK_RCBRACE
	;

value_list_literal:
	TOK_LCBRACE expression (TOK_COMMA expression)* TOK_RCBRACE
	;

map_literal:
	TOK_LCBRACE map_literal_item ( TOK_COMMA map_literal_item )* TOK_RCBRACE
	;

map_literal_item:
	expression TOK_COLON expression
	;

struct_literal:
	TOK_LCBRACE struct_literal_item (TOK_COMMA struct_literal_item)* TOK_RCBRACE
	;

struct_literal_item:
	TOK_DOT identifier TOK_SINGLE_EQ expression
	;

bool_literal:
	TOK_TRUE
	| TOK_FALSE
	;

null_ref:
	TOK_NULL
	;

/********************************************************************
 * B.20 Additional lexical conventions
 ********************************************************************/

string_literal: 
	DOUBLE_QUOTED_STRING 
	| TRIPLE_DOUBLE_QUOTED_STRING;

filename_string: DOUBLE_QUOTED_STRING;


