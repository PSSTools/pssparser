/****************************************************************************
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
