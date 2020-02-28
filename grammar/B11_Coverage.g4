
grammar Coverage;


covergroup_declaration:
	'covergroup' name=covergroup_identifier ('(' covergroup_port (',' covergroup_port)* ')')? '{'
		covergroup_body_item*
	'}' (';')?
;

covergroup_port:
	data_type identifier
;

covergroup_body_item:
	covergroup_option
	| covergroup_coverpoint
	| covergroup_cross
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
		('{' covergroup_coverpoint_body_item* '}' (';')? ) 
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
	('{' covergroup_cross_body_item* '}' (';')?)
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
	
	
