
grammar DataDeclarations;


data_declaration:
	data_type data_instantiation (',' data_instantiation)* ';' 
;

data_instantiation:
	identifier (array_dim)? ('=' constant_expression)?
	;
	
covergroup_portmap_list:
	(
		// Name-mapped port binding
		(covergroup_portmap (',' covergroup_portmap)*) 
		// Positional port binding
		| (hierarchical_id (',' hierarchical_id)*)
	)?
;

covergroup_portmap:
	'.' identifier '(' hierarchical_id ')'
;

array_dim:
	 '[' constant_expression ']'
;

