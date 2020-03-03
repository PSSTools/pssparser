
grammar Overrides;

overrides_declaration:
	 'override' '{' override_stmt* '}'
;

override_stmt:
	type_override 
	| instance_override
// >>= PSS 1.1
	| ';'
// <<= PSS 1.1
;

type_override:
	'type' target=type_identifier 'with' override=type_identifier ';'
;


instance_override:
	'instance' target=hierarchical_id 'with' override=type_identifier ';'
;