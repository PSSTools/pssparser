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
import B01_Package, B02_Action, B03_Struct, B04_PI,
	B05_Component, B06_ActivityStatements, B07_Overrides,
	B08_DataDeclarations, B09_DataTypes, B10_Constraint,
	B11_Coverage, B12_ConditionalCompile, B13_Expressions,
	B14_Identifiers, B15_Numbers, B16_LexicalRules,
	ImportClass, ExportAction
	;
	
compilation_unit : 
	portable_stimulus_description* EOF
	;

portable_stimulus_description : 
	package_body_item
	| package_declaration
	| component_declaration
	;

sub_action_field:
	type_identifier identifier array_dim? ';'
	;


/****************************************************************************
 * H1: Procedural Interface
 ****************************************************************************/

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

/****************************************************************************
 * H1: Component Declaration
 ****************************************************************************/


/********************************************************************
 * H1: Activity-Graph Statements
 ********************************************************************/

activity_labeled_stmt:
	identifier ':' labeled_activity_stmt
	;


activity_null_stmt:
	';'
	;





	
// TODO: allow action array elements to be traversed


/********************************************************************
 * H1: Overrides
 ********************************************************************/


// TODO: 'identifier' should probably be a type_identifier

// TODO: 'identifier' should probably be a type_identifier

/********************************************************************
 * H1: Data Declarations
 ********************************************************************/


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




/********************************************************************
 * H1: Data Types
 ********************************************************************/
 

/**
 * BNF: action_data_type ::= scalar_data_type | user_defined_datatype | action_type
action_data_type:
	scalar_data_type |
	user_defined_datatype
;
 */



  










open_range_list:
	open_range_value (',' open_range_value)*
;

open_range_value:
	lhs=expression ('..' rhs=expression)?
;

/********************************************************************
 * H1: Covergroup
 ********************************************************************/

covergroup_type_option:
	'type_option' '.' identifier '=' constant_expression ';'
;

covergroup_expression : expression;



/********************************************************************
 * Conditional Compile
 ********************************************************************/



package_body_compile_if_block_stmt:
	'{' package_body_item* '}'
;

action_body_compile_if_block_stmt:
	'{' action_body_item* '}'
;


component_body_compile_if_body_stmt:
	component_body_item
	| component_body_compile_if_block_stmt
;

component_body_compile_if_block_stmt:
	'{' component_body_item* '}'
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

bool_literal:
	'true'|'false'
;

super_primary:
	'super'
	;




