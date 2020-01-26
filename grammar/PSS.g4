/****************************************************************************
 *
 * Copyright 2016-2018 Matthew Ballance
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 ****************************************************************************/

grammar PSS;
	
model : 
	portable_stimulus_description* EOF
	;

portable_stimulus_description : 
	package_body_item
	| package_declaration
	| component_declaration
	;
	
package_declaration:
	'package' name=package_identifier '{'
		package_body_item*
	'}'	
;	

null_stmt: ';';

package_action_component_body_item:
	abstract_action_declaration
	| struct_declaration
	| enum_declaration
	| covergroup_declaration
	| function_decl
	| import_class_decl
	| import_method_qualifiers
	| export_action
	| typedef_declaration
	| import_stmt
	| extend_stmt
	| static_const_field_declaration	
	| compile_assert_stmt
	| null_stmt
;

package_body_item:
	package_action_component_body_item
	| const_field_declaration
	| package_body_compile_if
	;

const_field_declaration :
	'const' const_data_declaration
;

static_const_field_declaration :
	'static' 'const' const_data_declaration
;

const_data_declaration:
	scalar_data_type const_data_instantiation (',' const_data_instantiation)* ';' 
;

const_data_instantiation:	
	identifier '=' init=constant_expression
;

extend_stmt:
		(
			('extend' ext_type='action' type_identifier '{'
				action_body_item*
				'}' 
			) | 
			('extend' struct_kind type_identifier '{'
				struct_body_item*
				'}' 
			) |
			('extend' ext_type='enum' type_identifier '{'
				(enum_item (',' enum_item)*)?
				'}' 
			) |
			('extend' ext_type='component' type_identifier '{'
				component_body_item*
				'}' 
			)
		)
;

import_stmt:
	'import' package_import_pattern ';'
;

package_import_pattern:
	type_identifier ('::' wildcard='*')?
;

/****************************************************************************
 * H1: Action Declarations
 ****************************************************************************/
action_declaration:
	'action' action_identifier (action_super_spec)? 
	'{'
		action_body_item*
	'}' 
;


abstract_action_declaration :
	'abstract' 'action' action_identifier (action_super_spec)?
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
	| scheduling_constraint
	| static_const_field_declaration
	| action_body_compile_if
	| compile_assert_stmt
	| attr_field
	| attr_group
	| inline_covergroup
	| null_stmt
;

activity_declaration: 'activity' '{' activity_stmt* '}'  ;

attr_field:
	access_modifier? rand='rand'? declaration=data_declaration
;

attr_group:
	access_modifier ':'
	;

action_field_declaration:
	object_ref_field
	| activity_data_field
;

sub_action_field:
	type_identifier identifier array_dim? ';'
	;
	
object_ref_field:
	flow_ref_field
	| resource_ref_field
	;


flow_ref_field:
	(is_input='input' | is_output='output') type_identifier identifier (',' identifier)* ';'
	;
	
resource_ref_field:
	(lock='lock' | share='share') type_identifier identifier (',' identifier)* ';'
	;

activity_data_field:
	'action' data_declaration
;

scheduling_constraint:
	'constraint' (is_parallel='parallel' | is_sequence='sequence') '{'
		variable_ref_path ',' variable_ref_path (',' variable_ref_path)* '}'
	;

/****************************************************************************
 * H2: Exec Blocks
 ****************************************************************************/
exec_block_stmt:
	exec_block |
	target_code_exec_block |
	target_file_exec_block
	;
	
exec_block:
	'exec' exec_kind_identifier '{' exec_body_stmt* '}'
;

exec_kind_identifier:
	'pre_solve' |
	'post_solve' |
	'body' |
	'header' |
	'declaration' |
	'run_start' |
	'run_end' |
	'init'
;	

target_code_exec_block:
	'exec' exec_kind_identifier language_identifier '=' string ';'
;

target_file_exec_block:
	'exec' 'file' filename_string '=' string ';'
