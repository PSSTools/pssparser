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

grammar Constraint;

constraint_declaration:
	(
		// Note: 1.0 doesn't allow a semicolon after the block constraint forms,
		// despite examples showing this
		((is_dynamic='dynamic')? 'constraint' identifier '{' constraint_body_item* '}' ) 
		| ('constraint' constraint_set )
	)
;

//constraint_declaration ::=
//       [ dynamic ] constraint identifier { { constraint_body_item } }
//     | constraint constraint_set


constraint_body_item:
	expression_constraint_item
	| implication_constraint_item
	| foreach_constraint_item
	| if_constraint_item
	| unique_constraint_item
// >>= PSS 1.1
	| default_constraint_item
	| forall_constraint_item
	| ';'
// <<= PSS 1.1
;

// >>= PSS 1.1
default_constraint_item:
	default_constraint
	| default_disable_constraint
	;
	
default_constraint:
	'default' hierarchical_id '==' constant_expression ';'
	;

default_disable_constraint:
	'default' 'disable' hierarchical_id ';'
	;	
	
forall_constraint_item:
	'forall' '(' identifier ':' type_identifier ('in' variable_ref_path)? ')' constraint_set
	;
// <<= PSS 1.1

expression_constraint_item:
	expression ';'
;

implication_constraint_item:
	expression '->' constraint_set
;

constraint_set:
	constraint_body_item | 
	constraint_block
;

constraint_block:
	 '{' constraint_body_item* '}'
;

foreach_constraint_item:
	'foreach' '(' (it_id=iterator_identifier ':')? expression ('[' idx_id=index_identifier ']')? ')' constraint_set
;

if_constraint_item:
	'if' '(' expression ')' constraint_set ('else' constraint_set )? 
;

unique_constraint_item:
	'unique' '{' hierarchical_id_list '}' ';'
;

single_stmt_constraint:
	expression_constraint_item |
	unique_constraint_item
;


