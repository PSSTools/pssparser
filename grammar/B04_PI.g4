
grammar PI;

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
	'import' (import_function_qualifiers)? 'function' type_identifier ';'
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
	'function' method_prototype '=' string ';'
	;

// TODO: method_parameter_list appears unused	
method_parameter_list: 
	'('
	(
		expression (',' expression)*
	)?
	')'
;

	