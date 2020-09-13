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
grammar PSSParser;

compilation_unit : 
	portable_stimulus_description* EOF
	;

portable_stimulus_description : 
/*	package_body_item 
	|*/ package_declaration
	| component_declaration
	;

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

// NOTE: refactored grammar
action_handle_declaration:
	action_type_identifier action_instantiation (',' action_instantiation)* ';'
	;
	
action_instantiation:
	action_identifier array_dim?
	;
	
//action_instantiation:
//	ids+=action_identifier (array_dim)? (',' ids+=action_identifier (array_dim)? )*
//	;


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
	target_file_exec_block
	| exec_block 
	| target_code_exec_block 
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

function_decl:
	'function' method_prototype ';'
;

method_prototype:
	method_return_type method_identifier method_parameter_list_prototype
;

method_return_type:
	'void'
	| data_type
;

method_parameter_list_prototype: 
	'('
		(
			method_parameter (',' method_parameter)*
		)?
	')'
;

method_parameter:
	method_parameter_dir? data_type identifier
;

method_parameter_dir:
	'input'
	|'output'
	|'inout'
;

function_qualifiers:
	('import' import_function_qualifiers? 'function' type_identifier ';')
	| ('import' import_function_qualifiers? 'function' method_prototype ';')
	;
	
import_function_qualifiers:
	method_qualifiers (language_identifier)? 
	| language_identifier
;

method_qualifiers: 
	'target'
	| 'solve'
;

target_template_function:
	'target' language_identifier 'function' method_prototype '=' string ';'
	;

// TODO: method_parameter_list appears unused	
method_parameter_list: 
	'(' (expression (',' expression)*)? ')'
;

// >>= PSS 1.1
pss_function_defn:
	method_qualifiers? 'function' method_prototype '{' procedural_stmt* '}'
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
	| ';' // TODO: need to incorporate
	;
	
procedural_block_stmt:
	('sequence')? '{' procedural_stmt* '}'
	;
	
procedural_var_decl_stmt:
	data_declaration
	;
	
procedural_expr_stmt:
	(expression ';')
	| (variable_ref_path assign_op expression ';')
	;
	
procedural_return_stmt:
	'return' expression? ';'
	;
	
procedural_if_else_stmt:
	'if' '(' expression ')' procedural_stmt ( 'else' procedural_stmt )?
	;
	
procedural_match_stmt:
	'match' '(' expression ')' '{' procedural_match_choice procedural_match_choice* '}'
	;

procedural_match_choice:
	('[' open_range_list ']' ':' procedural_stmt)
	| ('default' ':' procedural_stmt)
	;

procedural_repeat_stmt:
	(is_while='while' '(' expression ')' procedural_stmt)
	| (is_repeat='repeat' '(' (identifier ':')? expression ')' procedural_stmt)
	| (is_repeat_while='repeat' procedural_stmt 'while' '(' expression ')' ';')
	;
	
procedural_foreach_stmt:
	'foreach' '(' (iterator_identifier ':')? expression ('[' index_identifier ']')? ')' procedural_stmt
	;
	
procedural_break_stmt:
	'break' ';'
	;

procedural_continue_stmt:
	'continue' ';'
	;
	
// <<= PSS 1.1

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
	(is_static='static' is_const='const')? data_declaration
;

component_pool_declaration:
	'pool' ('[' expression ']')? type_identifier identifier (',' identifier)* ';'
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

activity_stmt: 
	(identifier ':')? labeled_activity_stmt
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
	| ';'
// <<= PSS 1.1
;

activity_if_else_stmt:
	'if' '(' expression ')' activity_stmt 
	('else' activity_stmt)?
;

activity_repeat_stmt:
	 (
		(is_while='while' '(' expression ')' activity_stmt) |
		(is_repeat='repeat' '(' (loop_var=identifier ':')? expression ')' activity_stmt) |
		(is_do_while='repeat' activity_stmt is_do_while='while' '(' expression ')' ';')
		)
;

activity_replicate_stmt:
	'replicate' '(' (index_identifier ':')? expression ')' ( identifier '[' ']' ':')? 
		labeled_activity_stmt
	;

