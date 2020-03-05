
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
	procedural_var_decl_stmt
	| procedural_expr_stmt
	| procedural_return_stmt
	| procedural_if_else_stmt
	| procedural_match_stmt
	| procedural_repeat_stmt
	| procedural_foreach_stmt
	| procedural_break_stmt
	| procedural_continue_stmt
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
	('while' '(' expression ')' procedural_stmt)
	| ('repeat' '(' (identifier ':')? expression ')' procedural_stmt)
	| ('repeat' procedural_stmt 'while' '(' expression ')' ';')
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

	