;

assign_op:
	'=' | '+=' | '-=' | '<<=' | '>>=' | '|=' | '&='
;

exec_body_stmt:
	expression (assign_op expression)? ';'
	| null_stmt
;

/****************************************************************************
 * H1: Struct Declarations
 ****************************************************************************/
struct_declaration: struct_kind identifier (struct_super_spec)? '{'
		struct_body_item*
	'}' 
;

struct_kind:
	(img='struct' | img='buffer' | img='stream' | img='state' | (img='resource' ('[' constant_expression ']')?))
;

struct_super_spec : ':' type_identifier
;

struct_body_item:
	constraint_declaration
	| attr_field
	| attr_group
	| typedef_declaration
	| covergroup_declaration
	| exec_block_stmt
	| static_const_field_declaration
	| struct_body_compile_if
	| compile_assert_stmt
	| inline_covergroup
	| null_stmt
;

access_modifier:
	'public' | 'protected' | 'private'
	;


/****************************************************************************
 * H1: Procedural Interface
 ****************************************************************************/
function_decl:
	'function' method_prototype ';'
;

method_prototype:
	method_return_type method_identifier method_parameter_list_prototype
;

method_parameter_list_prototype: 
	'('
		(
			method_parameter (',' method_parameter)*
		)?
	')'
;

method_parameter_list: 
	'('
	(
		expression (',' expression)*
	)?
	')'
;

// Method qualifiers
import_method_qualifiers:
	import_method_phase_qualifiers |
	import_method_target_template
	;

import_method_phase_qualifiers:
	'import' import_function_qualifiers 'function' type_identifier ';'
;

// TODO: must refer to an explicit target
import_method_target_template:
	'target' language_identifier 'function' 'void' type_identifier method_parameter_list_prototype '=' target_template=string ';'
//	method_return_type method_identifier method_parameter_list_prototype
//	'target' language_identifier 'function' method_prototype '=' string ';'
;

import_function_qualifiers:
	(method_qualifiers (language_identifier)?) |
	language_identifier
;

method_qualifiers: 
	('target'|'solve')
;

method_return_type:
	'void'|data_type
;

method_parameter:
	method_parameter_dir? data_type identifier
;

method_parameter_dir:
	('input'|'output'|'inout')
;

/****************************************************************************
 * H2: Import Class Declaration
 ****************************************************************************/
import_class_decl:
	'import' 'class' import_class_identifier (import_class_extends)? '{'
		import_class_method_decl*
	'}' 
	;
	
import_class_method_decl:
	method_prototype ';'
;

import_class_extends:
	':' type_identifier (',' type_identifier)*
;

/****************************************************************************
 * H2: Export Action
 ****************************************************************************/
export_action:
	'export' (method_qualifiers)? action_type_identifier method_parameter_list_prototype ';'
;

/****************************************************************************
 * H1: Component Declaration
 ****************************************************************************/
component_declaration:
	'component' component_identifier (component_super_spec)? '{'
	component_body_item*
	'}' 
;

component_super_spec :
	':' type_identifier
;

component_body_item:
	overrides_declaration
	| attr_field
	| attr_group
	| component_pool_declaration
	| action_declaration
	| object_bind_stmt
	| exec_block
	| package_action_component_body_item
	| component_body_compile_if
	| compile_assert_stmt
	| null_stmt
;

component_field_declaration:
	component_data_declaration |
	component_pool_declaration
;

component_data_declaration:
	data_declaration
;

component_pool_declaration:
	'pool' ('[' expression ']')? data_declaration
;

component_field_modifier:
	('pool')
;

object_bind_stmt:
	'bind' hierarchical_id object_bind_item_or_list ';'
;

object_bind_item_or_list:
	component_path | '{' component_path (',' component_path)* '}'
;

component_path:
	 (component_identifier ('.' component_path_elem)*) |
	is_wildcard='*'
; 