activity_sequence_block_stmt:
	('sequence')? '{'  activity_stmt* '}' 
;

activity_constraint_stmt:
	'constraint' constraint_set 
;

activity_foreach_stmt:
	'foreach' '(' (it_id=iterator_identifier)? expression ('[' idx_id=index_identifier ']')? ')'
		activity_stmt
;

activity_action_traversal_stmt:
	(identifier ('[' expression ']')? ';')
	| (identifier ('[' expression ']')? 'with' constraint_set)
	| (is_do='do' type_identifier ';')
	| (is_do='do' type_identifier 'with' constraint_set)
;

activity_select_stmt:
	'select' '{'
		select_branch
		select_branch
		select_branch*
	'}'
;

select_branch:
	(
		('(' guard=expression ')' ('[' weight=expression ']')? ':') 
		| ('[' weight=expression ']' ':')
	)? activity_stmt
	;

activity_match_stmt:
	'match' '(' expression ')' '{'
		match_choice
		match_choice
		match_choice*
	'}'
	;
	
match_choice:
	('[' open_range_list ']' ':' activity_stmt)
	| (is_default='default' ':' activity_stmt)
	;
	
activity_parallel_stmt:
	 'parallel' activity_join_spec? '{'
		activity_stmt*
	'}' 
;

activity_schedule_stmt:
	 'schedule' activity_join_spec? '{'
		activity_stmt*
	'}' 
;

// >>= PSS 1.1
activity_join_spec:
	activity_join_branch_spec
	| activity_join_select_spec
	| activity_join_none_spec
	| activity_join_first_spec
	;
	
activity_join_branch_spec:
	'join_branch' '(' label_identifier (',' label_identifier)* ')'
	;
	
activity_join_select_spec:
	'join_select' '(' expression ')'
	;
	
activity_join_none_spec:
	'join_none'
	;
	
activity_join_first_spec:
	'join_first' '(' expression ')'
	;
	
// <<= PSS 1.1

activity_bind_stmt:
	'bind' hierarchical_id activity_bind_item_or_list ';'
;

activity_bind_item_or_list:
	hierarchical_id 
	| ('{' hierarchical_id (',' hierarchical_id)* '}')
;

symbol_declaration:
	'symbol' identifier ('(' symbol_paramlist ')')? '{' activity_stmt* '}'
;

symbol_paramlist:
	 (symbol_param (',' symbol_param)*)?
;

symbol_param:
	data_type identifier
;

activity_super_stmt:
	'super' ';'
	;

overrides_declaration:
	 'override' '{' override_stmt* '}'
;

override_stmt:
	type_override 
	| instance_override
// >>= PSS 1.1
	| ';'
// <<= PSS 1.1
;

type_override:
	'type' target=type_identifier 'with' override=type_identifier ';'
;


instance_override:
	'instance' target=hierarchical_id 'with' override=type_identifier ';'
;


data_declaration:
	data_type data_instantiation (',' data_instantiation)* ';' 
;

data_instantiation:
	identifier (array_dim)? ('=' constant_expression)?
	;

/*	
covergroup_portmap_list:
	(
		// Name-mapped port binding
		(covergroup_portmap (',' covergroup_portmap)*) 
		// Positional port binding
		| (hierarchical_id (',' hierarchical_id)*)
	)?
;

covergroup_portmap:
	'.' identifier '(' hierarchical_id ')'
;
 */

array_dim:
	 '[' constant_expression ']'
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
	| ('array' '<' container_elem_type ',' array_size_expression '>')
	| ('list' '<' container_elem_type '>')
	| ('map' '<' container_key_type ',' container_elem_type '>')
	| ('set' '<' container_key_type '>')
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
	 'chandle'
;

integer_type:
	integer_atom_type ('[' lhs=expression (':' rhs=expression)? ']')?
		(is_in='in' '[' domain=domain_open_range_list ']')?
;

integer_atom_type:
	'int'
	| 'bit'
;

domain_open_range_list:
	domain_open_range_value (',' domain_open_range_value)*
