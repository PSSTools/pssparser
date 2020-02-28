
grammar Component;

component_declaration:
	'component' component_identifier (component_super_spec)? '{'
	component_body_item*
	'}' (';')?
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
	| package_body_item
	| attr_group
	| component_body_compile_if
;

component_field_declaration:
	component_data_declaration |
	component_pool_declaration
;

component_data_declaration:
	('static' 'const')? data_declaration
;

component_pool_declaration:
	'pool' ('[' expression ']')? type_identifier identifier ';'
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

