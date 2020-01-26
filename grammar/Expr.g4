/****************************************************************************
 * Expr.g4
 ****************************************************************************/

grammar Expr;
	
entry : 
	expression EOF
	;

open_range_list:
	open_range_value (',' open_range_value)*
;

open_range_value:
	lhs=expression ('..' rhs=expression)?
;

expression:
	unary_op lhs=expression								|
	lhs=expression exp_op rhs=expression 				|
	lhs=expression mul_div_mod_op rhs=expression 		|
	lhs=expression add_sub_op rhs=expression			|
	lhs=expression shift_op rhs=expression				|
	lhs=expression inside_expr_term						|
    lhs=expression logical_inequality_op rhs=expression	|
    lhs=expression eq_neq_op rhs=expression				|
    lhs=expression binary_and_op rhs=expression			|
    lhs=expression binary_xor_op rhs=expression			|
    lhs=expression binary_or_op rhs=expression			|
    lhs=expression logical_and_op rhs=expression		|
    lhs=expression logical_or_op rhs=expression			|
    lhs=expression conditional_expr						|
	primary
	;

conditional_expr :
	'?' true_expr=expression ':' false_expr=expression
	; 

logical_or_op : '||';
logical_and_op : '&&';
binary_or_op : '|';
binary_xor_op : '^';
binary_and_op : '&';

inside_expr_term :
	'in' '[' open_range_list ']'
;

logical_inequality_op:
	'<'|'<='|'>'|'>='
;

unary_op: '+' | '-' | '!' | '~' | '&' | '|' | '^';

exp_op: '**';

eq_neq_op: '==' | '!=';
shift_op: '<<' | '>>';
add_sub_op: '+' | '-';
mul_div_mod_op: '*' | '/' | '%';

primary: 
	number 					
	| bool_literal			
	| paren_expr
	| string
	| variable_ref_path
	| static_ref_path
	;

static_ref_path:
	identifier '::' identifier ('::' identifier)*
	;

paren_expr:
	'(' expression ')'
;

variable_ref_path:
	variable_ref ('.' variable_ref)*
;

variable_ref:
	identifier ('[' expression (':' expression)? ']')?
;


identifier: ID | ESCAPED_ID;

bool_literal:
	'true'|'false'
;

/********************************************************************
 * H1: Numbers
 ********************************************************************/
number:
	based_hex_number 		|
	based_dec_number		|
	based_bin_number		|
	based_oct_number		|
	dec_number			|
	oct_number			|
	hex_number
;

based_hex_number: DEC_LITERAL? BASED_HEX_LITERAL;
BASED_HEX_LITERAL: '\'' ('s'|'S')? ('h'|'H') ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;

based_dec_number: DEC_LITERAL? BASED_DEC_LITERAL;
BASED_DEC_LITERAL: '\'' ('s'|'S')? ('d'|'D') ('0'..'9') ('0'..'9'|'_')*;

dec_number: DEC_LITERAL;
DEC_LITERAL: ('1'..'9') ('0'..'9'|'_')*;

based_bin_number: DEC_LITERAL? BASED_BIN_LITERAL;
BASED_BIN_LITERAL: '\'' ('s'|'S')? ('b'|'B') (('0'..'1') ('0'..'1'|'_')*);

based_oct_number: DEC_LITERAL? BASED_OCT_LITERAL;
BASED_OCT_LITERAL: '\'' ('s'|'S')? ('o'|'O') (('0'..'7') ('0'..'7'|'_')*);


oct_number: OCT_LITERAL;
OCT_LITERAL: '0' ('0'..'7')*;

hex_number: HEX_LITERAL;
HEX_LITERAL: '0x' ('0'..'9'|'a'..'f'|'A'..'F') ('0'..'9'|'a'..'f'|'A'..'F'|'_')*;


/********************************************************************
 * H1: Comments
 ********************************************************************/

WS : [ \t\n\r]+ -> channel (HIDDEN) ;
 
string: DOUBLE_QUOTED_STRING|TRIPLE_DOUBLE_QUOTED_STRING;

DOUBLE_QUOTED_STRING	: '"' (~ [\n\r])* '"' ;

/**
 * BNF: TRIPLE_DOUBLE_QUOTED_STRING ::= <kw>"""</kw><kw>"""</kw>
 */
TRIPLE_DOUBLE_QUOTED_STRING:
			'"""' TripleQuotedStringPart*? '"""'
		; 

fragment TripleQuotedStringPart : EscapedTripleQuote | SourceCharacter;
fragment EscapedTripleQuote: '\\"""';
fragment SourceCharacter :[\u0009\u000A\u000D\u0020-\uFFFF];

ID : [a-zA-Z_] [a-zA-Z0-9_]* ;

ESCAPED_ID : '\\' ('\u0021'..'\u007E')+ ~ [ \r\t\n]* ;