component_path_elem:
	component_action_identifier|is_wildcard='*'
;

/********************************************************************
 * H1: Activity-Graph Statements
 ********************************************************************/
activity_stmt: 
	labeled_activity_stmt
	| activity_labeled_stmt
	| activity_constraint_stmt
	| activity_bind_stmt
	| activity_data_field
	| sub_action_field
	| activity_null_stmt
;

activity_labeled_stmt:
	identifier ':' labeled_activity_stmt
	;

labeled_activity_stmt:
	activity_if_else_stmt
	| activity_repeat_stmt
	| activity_foreach_stmt
	| activity_sequence_block_stmt
	| activity_select_stmt
	| activity_match_stmt
	| activity_parallel_stmt
	| activity_schedule_stmt
	| activity_action_traversal_stmt
	| activity_super_stmt
;

activity_null_stmt:
	';'
	;

activity_super_stmt:
	'super' ';'
	;

activity_bind_stmt:
	'bind' hierarchical_id activity_bind_item_or_list ';'
;

activity_bind_item_or_list:
	hierarchical_id | ('{' hierarchical_id (',' hierarchical_id)* '}')
;

activity_if_else_stmt:
	'if' '(' expression ')' activity_stmt 
	('else' activity_stmt)?
;

activity_select_stmt:
	'select' '{'
		select_branch
		select_branch
		select_branch*
	'}'
;

select_branch:
	select_guard_weight? activity_stmt
	;
	
select_guard_weight:
	(
		('(' guard=expression ')' ('[' weight=expression ']')? ':') 
		| ('[' weight=expression ']' ':')
	)
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
	
// TODO: allow action array elements to be traversed
activity_action_traversal_stmt:
	(
		(variable_ref inline_with_constraint?)
		| (is_do='do' type_identifier inline_with_constraint?)
		| (function_symbol_call)
	)
	';'
;

inline_with_constraint:
	 (
		('with' '{' constraint_body_item* '}') | 
		('with' single_stmt_constraint)
	)
;


activity_parallel_stmt:
	 'parallel' '{'
		activity_stmt*
	'}' 
;

activity_schedule_stmt:
	 'schedule' '{'
		activity_stmt*
	'}' 
;

activity_repeat_stmt:
	 (
		(is_while='while' '(' expression ')' activity_stmt) |
		(is_repeat='repeat' '(' (loop_var=identifier ':')? expression ')' activity_stmt) |
		(is_do_while='repeat' activity_stmt is_do_while='while' '(' expression ')' ';')
		)
;

activity_constraint_stmt:
	 (
		('constraint' ('{' constraint_body_item* '}' )) | 
		('constraint' single_stmt_constraint)
	)
;

activity_foreach_stmt:
	'foreach' '(' expression ')' activity_sequence_block_stmt
;

activity_sequence_block_stmt:
	('sequence')? '{'  activity_stmt* '}'
;

symbol_declaration:
	'symbol' identifier ('(' symbol_paramlist ')')? '{' activity_stmt* '}'
;

symbol_param:
	data_type identifier
;

symbol_paramlist:
	 (symbol_param (',' symbol_param)*)?
;

/********************************************************************
 * H1: Overrides
 ********************************************************************/
overrides_declaration:
	 'override' '{' override_stmt* '}'
;

override_stmt:
	type_override 
	| instance_override
	| null_stmt
;

// TODO: 'identifier' should probably be a type_identifier
type_override:
	'type' target=type_identifier 'with' override=type_identifier ';'
;

// TODO: 'identifier' should probably be a type_identifier
instance_override:
	'instance' target=hierarchical_id 'with' override=type_identifier ';'
;

/********************************************************************
 * H1: Data Declarations
 ********************************************************************/
data_declaration:
	data_type data_instantiation (',' data_instantiation)* ';' 
;

data_instantiation:
	covergroup_port_or_with_instantiation 
	| plain_data_instantiation
	;

