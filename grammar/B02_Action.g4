
grammar Action;

action_declaration:
	'action' action_identifier (action_super_spec)? 
	'{'
		action_body_item*
	'}' (';')?
;

abstract_action_declaration :
	'abstract' 'action' action_identifier (action_super_spec)?
	'{'
		action_body_item*
	'}' (';')?
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
	| static_const_field_declaration
	| action_scheduling_constraint
//TODO	| attr_group
	| compile_assert_stmt
	| covergroup_instantiation
	| action_body_compile_if
	| inline_covergroup
	//TODO: | null_stmt
;

activity_declaration: 'activity' '{' activity_stmt* '}' (';')?
	;

action_field_declaration:
	object_ref_field
	| attr_field
	| activity_data_field
	| attr_group
	| action_handle_declaration
	| activity_data_field
;

object_ref_field:
	flow_ref_field
	| resource_ref_field
	;
	
flow_ref_field:
	(is_input='input' | is_output='output') flow_object_type identifier (',' identifier)* ';'
	;
	
resource_ref_field:
	(lock='lock' | share='share') resource_object_type identifier (',' identifier)* ';'
	;
	
flow_object_type:
	type_identifier
	;
	
resource_object_type:
	type_identifier
	;
	
attr_field:
	access_modifier? rand='rand'? declaration=data_declaration
;

access_modifier:
	'public' | 'protected' | 'private'
	;
	
attr_group:
	access_modifier ':'
	;
	
action_handle_declaration:
	action_type_identifier action_instantiation ';'
	;
	
action_instantiation:
	ids+=action_identifier (array_dim)? (',' ids+=action_identifier (array_dim)? )*
	;

activity_data_field:
	'action' data_declaration
;

// TODO: BNF has hierarchical_id
action_scheduling_constraint:
	'constraint' (is_parallel='parallel' | is_sequence='sequence') '{'
		variable_ref_path ',' variable_ref_path (',' variable_ref_path)* '}'
	;

// Exec

exec_block_stmt:
	exec_block |
	target_code_exec_block |
	target_file_exec_block
	;
	
exec_block:
	'exec' exec_kind_identifier '{' exec_body_stmt* '}' (';')?
;

exec_kind_identifier:
	'pre_solve' 
	| 'post_solve' 
	| 'body' 
	| 'header' 
	| 'declaration' 
	| 'run_start' 
	| 'run_end' 
	| 'init'
;	

exec_body_stmt:
	exec_body_method_call_stmt
	| exec_body_super_stmt
	| exec_body_assign_stmt
	;
	
exec_body_method_call_stmt:
	method_function_symbol_call ';'
	;
	
exec_body_super_stmt:
	'super' ';'
	;

exec_body_assign_stmt:
	variable_ref_path assign_op expression ';'
	;
	

assign_op:
	'=' | '+=' | '-=' | '<<=' | '>>=' | '|=' | '&='
;

target_code_exec_block:
	'exec' exec_kind_identifier language_identifier '=' string ';'
;

target_file_exec_block:
	'exec' 'file' filename_string '=' string ';'
;

	