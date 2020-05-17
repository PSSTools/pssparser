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

grammar Coverage;


covergroup_declaration:
	'covergroup' name=covergroup_identifier ('(' covergroup_port (',' covergroup_port)* ')')? '{'
		covergroup_body_item*
	'}' 
;

covergroup_port:
	data_type identifier
;

covergroup_body_item:
	covergroup_option
	| covergroup_coverpoint
	| covergroup_cross
// >>= PSS 1.1
	| ';'
// <<= PSS 1.1
;

covergroup_option:
	'option' '.' identifier '=' constant_expression ';'
;

covergroup_instantiation:
	covergroup_type_instantiation
	| inline_covergroup
	;
	
inline_covergroup:
	'covergroup' '{'
		covergroup_body_item*
	'}' identifier ';'
;

covergroup_type_instantiation:
	covergroup_type_identifier covergroup_identifier
	'(' covergroup_portmap_list ')' ('with' '{' (covergroup_option)? '}')? ';'
	;
	
covergroup_portmap_list:
	(
		(covergroup_portmap (',' covergroup_portmap)?)
		| hierarchical_id_list
	)
	;
	
covergroup_portmap:
	'.' identifier '(' hierarchical_id ')'
	;
		
covergroup_coverpoint: 
		(data_type? coverpoint_identifier ':')? 'coverpoint' target=expression ('iff' '(' iff=expression ')')?
			bins_or_empty
;

bins_or_empty:
		('{' covergroup_coverpoint_body_item* '}' ) 
		| ';'
;

covergroup_coverpoint_body_item:
	covergroup_option
	| covergroup_coverpoint_binspec
;

covergroup_coverpoint_binspec: (
		(bins_keyword identifier (is_array='['constant_expression? ']')? '=' coverpoint_bins)
	)
;

coverpoint_bins:
	(
		('[' covergroup_range_list ']' ('with' '(' covergroup_expression ')')? ';')
		| (coverpoint_identifier 'with' '(' covergroup_expression ')' ';')
		| is_default='default' ';'
	)
;

covergroup_range_list:
	covergroup_value_range (',' covergroup_value_range)*
	;

covergroup_value_range:
	expression
	| (expression '..' expression?)
	| (expression?	'..' expression)
	;

bins_keyword:
	'bins' 
	| 'illegal_bins' 
	| 'ignore_bins' 
;

covergroup_cross: 
	identifier ':' 'cross' coverpoint_identifier (',' coverpoint_identifier)*
		('iff' '(' iff=expression ')')? cross_item_or_null
;

cross_item_or_null:
	('{' covergroup_cross_body_item* '}' )
	| ';'
;

covergroup_cross_body_item:
	covergroup_option
	| covergroup_cross_binspec
	;
	

covergroup_cross_binspec:
	bins_type=bins_keyword name=identifier  
		'=' covercross_identifier 'with' '(' expr=covergroup_expression ')' ';'
	;

// TODO: no definition in the BNF	
covergroup_expression:
	expression
	;
	
	
