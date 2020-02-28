/********************************************************************
 * H1: Numbers
 ********************************************************************/
grammar Numbers;

number:
	based_hex_number
	| based_dec_number
	| based_bin_number
	| based_oct_number
	| dec_number
	| oct_number
	| hex_number
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