covergroup_port_or_with_instantiation:
	(
		(name=identifier '(' portmap=covergroup_portmap_list ')' withclause=covergroup_instance_with_clause?)
		| (name=identifier withclause=covergroup_instance_with_clause)
	)
;

covergroup_instance_with_clause:
	'with' '{'
	covergroup_option*
	'}'
;
	
plain_data_instantiation:	
	name=identifier dim=array_dim? ('=' init=constant_expression)?
;

array_dim:
	 '[' constant_expression ']'
;

covergroup_portmap_list:
	(
		// Name-mapped port binding
		(covergroup_portmap (',' covergroup_portmap)*) |
		// Positional port binding
		(hierarchical_id (',' hierarchical_id)*)
	)?
;

covergroup_portmap:
	'.' identifier '(' hierarchical_id ')'
;


/********************************************************************
 * H1: Data Types
 ********************************************************************/
 
data_type:
	scalar_data_type |
	user_defined_datatype
;

/**
 * BNF: action_data_type ::= scalar_data_type | user_defined_datatype | action_type
action_data_type:
	scalar_data_type |
	user_defined_datatype
;
 */


scalar_data_type:
	chandle_type 	|
	integer_type 	|
	string_type  	|
	bool_type
;

enum_declaration:
  	'enum' enum_identifier '{' 
  		(enum_item (',' enum_item)*)?
  		'}' 
  ;
  
bool_type:
	 'bool'
;

chandle_type:
	 'chandle'
;

enum_item:
	identifier ('=' constant_expression)?
;

user_defined_datatype:
	type_identifier
;

typedef_declaration:
 	'typedef' data_type type_identifier ';' 
;

string_type: 'string';  

integer_type:
	integer_atom_type ('[' lhs=expression (':' rhs=expression)? ']')?
		(is_in='in' '[' domain=domain_open_range_list ']')?
;

integer_atom_type:
	'int'|'bit'
;

domain_open_range_list:
	domain_open_range_value (',' domain_open_range_value)*
;

domain_open_range_value:
	(limit_low='..' rhs=expression) |
	lhs=expression (limit_high='..' (rhs=expression)?)?
;

open_range_list:
	open_range_value (',' open_range_value)*
;

open_range_value:
	lhs=expression ('..' rhs=expression)?
;

/********************************************************************
 * H1: Constraints
 ********************************************************************/
constraint_declaration:
	 
	(
		((is_dynamic='dynamic')? 'constraint' identifier '{' constraint_body_item* '}') |
		('constraint' '{' constraint_body_item* '}') | 
		('constraint' single_stmt_constraint)
	)
;

constraint_body_item:
	expression_constraint_item
	| foreach_constraint_item
	| if_constraint_item
	| unique_constraint_item
	| null_stmt
;

/**
 * BNF: expression_constraint_item ::= 
 	expression implicand_constraint_item
 	| expression <kw>;</kw>
 */
expression_constraint_item:
	expression (implicand_constraint_item|';')
;

implicand_constraint_item:
	'->' constraint_set
;

single_stmt_constraint:
	expression_constraint_item |
	unique_constraint_item
;

if_constraint_item:
	'if' '(' expression ')' constraint_set ('else' constraint_set )? 
;

foreach_constraint_item:
	'foreach' '(' expression ')' constraint_set
;

constraint_set:
	constraint_body_item | 
	constraint_block
;

constraint_block:
	 '{' constraint_body_item* '}'
;

unique_constraint_item:
	'unique' '{' open_range_list '}' ';'
;

/********************************************************************
 * H1: Covergroup
 ********************************************************************/

covergroup_declaration:
	'covergroup' name=identifier ('(' covergroup_port (',' covergroup_port)* ')')? '{'
		covergroup_body_item*
	'}' 
;

inline_covergroup:
	'covergroup' '{'
		covergroup_body_item*
	'}' identifier ';'
;

covergroup_port:
	data_type identifier
;

