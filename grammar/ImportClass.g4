
grammar ImportClass;

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