;

domain_open_range_value:
	lhs=expression (limit_high='..' (rhs=expression)?)?
	| lhs=expression limit_high='..'
	| (limit_low='..' rhs=expression)
	| lhs=expression
;

string_type: 'string' ( 'in' '[' DOUBLE_QUOTED_STRING (',' DOUBLE_QUOTED_STRING)* ']')? 
;  

bool_type:
	 'bool'
;

user_defined_datatype:
	type_identifier
;

enum_declaration:
  	'enum' enum_identifier '{' 
  		(enum_item (',' enum_item)*)?
  		'}' 
  ;
  
enum_item:
	identifier ('=' constant_expression)?
;

enum_type:
	enum_type_identifier ('in' '[' open_range_list ']')?
;

enum_type_identifier:
	type_identifier
	;
	
typedef_declaration:
 	'typedef' data_type type_identifier ';' 
;

// >>= PSS-1.1

template_param_decl_list: 
	'<' template_param_decl ( ',' template_param_decl )* '>'
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
	'type' identifier ( '=' type_identifier )?
	;

category_type_param_decl: 
	type_category identifier ( type_restriction )? ( '=' type_identifier )?
	;

type_restriction: 
	':' type_identifier
	;

type_category:
    'action'
  | 'component'
  | struct_kind
  ;

value_param_decl: 
	data_type identifier ( '=' constant_expression )?
	;

template_param_value_list: 
	'<' ( template_param_value ( ',' template_param_value )* )? '>'
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
		((is_dynamic='dynamic')? 'constraint' identifier '{' constraint_body_item* '}' ) 
		| ('constraint' constraint_set )
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
	| ';'
// <<= PSS 1.1
;

// >>= PSS 1.1
default_constraint_item:
	default_constraint
	| default_disable_constraint
	;
	
default_constraint:
	'default' hierarchical_id '==' constant_expression ';'
	;

default_disable_constraint:
	'default' 'disable' hierarchical_id ';'
	;	
	
forall_constraint_item:
	'forall' '(' identifier ':' type_identifier ('in' variable_ref_path)? ')' constraint_set
	;
// <<= PSS 1.1

expression_constraint_item:
	expression ';'
;

implication_constraint_item:
	expression '->' constraint_set
;

constraint_set:
	constraint_body_item | 
	constraint_block
;

constraint_block:
	 '{' constraint_body_item* '}'
;

foreach_constraint_item:
	'foreach' '(' (it_id=iterator_identifier ':')? expression ('[' idx_id=index_identifier ']')? ')' constraint_set
;

if_constraint_item:
	'if' '(' expression ')' constraint_set ('else' constraint_set )? 
;

unique_constraint_item:
	'unique' '{' hierarchical_id_list '}' ';'
;

single_stmt_constraint:
	expression_constraint_item |
	unique_constraint_item
;


covergroup_declaration:
	'covergroup' name=covergroup_identifier ('(' covergroup_port (',' covergroup_port)* ')')? '{'
		covergroup_body_item*
	'}' 
;

covergroup_port:
	data_type identifier
;

covergroup_body_item:
	covergroup_option
	| covergroup_coverpoint
	| covergroup_cross
// >>= PSS 1.1
	| ';'
// <<= PSS 1.1
;

covergroup_option:
	'option' '.' identifier '=' constant_expression ';'
;

covergroup_instantiation:
	covergroup_type_instantiation
	| inline_covergroup
	;
	
inline_covergroup:
	'covergroup' '{'
		covergroup_body_item*
	'}' identifier ';'
;

covergroup_type_instantiation:
	covergroup_type_identifier covergroup_identifier
	'(' covergroup_portmap_list ')' ('with' '{' (covergroup_option)? '}')? ';'
	;
	
covergroup_portmap_list:
	(
		(covergroup_portmap (',' covergroup_portmap)?)
		| hierarchical_id_list
	)
	;
	
covergroup_portmap:
	'.' identifier '(' hierarchical_id ')'
	;
		
