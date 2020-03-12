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

grammar LexicalRules;

WS : [ \t\n\r]+ -> channel (HIDDEN) ;

/**
 * BNF: SL_COMMENT ::= <kw>//</kw>\n 
 */
SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> channel (HIDDEN) ;

/*
 * BNF: ML_COMMENT ::= <kw>/*</kw><kw>*\057</kw>
 */
ML_COMMENT	: '/*' .*? '*/' -> channel (HIDDEN) ;
 
string: DOUBLE_QUOTED_STRING | TRIPLE_DOUBLE_QUOTED_STRING;

DOUBLE_QUOTED_STRING	: '"' (~ [\n\r])* '"' ;

// TODO: unescaped_character, escaped_character

/**
 * BNF: TRIPLE_DOUBLE_QUOTED_STRING ::= <kw>"""</kw><kw>"""</kw>
 */
TRIPLE_DOUBLE_QUOTED_STRING:
			'"""' TripleQuotedStringPart*? '"""'
		; 
		
fragment TripleQuotedStringPart : EscapedTripleQuote | SourceCharacter;
fragment EscapedTripleQuote: '\\"""';
fragment SourceCharacter :[\u0009\u000A\u000D\u0020-\uFFFF];
		
// TODO: move to LexicalRules
ID : [a-zA-Z_] [a-zA-Z0-9_]* ;

ESCAPED_ID : '\\' ('\u0021'..'\u007E')+ ~ [ \r\t\n]* ;
