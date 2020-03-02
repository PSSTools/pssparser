
grammar ConditionalCompile;

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

	