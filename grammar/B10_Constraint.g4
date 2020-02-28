
grammar Constraint;

constraint_declaration:
	(
		((is_dynamic='dynamic')? 'constraint' identifier '{' constraint_body_item* '}') 
		| ('constraint' '{' constraint_body_item* '}') 
		| ('constraint' single_stmt_constraint)
	)
;

constraint_body_item:
	expression_constraint_item
	| foreach_constraint_item
	| if_constraint_item
	| unique_constraint_item
;

expression_constraint_item:
	expression implicand_constraint_item 
	| expression ';'
;

implicand_constraint_item:
	'->' constraint_set
;

constraint_set:
	constraint_body_item | 
	constraint_block
;

constraint_block:
	 '{' constraint_body_item* '}'
;

foreach_constraint_item:
	'foreach' '(' (it_id=iterator_identifier ':')? expression ('[' idx_id=index_identifier ']')? ')' constraint_set
;

if_constraint_item:
	'if' '(' expression ')' constraint_set ('else' constraint_set )? 
;

unique_constraint_item:
	'unique' '{' hierarchical_id_list '}' ';'
;

single_stmt_constraint:
	expression_constraint_item |
	unique_constraint_item
;


