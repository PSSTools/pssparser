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

grammar TemplateTypes;

// >>= PSS-1.1

template_param_decl_list: 
	'<' template_param_decl ( ',' template_param_decl )* '>'
	;

template_param_decl:
	type_param_decl 
	| value_param_decl
	;

type_param_decl: 
	generic_type_param_decl 
	| category_type_param_decl
	;

generic_type_param_decl: 
	'type' identifier ( '=' type_identifier )?
	;

category_type_param_decl: 
	type_category identifier ( type_restriction )? ( '=' type_identifier )?
	;

type_restriction: 
	':' type_identifier
	;

type_category:
    'action'
  | 'component'
  | struct_kind
  ;

value_param_decl: 
	data_type identifier ( '=' constant_expression )?
	;

template_param_value_list: 
	'<' ( template_param_value ( ',' template_param_value )* )? '>'
	;

template_param_value: 
	constant_expression 
	| type_identifier
	;

// <<= PSS-1.1
