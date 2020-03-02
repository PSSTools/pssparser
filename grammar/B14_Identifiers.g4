
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
	(explicit_global='::')? type_identifier_elem ('::' type_identifier_elem)* 
	;
	
// >>= PSS 1.1
type_identifier_elem:
	identifier template_param_value_list?
	;
// <<= PSS 1.1 
	
package_identifier: type_identifier ;

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

filename_string: DOUBLE_QUOTED_STRING;


bool_literal:
	'true'|'false'
;


