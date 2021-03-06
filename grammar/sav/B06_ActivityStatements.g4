/****************************************************************************
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 ****************************************************************************/

grammar ActivityStatements;

activity_stmt: 
	(identifier ':')? labeled_activity_stmt
	| activity_data_field
	| activity_bind_stmt
	| action_handle_declaration
	| activity_constraint_stmt
	| action_scheduling_constraint
// >>= PSS 1.1
	| activity_replicate_stmt
// <<= PSS 1.1
;

labeled_activity_stmt:
	activity_if_else_stmt
	| activity_repeat_stmt
	| activity_foreach_stmt
	| activity_action_traversal_stmt
	| activity_sequence_block_stmt
	| activity_select_stmt
	| activity_match_stmt
	| activity_parallel_stmt
	| activity_schedule_stmt
	| activity_super_stmt
	| function_symbol_call
// >>= PSS 1.1
	// TODO: need to change align-semicolon spec 
	| ';'
// <<= PSS 1.1
;

activity_if_else_stmt:
	'if' '(' expression ')' activity_stmt 
	('else' activity_stmt)?
;

activity_repeat_stmt:
	 (
		(is_while='while' '(' expression ')' activity_stmt) |
		(is_repeat='repeat' '(' (loop_var=identifier ':')? expression ')' activity_stmt) |
		(is_do_while='repeat' activity_stmt is_do_while='while' '(' expression ')' ';')
		)
;

activity_replicate_stmt:
	'replicate' '(' (index_identifier ':')? expression ')' ( identifier '[' ']' ':')? 
		labeled_activity_stmt
	;

activity_sequence_block_stmt:
	('sequence')? '{'  activity_stmt* '}' 
;

activity_constraint_stmt:
	'constraint' constraint_set 
;

activity_foreach_stmt:
	'foreach' '(' (it_id=iterator_identifier)? expression ('[' idx_id=index_identifier ']')? ')'
		activity_stmt
;

activity_action_traversal_stmt:
	(identifier ('[' expression ']')? ';')
	| (identifier ('[' expression ']')? 'with' constraint_set)
	| (is_do='do' type_identifier ';')
	| (is_do='do' type_identifier 'with' constraint_set)
;

activity_select_stmt:
	'select' '{'
		select_branch
		select_branch
		select_branch*
	'}'
;

select_branch:
	(
		('(' guard=expression ')' ('[' weight=expression ']')? ':') 
		| ('[' weight=expression ']' ':')
	)? activity_stmt
	;

activity_match_stmt:
	'match' '(' expression ')' '{'
		match_choice
		match_choice
		match_choice*
	'}'
	;
	
match_choice:
	('[' open_range_list ']' ':' activity_stmt)
	| (is_default='default' ':' activity_stmt)
	;
	
activity_parallel_stmt:
	 'parallel' activity_join_spec? '{'
		activity_stmt*
	'}' 
;

activity_schedule_stmt:
	 'schedule' activity_join_spec? '{'
		activity_stmt*
	'}' 
;

// >>= PSS 1.1
activity_join_spec:
	activity_join_branch_spec
	| activity_join_select_spec
	| activity_join_none_spec
	| activity_join_first_spec
	;
	
activity_join_branch_spec:
	'join_branch' '(' label_identifier (',' label_identifier)* ')'
	;
	
activity_join_select_spec:
	'join_select' '(' expression ')'
	;
	
activity_join_none_spec:
	'join_none'
	;
	
activity_join_first_spec:
	'join_first' '(' expression ')'
	;
	
// <<= PSS 1.1

activity_bind_stmt:
	'bind' hierarchical_id activity_bind_item_or_list ';'
;

activity_bind_item_or_list:
	hierarchical_id 
	| ('{' hierarchical_id (',' hierarchical_id)* '}')
;

symbol_declaration:
	'symbol' identifier ('(' symbol_paramlist ')')? '{' activity_stmt* '}'
;

symbol_paramlist:
	 (symbol_param (',' symbol_param)*)?
;

symbol_param:
	data_type identifier
;

activity_super_stmt:
	'super' ';'
	;
