
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
