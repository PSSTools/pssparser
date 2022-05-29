/****************************************************************************
 * PSSLexer.g4 
 ****************************************************************************/

lexer grammar PSSLexer;

TOK_AT: '@';
TOK_LPAREN: '(';
TOK_RPAREN: ')';
TOK_COMMA: ',';
TOK_DOUBLE_EQ: '==';
TOK_SINGLE_EQ: '=';
TOK_NE: '!=';
TOK_PACKAGE: 'package';
TOK_LCBRACE: '{';
TOK_RCBRACE: '}';
TOK_SEMICOLON: ';';
TOK_IMPORT: 'import';
TOK_DOUBLE_COLON: '::';
TOK_ASTERISK: '*';
TOK_EXTEND: 'extend';
TOK_ACTION: 'action';
TOK_COMPONENT: 'component';
TOK_ENUM: 'enum';
TOK_CONST: 'const';
TOK_STATIC: 'static';
TOK_ABSTRACT: 'abstract';
TOK_COLON: ':';
TOK_ACTIVITY: 'activity';
TOK_INPUT: 'input';
TOK_OUTPUT: 'output';
TOK_INOUT: 'inout';
TOK_LOCK: 'lock';
TOK_SHARE: 'share';
TOK_RAND: 'rand';
TOK_PUBLIC: 'public';
TOK_PROTECTED: 'protected';
TOK_PRIVATE: 'private';
TOK_CONSTRAINT: 'constraint';
TOK_PARALLEL: 'parallel';
TOK_SEQUENCE: 'sequence';
TOK_EXEC: 'exec';
TOK_STRUCT: 'struct';
TOK_BUFFER: 'buffer';
TOK_STREAM: 'stream';
TOK_STATE: 'state';
TOK_RESOURCE: 'resource';
TOK_PRE_SOLVE: 'pre_solve';
TOK_POST_SOLVE: 'post_solve';
TOK_BODY: 'body';
TOK_HEADER: 'header';
TOK_DECLARATION: 'declaration';
TOK_RUN_START: 'run_start';
TOK_RUN_END: 'run_end';
TOK_INIT: 'init';
TOK_INIT_UP: 'init_up';
TOK_INIT_DOWN: 'init_down';
TOK_SUPER: 'super';
TOK_PLUS_EQ: '+=';
TOK_MINUS_EQ: '-=';
TOK_SHL_EQ: '<<=';
TOK_SHR_EQ: '>>=';
TOK_OR_EQ: '|=';
TOK_AND_EQ: '&=';
TOK_FILE: 'file';
TOK_FUNCTION: 'function';
TOK_VOID: 'void';
TOK_TARGET: 'target';
TOK_SOLVE: 'solve';
TOK_RETURN: 'return';
TOK_IF: 'if';
TOK_ELSE: 'else';
TOK_MATCH: 'match';
TOK_LSBRACE: '[';
TOK_RSBRACE: ']';
TOK_DEFAULT: 'default';
TOK_WHILE: 'while';
TOK_REPEAT: 'repeat';
TOK_FOREACH: 'foreach';
TOK_BREAK: 'break';
TOK_CONTINUE: 'continue';
TOK_POOL: 'pool';
TOK_BIND: 'bind';
TOK_DOT: '.';
TOK_REPLICATE: 'replicate';
TOK_WITH: 'with';
TOK_DO: 'do';
TOK_SELECT: 'select';
TOK_SCHEDULE: 'schedule';
TOK_JOIN_BRANCH: 'join_branch';
TOK_JOIN_SELECT: 'join_select';
TOK_JOIN_NONE: 'join_none';
TOK_JOIN_FIRST: 'join_first';
TOK_SYMBOL: 'symbol';
TOK_OVERRIDE: 'override';
TOK_TYPE: 'type';
TOK_INSTANCE: 'instance';
TOK_CHANDLE: 'chandle';
TOK_ARRAY: 'array';
TOK_LIST: 'list';
TOK_MAP: 'map';
TOK_SET: 'set';
TOK_LT: '<';
TOK_LTE: '<=';
TOK_GT: '>';
TOK_GTE: '>=';
TOK_IN: 'in';
TOK_INT: 'int';
TOK_BIT: 'bit';
TOK_ELIPSIS: '..';
TOK_STRING: 'string';
TOK_BOOL: 'bool';
TOK_TYPEDEF: 'typedef';
TOK_DYNAMIC: 'dynamic';
TOK_DISABLE: 'disable';
TOK_FORALL: 'forall';
TOK_IMPLIES: '->';
TOK_UNIQUE: 'unique';
TOK_COVERGROUP: 'covergroup';
TOK_COVERPOINT: 'coverpoint';
TOK_BINS: 'bins';
TOK_ILLEGAL_BINS: 'illegal_bins';
TOK_IGNORE_BINS: 'ignore_bins';
TOK_CROSS: 'cross';
TOK_IFF: 'iff';
TOK_COMPILE: 'compile';
TOK_ASSERT: 'assert';
TOK_HAS: 'has';
TOK_COND: '?';
TOK_OPTION: 'option';
TOK_PLUS: '+';
TOK_MINUS: '-';
TOK_NOT: '!';
TOK_NEG: '~';
TOK_SINGLE_AND: '&';
TOK_DOUBLE_AND: '&';
TOK_SINGLE_OR: '|';
TOK_DOUBLE_OR: '||';
TOK_CARET: '^';
TOK_EXP: '**';
TOK_DIV: '/';
TOK_MOD: '%';
TOK_DOUBLE_LT: '<<';
TOK_TRUE: 'true';
TOK_FALSE: 'false';
TOK_EXPORT: 'export';
TOK_CLASS: 'class';

WS : [ \t\n\r]+ -> channel (10) ;
//WS : [ \t\n\r]+ -> skip;

/**
 * BNF: SL_COMMENT ::= <kw>//</kw>\n 
 */
SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> channel (11) ;
//SL_COMMENT 	: '//' .*? '\r'? ('\n'|EOF) -> skip;

/*
 * BNF: ML_COMMENT ::= <kw>/*</kw><kw>*\057</kw>
 */
ML_COMMENT	: '/*' .*? '*/' -> channel (12) ;
//ML_COMMENT	: '/*' .*? '*/' -> skip;
 

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
		
BASED_HEX_LITERAL: '\'' ('s'|'S')? ('h'|'H') ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;
BASED_DEC_LITERAL: '\'' ('s'|'S')? ('d'|'D') ('0'..'9') ('0'..'9'|'_')*;
DEC_LITERAL: ('1'..'9') ('0'..'9'|'_')*;
BASED_BIN_LITERAL: '\'' ('s'|'S')? ('b'|'B') (('0'..'1') ('0'..'1'|'_')*);
BASED_OCT_LITERAL: '\'' ('s'|'S')? ('o'|'O') (('0'..'7') ('0'..'7'|'_')*);
OCT_LITERAL: '0' ('0'..'7')*;
HEX_LITERAL: '0x' ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;