covergroup_coverpoint: 
		(data_type? coverpoint_identifier ':')? 'coverpoint' target=expression ('iff' '(' iff=expression ')')?
			bins_or_empty
;

bins_or_empty:
		('{' covergroup_coverpoint_body_item* '}' ) 
		| ';'
;

covergroup_coverpoint_body_item:
	covergroup_option
	| covergroup_coverpoint_binspec
;

covergroup_coverpoint_binspec: (
		(bins_keyword identifier (is_array='['constant_expression? ']')? '=' coverpoint_bins)
	)
;

coverpoint_bins:
	(
		('[' covergroup_range_list ']' ('with' '(' covergroup_expression ')')? ';')
		| (coverpoint_identifier 'with' '(' covergroup_expression ')' ';')
		| is_default='default' ';'
	)
;

covergroup_range_list:
	covergroup_value_range (',' covergroup_value_range)*
	;

covergroup_value_range:
	expression
	| (expression '..' expression?)
	| (expression?	'..' expression)
	;

bins_keyword:
	'bins' 
	| 'illegal_bins' 
	| 'ignore_bins' 
;

covergroup_cross: 
	identifier ':' 'cross' coverpoint_identifier (',' coverpoint_identifier)*
		('iff' '(' iff=expression ')')? cross_item_or_null
;

cross_item_or_null:
	('{' covergroup_cross_body_item* '}' )
	| ';'
;

covergroup_cross_body_item:
	covergroup_option
	| covergroup_cross_binspec
	;
	

covergroup_cross_binspec:
	bins_type=bins_keyword name=identifier  
		'=' covercross_identifier 'with' '(' expr=covergroup_expression ')' ';'
	;

// TODO: no definition in the BNF	
covergroup_expression:
	expression
	;
	
	
package_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=package_body_compile_if_item
	('else' false_body=package_body_compile_if_item)?
;

package_body_compile_if_item:
	package_body_item
	| ('{' package_body_item* '}')
;

action_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=action_body_compile_if_item
	('else' false_body=action_body_compile_if_item)?
;

action_body_compile_if_item:
	action_body_item
	| ('{' action_body_item* '}')
;

component_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=component_body_compile_if_item
	('else' false_body=component_body_compile_if_item)?
;

component_body_compile_if_item:
	component_body_item
	| ('{' component_body_item* '}')
	;
	
struct_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=struct_body_compile_if_item
	('else' false_body=struct_body_compile_if_item)?
;

struct_body_compile_if_item:
	struct_body_item
	| ('{' struct_body_item* '}')
;

// == PSS 1.1 -- replace static_ref with static_ref_path
compile_has_expr:
	'compile' 'has' '(' static_ref_path ')'
	;
	
compile_assert_stmt :
	'compile' 'assert' '(' cond=constant_expression (',' msg=string)? ')' ';'
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
	'?' true_expr=expression ':' false_expr=expression
	; 

logical_or_op : '||';
logical_and_op : '&&';
binary_or_op : '|';
binary_xor_op : '^';
binary_and_op : '&';

inside_expr_term :
	'in' '[' open_range_list ']'
;

open_range_list:
	open_range_value (',' open_range_value)*
;

open_range_value:
	lhs=expression ('..' rhs=expression)?
;

logical_inequality_op:
	'<'|'<='|'>'|'>='
;

unary_op: '+' | '-' | '!' | '~' | '&' | '|' | '^';

exp_op: '**';


primary: 
	number 					
	| bool_literal			
	| paren_expr
	| string
	| variable_ref_path
	| method_function_symbol_call
	| static_ref_path
	| is_super='super' '.' variable_ref_path
	| compile_has_expr
	| cast_expression // TODO: File Jama issue
	;
	
paren_expr:
	'(' expression ')'
;

// TODO: casting_type is undefined
cast_expression:
	'(' casting_type ')' expression
	;
	
casting_type:
	data_type
	;
	
variable_ref_path:
	hierarchical_id ('[' expression (':' expression)? ']')?
;

method_function_symbol_call:
	method_call
	| function_symbol_call
	;

// TODO: trailing ';' is incorrect
method_call:
	hierarchical_id method_parameter_list /*';'*/
	;

