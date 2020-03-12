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

	