covergroup_body_item:
	covergroup_option
	| covergroup_coverpoint
	| covergroup_cross
	| null_stmt
;

covergroup_option:
	'option' '.' identifier '=' constant_expression ';'
;

covergroup_type_option:
	'type_option' '.' identifier '=' constant_expression ';'
;

covergroup_coverpoint: 
		(data_type? coverpoint_identifier ':')? 'coverpoint' target=expression ('iff' '(' iff=expression ')')?
			covergroup_coverpoint_body
;

covergroup_coverpoint_body:
		('{' covergroup_coverpoint_body_item* '}' ) 
		| ';'
;

covergroup_coverpoint_body_item:
	covergroup_option
	| covergroup_coverpoint_binspec
	| null_stmt
;

bins_keyword:
	'bins' | 'illegal_bins' | 'ignore_bins' 
;

covergroup_coverpoint_binspec: (
		(bins_keyword identifier (is_array='['constant_expression? ']')? '=' covergroup_coverpoint_explicit_bins)
	)
;

covergroup_coverpoint_explicit_bins:
	(
		('[' covergroup_open_range_list ']' ('with' '(' covergroup_expression ')')? ';')
		| (coverpoint_identifier 'with' '(' covergroup_expression ')' ';')
		| is_default='default' ';'
	)
;

covergroup_open_range_list:
	covergroup_open_range_value (',' covergroup_open_range_value)*
;

covergroup_open_range_value:
	(limit_high='..' rhs=expression) |
	lhs=expression ('..' (rhs=expression)?)?
;

covergroup_expression : expression;


covergroup_cross: 
	identifier ':' 'cross' coverpoint_identifier (',' coverpoint_identifier)*
		('iff' '(' iff=expression ')')? covergroup_cross_body
;

covergroup_cross_body:
	(('{' covergroup_cross_body_item* '}' ) | ';')
;

covergroup_cross_body_item:
	covergroup_option
	| covergroup_cross_binspec
	| null_stmt
;

covergroup_cross_binspec:
	bins_type=bins_keyword name=identifier  
		'=' covercross_identifier 'with' '(' expr=covergroup_expression ')' ';'
;

/********************************************************************
 * Conditional Compile
 ********************************************************************/

package_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=package_body_compile_if_body_stmt
	('else' false_body=package_body_compile_if_body_stmt)?
;

package_body_compile_if_body_stmt:
	package_body_item
	| package_body_compile_if_block_stmt
;

package_body_compile_if_block_stmt:
	'{' package_body_item* '}'
;

action_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=action_body_compile_if_body_stmt
	('else' false_body=action_body_compile_if_body_stmt)?
;

action_body_compile_if_body_stmt:
	action_body_item
	| action_body_compile_if_block_stmt
;

action_body_compile_if_block_stmt:
	'{' action_body_item* '}'
;

component_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=component_body_compile_if_body_stmt
	('else' false_body=component_body_compile_if_body_stmt)?
;

component_body_compile_if_body_stmt:
	component_body_item
	| component_body_compile_if_block_stmt
;

component_body_compile_if_block_stmt:
	'{' component_body_item* '}'
;

struct_body_compile_if:
	'compile' 'if' '(' cond=constant_expression ')' true_body=struct_body_compile_if_body_stmt
	('else' false_body=struct_body_compile_if_body_stmt)?
;

struct_body_compile_if_body_stmt:
	struct_body_item
	| struct_body_compile_if_block_stmt
;

struct_body_compile_if_block_stmt:
	'{' struct_body_item* '}'
;

compile_assert_stmt :
	'compile' 'assert' '(' cond=constant_expression (',' msg=string_literal)? ')' ';'
;


/********************************************************************
 * H1: Expressions
 ********************************************************************/

constant_expression: expression;

expression:
	cast_op lhs=expression								|
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

logical_inequality_op:
	'<'|'<='|'>'|'>='
;

cast_op: '(' data_type ')';