// TODO: trailing ';' is incorrect
function_symbol_call:
	function_symbol_id method_parameter_list /*';'*/
	;
	
function_symbol_id:
	function_id
	| symbol_identifier
	;

function_id:
	identifier ('::' identifier)*
	;	


static_ref_path:
	is_global='::'? static_ref_path_elem ('::' static_ref_path_elem)*
	;
	
static_ref_path_elem: 
	identifier template_param_value_list?
	;

mul_div_mod_op: '*' | '/' | '%';

add_sub_op: '+' | '-';

// Note: Implementation difference vs spec
// shift_op: '<<' | '>>';
shift_op: '<<' | '>' '>';

eq_neq_op: '==' | '!=';


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


number:
	based_hex_number
	| based_dec_number
	| based_bin_number
	| based_oct_number
	| dec_number
	| oct_number
	| hex_number
;

based_hex_number: DEC_LITERAL? BASED_HEX_LITERAL;
BASED_HEX_LITERAL: '\'' ('s'|'S')? ('h'|'H') ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;

based_dec_number: DEC_LITERAL? BASED_DEC_LITERAL;
BASED_DEC_LITERAL: '\'' ('s'|'S')? ('d'|'D') ('0'..'9') ('0'..'9'|'_')*;

dec_number: DEC_LITERAL;
DEC_LITERAL: ('1'..'9') ('0'..'9'|'_')*;

based_bin_number: DEC_LITERAL? BASED_BIN_LITERAL;
BASED_BIN_LITERAL: '\'' ('s'|'S')? ('b'|'B') (('0'..'1') ('0'..'1'|'_')*);

based_oct_number: DEC_LITERAL? BASED_OCT_LITERAL;
BASED_OCT_LITERAL: '\'' ('s'|'S')? ('o'|'O') (('0'..'7') ('0'..'7'|'_')*);


oct_number: OCT_LITERAL;
OCT_LITERAL: '0' ('0'..'7')*;

hex_number: HEX_LITERAL;
HEX_LITERAL: '0x' ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;


WS : [ \t\n\r]+ -> channel (HIDDEN) ;
//WS : [ \t\n\r]+ -> skip;

/**
 * BNF: SL_COMMENT ::= <kw>//</kw>\n 
 */
SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> channel (HIDDEN) ;
//SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> skip;

/*
 * BNF: ML_COMMENT ::= <kw>/*</kw><kw>*\057</kw>
 */
ML_COMMENT	: '/*' .*? '*/' -> channel (HIDDEN) ;
//ML_COMMENT	: '/*' .*? '*/' -> skip;
 
string: DOUBLE_QUOTED_STRING | TRIPLE_DOUBLE_QUOTED_STRING;

filename_string: DOUBLE_QUOTED_STRING;

DOUBLE_QUOTED_STRING	: '"' (~ [\n\r])* '"' ;

// TODO: unescaped_character, escaped_character

/**
 * BNF: TRIPLE_DOUBLE_QUOTED_STRING ::= <kw>"""</kw><kw>"""</kw>
 */
TRIPLE_DOUBLE_QUOTED_STRING:
			'"""' TripleQuotedStringPart*? '"""'
		; 
		
fragment TripleQuotedStringPart : EscapedTripleQuote | SourceCharacter;
fragment EscapedTripleQuote: '\\"""';
fragment SourceCharacter :[\u0009\u000A\u000D\u0020-\uFFFF];
		
// TODO: move to LexicalRules
ID : [a-zA-Z_] [a-zA-Z0-9_]* ;

ESCAPED_ID : '\\' ('\u0021'..'\u007E')+ ~ [ \r\t\n]* ;


export_action:
	'export' (method_qualifiers)? action_type_identifier method_parameter_list_prototype ';'
;

import_class_decl:
	'import' 'class' import_class_identifier (import_class_extends)? '{'
		import_class_method_decl*
	'}' 
	;

import_class_extends:
	':' type_identifier (',' type_identifier)*
;
	
import_class_method_decl:
	method_prototype ';'
;

