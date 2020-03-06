
grammar DataTypes;

data_type:
	scalar_data_type 
// >>= PSS 1.1
	| container_type
// <<= PSS 1.1
	| user_defined_datatype
;

// >>= PSS 1.1
container_type:
	| ('array' '<' container_elem_type ',' array_size_expression '>')
	| ('list' '<' container_elem_type '>')
	| ('map' '<' container_key_type ',' container_elem_type '>')
	| ('set' '<' container_key_type '>')
	;
	
array_size_expression:
	constant_expression
	;
	
container_elem_type:
	container_type
	| scalar_data_type
	| type_identifier
	;
	
container_key_type:
	scalar_data_type
	| enum_identifier
	;
// <<= PSS 1.1

scalar_data_type:
	chandle_type 	|
	integer_type 	|
	string_type  	|
	bool_type
;

chandle_type:
	 'chandle'
;

integer_type:
	integer_atom_type ('[' lhs=expression (':' rhs=expression)? ']')?
		(is_in='in' '[' domain=domain_open_range_list ']')?
;

integer_atom_type:
	'int'
	| 'bit'
;

domain_open_range_list:
	domain_open_range_value (',' domain_open_range_value)*
;

domain_open_range_value:
	lhs=expression (limit_high='..' (rhs=expression)?)?
	| lhs=expression limit_high='..'
	| (limit_low='..' rhs=expression)
	| lhs=expression
;

string_type: 'string' ( 'in' '[' DOUBLE_QUOTED_STRING (',' DOUBLE_QUOTED_STRING)* ']')? 
;  

bool_type:
	 'bool'
;

user_defined_datatype:
	type_identifier
;

enum_declaration:
  	'enum' enum_identifier '{' 
  		(enum_item (',' enum_item)*)?
  		'}' 
  ;
  
enum_item:
	identifier ('=' constant_expression)?
;

enum_type:
	enum_type_identifier ('in' '[' open_range_list ']')?
;

enum_type_identifier:
	type_identifier
	;
	
typedef_declaration:
 	'typedef' data_type type_identifier ';' 
;
