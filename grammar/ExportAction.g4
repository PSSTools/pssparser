
grammar ExportAction;

export_action:
	'export' (method_qualifiers)? action_type_identifier method_parameter_list_prototype ';'
;