unary_op: '+' | '-' | '!' | '~' | '&' | '|' | '^';

exp_op: '**';

eq_neq_op: '==' | '!=';
shift_op: '<<' | '>>';
add_sub_op: '+' | '-';
mul_div_mod_op: '*' | '/' | '%';

primary: 
	number 					
	| bool_literal			
	| paren_expr
	| string_literal
	| variable_ref_path
	| method_function_call
	| static_ref_path
	| compile_has_expr
	| super_primary
	;

// #6362	
static_ref_path:
	identifier '::' identifier ('::' identifier)*
	;
	
compile_has_static_ref_path:
	(is_global='::')? identifier ('::' identifier)*
	;
	
compile_has_expr:
	'compile' 'has' '(' compile_has_static_ref_path ')'
	;

method_function_call:
	method_call		|
	function_symbol_call
;

method_call:
	method_hierarchical_id method_parameter_list
;

method_hierarchical_id :
	identifier '.' identifier ('.' identifier)*
;

function_symbol_call:
	function_symbol_id method_parameter_list	
;

function_symbol_id:
	type_identifier
;

paren_expr:
	'(' expression ')'
;

variable_ref_path:
	variable_ref ('.' variable_ref)*
;

variable_ref:
	identifier ('[' expression (':' expression)? ']')?
;



/********************************************************************
 * H1: Identifiers and Literals
 ********************************************************************/
action_identifier: identifier;
struct_identifier: identifier;
component_identifier: identifier;
component_action_identifier: identifier;
coverpoint_identifier : identifier;
covercross_identifier : identifier;
enum_identifier: identifier;
import_class_identifier: identifier;
language_identifier: identifier;
method_identifier: identifier;
variable_identifier: identifier;
constant: number | identifier;

coverpoint_target_identifier : hierarchical_id;
parameter_identifier : identifier;

identifier: ID | ESCAPED_ID;

filename_string: DOUBLE_QUOTED_STRING;

// Namespace
package_identifier: type_identifier ;

action_type_identifier: type_identifier;

type_identifier: (explicit_global='::')? ID ('::' ID)* ;

hierarchical_id:
	identifier ('.' identifier)*
;

bool_literal:
	'true'|'false'
;

super_primary:
	'super'
	;

/********************************************************************
 * H1: Numbers
 ********************************************************************/
number:
	based_hex_number 		|
	based_dec_number		|
	based_bin_number		|
	based_oct_number		|
	dec_number			|
	oct_number			|
	hex_number
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


/********************************************************************
 * H1: Comments
 ********************************************************************/

WS : [ \t\n\r]+ -> channel (HIDDEN) ;
 
/**
 * BNF: SL_COMMENT ::= <kw>//</kw>\n 
 */
SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> channel (HIDDEN) ;

/*
 * BNF: ML_COMMENT ::= <kw>/*</kw><kw>*\057</kw>
 */
ML_COMMENT	: '/*' .*? '*/' -> channel (HIDDEN) ;

string: DOUBLE_QUOTED_STRING|TRIPLE_DOUBLE_QUOTED_STRING;

string_literal: value=string;

DOUBLE_QUOTED_STRING	: '"' (~ [\n\r])* '"' ;

/**
 * BNF: TRIPLE_DOUBLE_QUOTED_STRING ::= <kw>"""</kw><kw>"""</kw>
 */
TRIPLE_DOUBLE_QUOTED_STRING:
			'"""' TripleQuotedStringPart*? '"""'
		; 

fragment TripleQuotedStringPart : EscapedTripleQuote | SourceCharacter;
fragment EscapedTripleQuote: '\\"""';
fragment SourceCharacter :[\u0009\u000A\u000D\u0020-\uFFFF];

ID : [a-zA-Z_] [a-zA-Z0-9_]* ;

ESCAPED_ID : '\\' ('\u0021'..'\u007E')+ ~ [ \r\t\n]* ;





