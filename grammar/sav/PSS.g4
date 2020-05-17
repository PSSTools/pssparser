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
grammar PSS;

import B01_Package, B02_Action, B03_Struct, B04_PI,
	B05_Component, B06_ActivityStatements, B07_Overrides,
	B08_DataDeclarations, B09_DataTypes, B09_TemplateTypes,
	B10_Constraint,
	B11_Coverage, B12_ConditionalCompile, B13_Expressions,
	B14_Identifiers, B15_Numbers, B16_LexicalRules,
	ImportClass, ExportAction
	;
	
compilation_unit : 
	portable_stimulus_description* EOF
	;

portable_stimulus_description : 
	package_body_item
	| package_declaration
	| component_declaration
	;







