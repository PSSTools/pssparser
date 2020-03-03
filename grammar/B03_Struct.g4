
grammar Struct;

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
