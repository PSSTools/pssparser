// Generated from grammar/PSS.g4 by ANTLR 4.7.3-SNAPSHOT


import { ParseTreeVisitor } from "antlr4ts/tree/ParseTreeVisitor";

import { Compilation_unitContext } from "./PSSParser";
import { Portable_stimulus_descriptionContext } from "./PSSParser";
import { Package_declarationContext } from "./PSSParser";
import { Package_body_itemContext } from "./PSSParser";
import { Import_stmtContext } from "./PSSParser";
import { Package_import_patternContext } from "./PSSParser";
import { Extend_stmtContext } from "./PSSParser";
import { Const_field_declarationContext } from "./PSSParser";
import { Const_data_declarationContext } from "./PSSParser";
import { Const_data_instantiationContext } from "./PSSParser";
import { Static_const_field_declarationContext } from "./PSSParser";
import { Action_declarationContext } from "./PSSParser";
import { Abstract_action_declarationContext } from "./PSSParser";
import { Action_super_specContext } from "./PSSParser";
import { Action_body_itemContext } from "./PSSParser";
import { Activity_declarationContext } from "./PSSParser";
import { Action_field_declarationContext } from "./PSSParser";
import { Object_ref_declarationContext } from "./PSSParser";
import { Flow_ref_declarationContext } from "./PSSParser";
import { Resource_ref_declarationContext } from "./PSSParser";
import { Object_ref_fieldContext } from "./PSSParser";
import { Flow_object_typeContext } from "./PSSParser";
import { Resource_object_typeContext } from "./PSSParser";
import { Attr_fieldContext } from "./PSSParser";
import { Access_modifierContext } from "./PSSParser";
import { Attr_groupContext } from "./PSSParser";
import { Action_handle_declarationContext } from "./PSSParser";
import { Action_instantiationContext } from "./PSSParser";
import { Activity_data_fieldContext } from "./PSSParser";
import { Action_scheduling_constraintContext } from "./PSSParser";
import { Exec_block_stmtContext } from "./PSSParser";
import { Exec_blockContext } from "./PSSParser";
import { Exec_kind_identifierContext } from "./PSSParser";
import { Exec_stmtContext } from "./PSSParser";
import { Exec_super_stmtContext } from "./PSSParser";
import { Assign_opContext } from "./PSSParser";
import { Target_code_exec_blockContext } from "./PSSParser";
import { Target_file_exec_blockContext } from "./PSSParser";
import { Struct_declarationContext } from "./PSSParser";
import { Struct_kindContext } from "./PSSParser";
import { Object_kindContext } from "./PSSParser";
import { Struct_super_specContext } from "./PSSParser";
import { Struct_body_itemContext } from "./PSSParser";
import { Function_declContext } from "./PSSParser";
import { Method_prototypeContext } from "./PSSParser";
import { Method_return_typeContext } from "./PSSParser";
import { Method_parameter_list_prototypeContext } from "./PSSParser";
import { Method_parameterContext } from "./PSSParser";
import { Method_parameter_dirContext } from "./PSSParser";
import { Function_qualifiersContext } from "./PSSParser";
import { Import_function_qualifiersContext } from "./PSSParser";
import { Method_qualifiersContext } from "./PSSParser";
import { Target_template_functionContext } from "./PSSParser";
import { Method_parameter_listContext } from "./PSSParser";
import { Pss_function_defnContext } from "./PSSParser";
import { Procedural_stmtContext } from "./PSSParser";
import { Procedural_block_stmtContext } from "./PSSParser";
import { Procedural_var_decl_stmtContext } from "./PSSParser";
import { Procedural_expr_stmtContext } from "./PSSParser";
import { Procedural_return_stmtContext } from "./PSSParser";
import { Procedural_if_else_stmtContext } from "./PSSParser";
import { Procedural_match_stmtContext } from "./PSSParser";
import { Procedural_match_choiceContext } from "./PSSParser";
import { Procedural_repeat_stmtContext } from "./PSSParser";
import { Procedural_foreach_stmtContext } from "./PSSParser";
import { Procedural_break_stmtContext } from "./PSSParser";
import { Procedural_continue_stmtContext } from "./PSSParser";
import { Component_declarationContext } from "./PSSParser";
import { Component_super_specContext } from "./PSSParser";
import { Component_body_itemContext } from "./PSSParser";
import { Component_field_declarationContext } from "./PSSParser";
import { Component_data_declarationContext } from "./PSSParser";
import { Component_pool_declarationContext } from "./PSSParser";
import { Object_bind_stmtContext } from "./PSSParser";
import { Object_bind_item_or_listContext } from "./PSSParser";
import { Component_pathContext } from "./PSSParser";
import { Component_path_elemContext } from "./PSSParser";
import { Activity_stmtContext } from "./PSSParser";
import { Labeled_activity_stmtContext } from "./PSSParser";
import { Activity_if_else_stmtContext } from "./PSSParser";
import { Activity_repeat_stmtContext } from "./PSSParser";
import { Activity_replicate_stmtContext } from "./PSSParser";
import { Activity_sequence_block_stmtContext } from "./PSSParser";
import { Activity_constraint_stmtContext } from "./PSSParser";
import { Activity_foreach_stmtContext } from "./PSSParser";
import { Activity_action_traversal_stmtContext } from "./PSSParser";
import { Activity_select_stmtContext } from "./PSSParser";
import { Select_branchContext } from "./PSSParser";
import { Activity_match_stmtContext } from "./PSSParser";
import { Match_choiceContext } from "./PSSParser";
import { Activity_parallel_stmtContext } from "./PSSParser";
import { Activity_schedule_stmtContext } from "./PSSParser";
import { Activity_join_specContext } from "./PSSParser";
import { Activity_join_branch_specContext } from "./PSSParser";
import { Activity_join_select_specContext } from "./PSSParser";
import { Activity_join_none_specContext } from "./PSSParser";
import { Activity_join_first_specContext } from "./PSSParser";
import { Activity_bind_stmtContext } from "./PSSParser";
import { Activity_bind_item_or_listContext } from "./PSSParser";
import { Symbol_declarationContext } from "./PSSParser";
import { Symbol_paramlistContext } from "./PSSParser";
import { Symbol_paramContext } from "./PSSParser";
import { Activity_super_stmtContext } from "./PSSParser";
import { Overrides_declarationContext } from "./PSSParser";
import { Override_stmtContext } from "./PSSParser";
import { Type_overrideContext } from "./PSSParser";
import { Instance_overrideContext } from "./PSSParser";
import { Data_declarationContext } from "./PSSParser";
import { Data_instantiationContext } from "./PSSParser";
import { Array_dimContext } from "./PSSParser";
import { Data_typeContext } from "./PSSParser";
import { Container_typeContext } from "./PSSParser";
import { Array_size_expressionContext } from "./PSSParser";
import { Container_elem_typeContext } from "./PSSParser";
import { Container_key_typeContext } from "./PSSParser";
import { Scalar_data_typeContext } from "./PSSParser";
import { Chandle_typeContext } from "./PSSParser";
import { Integer_typeContext } from "./PSSParser";
import { Integer_atom_typeContext } from "./PSSParser";
import { Domain_open_range_listContext } from "./PSSParser";
import { Domain_open_range_valueContext } from "./PSSParser";
import { String_typeContext } from "./PSSParser";
import { Bool_typeContext } from "./PSSParser";
import { User_defined_datatypeContext } from "./PSSParser";
import { Enum_declarationContext } from "./PSSParser";
import { Enum_itemContext } from "./PSSParser";
import { Enum_typeContext } from "./PSSParser";
import { Enum_type_identifierContext } from "./PSSParser";
import { Typedef_declarationContext } from "./PSSParser";
import { Template_param_decl_listContext } from "./PSSParser";
import { Template_param_declContext } from "./PSSParser";
import { Type_param_declContext } from "./PSSParser";
import { Generic_type_param_declContext } from "./PSSParser";
import { Category_type_param_declContext } from "./PSSParser";
import { Type_restrictionContext } from "./PSSParser";
import { Type_categoryContext } from "./PSSParser";
import { Value_param_declContext } from "./PSSParser";
import { Template_param_value_listContext } from "./PSSParser";
import { Template_param_valueContext } from "./PSSParser";
import { Constraint_declarationContext } from "./PSSParser";
import { Constraint_body_itemContext } from "./PSSParser";
import { Default_constraint_itemContext } from "./PSSParser";
import { Default_constraintContext } from "./PSSParser";
import { Default_disable_constraintContext } from "./PSSParser";
import { Forall_constraint_itemContext } from "./PSSParser";
import { Expression_constraint_itemContext } from "./PSSParser";
import { Implication_constraint_itemContext } from "./PSSParser";
import { Constraint_setContext } from "./PSSParser";
import { Constraint_blockContext } from "./PSSParser";
import { Foreach_constraint_itemContext } from "./PSSParser";
import { If_constraint_itemContext } from "./PSSParser";
import { Unique_constraint_itemContext } from "./PSSParser";
import { Single_stmt_constraintContext } from "./PSSParser";
import { Covergroup_declarationContext } from "./PSSParser";
import { Covergroup_portContext } from "./PSSParser";
import { Covergroup_body_itemContext } from "./PSSParser";
import { Covergroup_optionContext } from "./PSSParser";
import { Covergroup_instantiationContext } from "./PSSParser";
import { Inline_covergroupContext } from "./PSSParser";
import { Covergroup_type_instantiationContext } from "./PSSParser";
import { Covergroup_portmap_listContext } from "./PSSParser";
import { Covergroup_portmapContext } from "./PSSParser";
import { Covergroup_coverpointContext } from "./PSSParser";
import { Bins_or_emptyContext } from "./PSSParser";
import { Covergroup_coverpoint_body_itemContext } from "./PSSParser";
import { Covergroup_coverpoint_binspecContext } from "./PSSParser";
import { Coverpoint_binsContext } from "./PSSParser";
import { Covergroup_range_listContext } from "./PSSParser";
import { Covergroup_value_rangeContext } from "./PSSParser";
import { Bins_keywordContext } from "./PSSParser";
import { Covergroup_crossContext } from "./PSSParser";
import { Cross_item_or_nullContext } from "./PSSParser";
import { Covergroup_cross_body_itemContext } from "./PSSParser";
import { Covergroup_cross_binspecContext } from "./PSSParser";
import { Covergroup_expressionContext } from "./PSSParser";
import { Package_body_compile_ifContext } from "./PSSParser";
import { Package_body_compile_if_itemContext } from "./PSSParser";
import { Action_body_compile_ifContext } from "./PSSParser";
import { Action_body_compile_if_itemContext } from "./PSSParser";
import { Component_body_compile_ifContext } from "./PSSParser";
import { Component_body_compile_if_itemContext } from "./PSSParser";
import { Struct_body_compile_ifContext } from "./PSSParser";
import { Struct_body_compile_if_itemContext } from "./PSSParser";
import { Compile_has_exprContext } from "./PSSParser";
import { Compile_assert_stmtContext } from "./PSSParser";
import { Constant_expressionContext } from "./PSSParser";
import { ExpressionContext } from "./PSSParser";
import { Conditional_exprContext } from "./PSSParser";
import { Logical_or_opContext } from "./PSSParser";
import { Logical_and_opContext } from "./PSSParser";
import { Binary_or_opContext } from "./PSSParser";
import { Binary_xor_opContext } from "./PSSParser";
import { Binary_and_opContext } from "./PSSParser";
import { Inside_expr_termContext } from "./PSSParser";
import { Open_range_listContext } from "./PSSParser";
import { Open_range_valueContext } from "./PSSParser";
import { Logical_inequality_opContext } from "./PSSParser";
import { Unary_opContext } from "./PSSParser";
import { Exp_opContext } from "./PSSParser";
import { PrimaryContext } from "./PSSParser";
import { Paren_exprContext } from "./PSSParser";
import { Cast_expressionContext } from "./PSSParser";
import { Casting_typeContext } from "./PSSParser";
import { Variable_ref_pathContext } from "./PSSParser";
import { Method_function_symbol_callContext } from "./PSSParser";
import { Method_callContext } from "./PSSParser";
import { Function_symbol_callContext } from "./PSSParser";
import { Function_symbol_idContext } from "./PSSParser";
import { Function_idContext } from "./PSSParser";
import { Static_ref_pathContext } from "./PSSParser";
import { Static_ref_path_elemContext } from "./PSSParser";
import { Mul_div_mod_opContext } from "./PSSParser";
import { Add_sub_opContext } from "./PSSParser";
import { Shift_opContext } from "./PSSParser";
import { Eq_neq_opContext } from "./PSSParser";
import { ConstantContext } from "./PSSParser";
import { IdentifierContext } from "./PSSParser";
import { Hierarchical_id_listContext } from "./PSSParser";
import { Hierarchical_idContext } from "./PSSParser";
import { Hierarchical_id_elemContext } from "./PSSParser";
import { Action_type_identifierContext } from "./PSSParser";
import { Type_identifierContext } from "./PSSParser";
import { Type_identifier_elemContext } from "./PSSParser";
import { Package_identifierContext } from "./PSSParser";
import { Covercross_identifierContext } from "./PSSParser";
import { Covergroup_identifierContext } from "./PSSParser";
import { Coverpoint_target_identifierContext } from "./PSSParser";
import { Action_identifierContext } from "./PSSParser";
import { Struct_identifierContext } from "./PSSParser";
import { Component_identifierContext } from "./PSSParser";
import { Component_action_identifierContext } from "./PSSParser";
import { Coverpoint_identifierContext } from "./PSSParser";
import { Enum_identifierContext } from "./PSSParser";
import { Import_class_identifierContext } from "./PSSParser";
import { Label_identifierContext } from "./PSSParser";
import { Language_identifierContext } from "./PSSParser";
import { Method_identifierContext } from "./PSSParser";
import { Symbol_identifierContext } from "./PSSParser";
import { Variable_identifierContext } from "./PSSParser";
import { Iterator_identifierContext } from "./PSSParser";
import { Index_identifierContext } from "./PSSParser";
import { Buffer_type_identifierContext } from "./PSSParser";
import { Covergroup_type_identifierContext } from "./PSSParser";
import { Resource_type_identifierContext } from "./PSSParser";
import { State_type_identifierContext } from "./PSSParser";
import { Stream_type_identifierContext } from "./PSSParser";
import { Bool_literalContext } from "./PSSParser";
import { NumberContext } from "./PSSParser";
import { Based_hex_numberContext } from "./PSSParser";
import { Based_dec_numberContext } from "./PSSParser";
import { Dec_numberContext } from "./PSSParser";
import { Based_bin_numberContext } from "./PSSParser";
import { Based_oct_numberContext } from "./PSSParser";
import { Oct_numberContext } from "./PSSParser";
import { Hex_numberContext } from "./PSSParser";
import { StringContext } from "./PSSParser";
import { Filename_stringContext } from "./PSSParser";
import { Export_actionContext } from "./PSSParser";
import { Import_class_declContext } from "./PSSParser";
import { Import_class_extendsContext } from "./PSSParser";
import { Import_class_method_declContext } from "./PSSParser";


/**
 * This interface defines a complete generic visitor for a parse tree produced
 * by `PSSParser`.
 *
 * @param <Result> The return type of the visit operation. Use `void` for
 * operations with no return type.
 */
export interface PSSVisitor<Result> extends ParseTreeVisitor<Result> {
	/**
	 * Visit a parse tree produced by `PSSParser.compilation_unit`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCompilation_unit?: (ctx: Compilation_unitContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.portable_stimulus_description`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPortable_stimulus_description?: (ctx: Portable_stimulus_descriptionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_declaration?: (ctx: Package_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_body_item?: (ctx: Package_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_stmt?: (ctx: Import_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_import_pattern`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_import_pattern?: (ctx: Package_import_patternContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.extend_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExtend_stmt?: (ctx: Extend_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.const_field_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConst_field_declaration?: (ctx: Const_field_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.const_data_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConst_data_declaration?: (ctx: Const_data_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.const_data_instantiation`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConst_data_instantiation?: (ctx: Const_data_instantiationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.static_const_field_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStatic_const_field_declaration?: (ctx: Static_const_field_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_declaration?: (ctx: Action_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.abstract_action_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAbstract_action_declaration?: (ctx: Abstract_action_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_super_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_super_spec?: (ctx: Action_super_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_body_item?: (ctx: Action_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_declaration?: (ctx: Activity_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_field_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_field_declaration?: (ctx: Action_field_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.object_ref_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitObject_ref_declaration?: (ctx: Object_ref_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.flow_ref_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFlow_ref_declaration?: (ctx: Flow_ref_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.resource_ref_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitResource_ref_declaration?: (ctx: Resource_ref_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.object_ref_field`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitObject_ref_field?: (ctx: Object_ref_fieldContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.flow_object_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFlow_object_type?: (ctx: Flow_object_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.resource_object_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitResource_object_type?: (ctx: Resource_object_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.attr_field`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAttr_field?: (ctx: Attr_fieldContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.access_modifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAccess_modifier?: (ctx: Access_modifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.attr_group`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAttr_group?: (ctx: Attr_groupContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_handle_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_handle_declaration?: (ctx: Action_handle_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_instantiation`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_instantiation?: (ctx: Action_instantiationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_data_field`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_data_field?: (ctx: Activity_data_fieldContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_scheduling_constraint`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_scheduling_constraint?: (ctx: Action_scheduling_constraintContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exec_block_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExec_block_stmt?: (ctx: Exec_block_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exec_block`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExec_block?: (ctx: Exec_blockContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exec_kind_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExec_kind_identifier?: (ctx: Exec_kind_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exec_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExec_stmt?: (ctx: Exec_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exec_super_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExec_super_stmt?: (ctx: Exec_super_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.assign_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAssign_op?: (ctx: Assign_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.target_code_exec_block`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTarget_code_exec_block?: (ctx: Target_code_exec_blockContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.target_file_exec_block`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTarget_file_exec_block?: (ctx: Target_file_exec_blockContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_declaration?: (ctx: Struct_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_kind`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_kind?: (ctx: Struct_kindContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.object_kind`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitObject_kind?: (ctx: Object_kindContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_super_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_super_spec?: (ctx: Struct_super_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_body_item?: (ctx: Struct_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.function_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFunction_decl?: (ctx: Function_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_prototype`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_prototype?: (ctx: Method_prototypeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_return_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_return_type?: (ctx: Method_return_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_parameter_list_prototype`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_parameter_list_prototype?: (ctx: Method_parameter_list_prototypeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_parameter`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_parameter?: (ctx: Method_parameterContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_parameter_dir`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_parameter_dir?: (ctx: Method_parameter_dirContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.function_qualifiers`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFunction_qualifiers?: (ctx: Function_qualifiersContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_function_qualifiers`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_function_qualifiers?: (ctx: Import_function_qualifiersContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_qualifiers`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_qualifiers?: (ctx: Method_qualifiersContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.target_template_function`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTarget_template_function?: (ctx: Target_template_functionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_parameter_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_parameter_list?: (ctx: Method_parameter_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.pss_function_defn`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPss_function_defn?: (ctx: Pss_function_defnContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_stmt?: (ctx: Procedural_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_block_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_block_stmt?: (ctx: Procedural_block_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_var_decl_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_var_decl_stmt?: (ctx: Procedural_var_decl_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_expr_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_expr_stmt?: (ctx: Procedural_expr_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_return_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_return_stmt?: (ctx: Procedural_return_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_if_else_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_if_else_stmt?: (ctx: Procedural_if_else_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_match_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_match_stmt?: (ctx: Procedural_match_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_match_choice`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_match_choice?: (ctx: Procedural_match_choiceContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_repeat_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_repeat_stmt?: (ctx: Procedural_repeat_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_foreach_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_foreach_stmt?: (ctx: Procedural_foreach_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_break_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_break_stmt?: (ctx: Procedural_break_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.procedural_continue_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitProcedural_continue_stmt?: (ctx: Procedural_continue_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_declaration?: (ctx: Component_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_super_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_super_spec?: (ctx: Component_super_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_body_item?: (ctx: Component_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_field_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_field_declaration?: (ctx: Component_field_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_data_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_data_declaration?: (ctx: Component_data_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_pool_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_pool_declaration?: (ctx: Component_pool_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.object_bind_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitObject_bind_stmt?: (ctx: Object_bind_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.object_bind_item_or_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitObject_bind_item_or_list?: (ctx: Object_bind_item_or_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_path`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_path?: (ctx: Component_pathContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_path_elem`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_path_elem?: (ctx: Component_path_elemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_stmt?: (ctx: Activity_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.labeled_activity_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLabeled_activity_stmt?: (ctx: Labeled_activity_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_if_else_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_if_else_stmt?: (ctx: Activity_if_else_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_repeat_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_repeat_stmt?: (ctx: Activity_repeat_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_replicate_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_replicate_stmt?: (ctx: Activity_replicate_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_sequence_block_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_sequence_block_stmt?: (ctx: Activity_sequence_block_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_constraint_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_constraint_stmt?: (ctx: Activity_constraint_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_foreach_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_foreach_stmt?: (ctx: Activity_foreach_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_action_traversal_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_action_traversal_stmt?: (ctx: Activity_action_traversal_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_select_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_select_stmt?: (ctx: Activity_select_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.select_branch`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSelect_branch?: (ctx: Select_branchContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_match_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_match_stmt?: (ctx: Activity_match_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.match_choice`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMatch_choice?: (ctx: Match_choiceContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_parallel_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_parallel_stmt?: (ctx: Activity_parallel_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_schedule_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_schedule_stmt?: (ctx: Activity_schedule_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_join_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_join_spec?: (ctx: Activity_join_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_join_branch_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_join_branch_spec?: (ctx: Activity_join_branch_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_join_select_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_join_select_spec?: (ctx: Activity_join_select_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_join_none_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_join_none_spec?: (ctx: Activity_join_none_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_join_first_spec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_join_first_spec?: (ctx: Activity_join_first_specContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_bind_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_bind_stmt?: (ctx: Activity_bind_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_bind_item_or_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_bind_item_or_list?: (ctx: Activity_bind_item_or_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.symbol_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSymbol_declaration?: (ctx: Symbol_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.symbol_paramlist`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSymbol_paramlist?: (ctx: Symbol_paramlistContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.symbol_param`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSymbol_param?: (ctx: Symbol_paramContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.activity_super_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitActivity_super_stmt?: (ctx: Activity_super_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.overrides_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitOverrides_declaration?: (ctx: Overrides_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.override_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitOverride_stmt?: (ctx: Override_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_override`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_override?: (ctx: Type_overrideContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.instance_override`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitInstance_override?: (ctx: Instance_overrideContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.data_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitData_declaration?: (ctx: Data_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.data_instantiation`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitData_instantiation?: (ctx: Data_instantiationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.array_dim`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitArray_dim?: (ctx: Array_dimContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.data_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitData_type?: (ctx: Data_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.container_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitContainer_type?: (ctx: Container_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.array_size_expression`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitArray_size_expression?: (ctx: Array_size_expressionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.container_elem_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitContainer_elem_type?: (ctx: Container_elem_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.container_key_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitContainer_key_type?: (ctx: Container_key_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.scalar_data_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitScalar_data_type?: (ctx: Scalar_data_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.chandle_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitChandle_type?: (ctx: Chandle_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.integer_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitInteger_type?: (ctx: Integer_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.integer_atom_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitInteger_atom_type?: (ctx: Integer_atom_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.domain_open_range_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDomain_open_range_list?: (ctx: Domain_open_range_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.domain_open_range_value`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDomain_open_range_value?: (ctx: Domain_open_range_valueContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.string_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitString_type?: (ctx: String_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.bool_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBool_type?: (ctx: Bool_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.user_defined_datatype`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitUser_defined_datatype?: (ctx: User_defined_datatypeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.enum_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEnum_declaration?: (ctx: Enum_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.enum_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEnum_item?: (ctx: Enum_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.enum_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEnum_type?: (ctx: Enum_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.enum_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEnum_type_identifier?: (ctx: Enum_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.typedef_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTypedef_declaration?: (ctx: Typedef_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.template_param_decl_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTemplate_param_decl_list?: (ctx: Template_param_decl_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.template_param_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTemplate_param_decl?: (ctx: Template_param_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_param_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_param_decl?: (ctx: Type_param_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.generic_type_param_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitGeneric_type_param_decl?: (ctx: Generic_type_param_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.category_type_param_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCategory_type_param_decl?: (ctx: Category_type_param_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_restriction`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_restriction?: (ctx: Type_restrictionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_category`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_category?: (ctx: Type_categoryContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.value_param_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitValue_param_decl?: (ctx: Value_param_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.template_param_value_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTemplate_param_value_list?: (ctx: Template_param_value_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.template_param_value`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitTemplate_param_value?: (ctx: Template_param_valueContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constraint_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstraint_declaration?: (ctx: Constraint_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constraint_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstraint_body_item?: (ctx: Constraint_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.default_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDefault_constraint_item?: (ctx: Default_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.default_constraint`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDefault_constraint?: (ctx: Default_constraintContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.default_disable_constraint`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDefault_disable_constraint?: (ctx: Default_disable_constraintContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.forall_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitForall_constraint_item?: (ctx: Forall_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.expression_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExpression_constraint_item?: (ctx: Expression_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.implication_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImplication_constraint_item?: (ctx: Implication_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constraint_set`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstraint_set?: (ctx: Constraint_setContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constraint_block`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstraint_block?: (ctx: Constraint_blockContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.foreach_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitForeach_constraint_item?: (ctx: Foreach_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.if_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitIf_constraint_item?: (ctx: If_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.unique_constraint_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitUnique_constraint_item?: (ctx: Unique_constraint_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.single_stmt_constraint`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSingle_stmt_constraint?: (ctx: Single_stmt_constraintContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_declaration`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_declaration?: (ctx: Covergroup_declarationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_port`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_port?: (ctx: Covergroup_portContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_body_item?: (ctx: Covergroup_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_option`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_option?: (ctx: Covergroup_optionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_instantiation`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_instantiation?: (ctx: Covergroup_instantiationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.inline_covergroup`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitInline_covergroup?: (ctx: Inline_covergroupContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_type_instantiation`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_type_instantiation?: (ctx: Covergroup_type_instantiationContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_portmap_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_portmap_list?: (ctx: Covergroup_portmap_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_portmap`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_portmap?: (ctx: Covergroup_portmapContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_coverpoint`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_coverpoint?: (ctx: Covergroup_coverpointContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.bins_or_empty`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBins_or_empty?: (ctx: Bins_or_emptyContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_coverpoint_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_coverpoint_body_item?: (ctx: Covergroup_coverpoint_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_coverpoint_binspec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_coverpoint_binspec?: (ctx: Covergroup_coverpoint_binspecContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.coverpoint_bins`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCoverpoint_bins?: (ctx: Coverpoint_binsContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_range_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_range_list?: (ctx: Covergroup_range_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_value_range`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_value_range?: (ctx: Covergroup_value_rangeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.bins_keyword`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBins_keyword?: (ctx: Bins_keywordContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_cross`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_cross?: (ctx: Covergroup_crossContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.cross_item_or_null`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCross_item_or_null?: (ctx: Cross_item_or_nullContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_cross_body_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_cross_body_item?: (ctx: Covergroup_cross_body_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_cross_binspec`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_cross_binspec?: (ctx: Covergroup_cross_binspecContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_expression`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_expression?: (ctx: Covergroup_expressionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_body_compile_if`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_body_compile_if?: (ctx: Package_body_compile_ifContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_body_compile_if_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_body_compile_if_item?: (ctx: Package_body_compile_if_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_body_compile_if`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_body_compile_if?: (ctx: Action_body_compile_ifContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_body_compile_if_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_body_compile_if_item?: (ctx: Action_body_compile_if_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_body_compile_if`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_body_compile_if?: (ctx: Component_body_compile_ifContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_body_compile_if_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_body_compile_if_item?: (ctx: Component_body_compile_if_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_body_compile_if`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_body_compile_if?: (ctx: Struct_body_compile_ifContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_body_compile_if_item`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_body_compile_if_item?: (ctx: Struct_body_compile_if_itemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.compile_has_expr`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCompile_has_expr?: (ctx: Compile_has_exprContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.compile_assert_stmt`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCompile_assert_stmt?: (ctx: Compile_assert_stmtContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constant_expression`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstant_expression?: (ctx: Constant_expressionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.expression`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExpression?: (ctx: ExpressionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.conditional_expr`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConditional_expr?: (ctx: Conditional_exprContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.logical_or_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLogical_or_op?: (ctx: Logical_or_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.logical_and_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLogical_and_op?: (ctx: Logical_and_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.binary_or_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBinary_or_op?: (ctx: Binary_or_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.binary_xor_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBinary_xor_op?: (ctx: Binary_xor_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.binary_and_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBinary_and_op?: (ctx: Binary_and_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.inside_expr_term`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitInside_expr_term?: (ctx: Inside_expr_termContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.open_range_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitOpen_range_list?: (ctx: Open_range_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.open_range_value`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitOpen_range_value?: (ctx: Open_range_valueContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.logical_inequality_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLogical_inequality_op?: (ctx: Logical_inequality_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.unary_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitUnary_op?: (ctx: Unary_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.exp_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExp_op?: (ctx: Exp_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.primary`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPrimary?: (ctx: PrimaryContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.paren_expr`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitParen_expr?: (ctx: Paren_exprContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.cast_expression`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCast_expression?: (ctx: Cast_expressionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.casting_type`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCasting_type?: (ctx: Casting_typeContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.variable_ref_path`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitVariable_ref_path?: (ctx: Variable_ref_pathContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_function_symbol_call`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_function_symbol_call?: (ctx: Method_function_symbol_callContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_call`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_call?: (ctx: Method_callContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.function_symbol_call`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFunction_symbol_call?: (ctx: Function_symbol_callContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.function_symbol_id`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFunction_symbol_id?: (ctx: Function_symbol_idContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.function_id`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFunction_id?: (ctx: Function_idContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.static_ref_path`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStatic_ref_path?: (ctx: Static_ref_pathContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.static_ref_path_elem`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStatic_ref_path_elem?: (ctx: Static_ref_path_elemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.mul_div_mod_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMul_div_mod_op?: (ctx: Mul_div_mod_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.add_sub_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAdd_sub_op?: (ctx: Add_sub_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.shift_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitShift_op?: (ctx: Shift_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.eq_neq_op`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEq_neq_op?: (ctx: Eq_neq_opContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.constant`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitConstant?: (ctx: ConstantContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitIdentifier?: (ctx: IdentifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.hierarchical_id_list`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitHierarchical_id_list?: (ctx: Hierarchical_id_listContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.hierarchical_id`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitHierarchical_id?: (ctx: Hierarchical_idContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.hierarchical_id_elem`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitHierarchical_id_elem?: (ctx: Hierarchical_id_elemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_type_identifier?: (ctx: Action_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_identifier?: (ctx: Type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.type_identifier_elem`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitType_identifier_elem?: (ctx: Type_identifier_elemContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.package_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitPackage_identifier?: (ctx: Package_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covercross_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovercross_identifier?: (ctx: Covercross_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_identifier?: (ctx: Covergroup_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.coverpoint_target_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCoverpoint_target_identifier?: (ctx: Coverpoint_target_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.action_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitAction_identifier?: (ctx: Action_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.struct_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStruct_identifier?: (ctx: Struct_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_identifier?: (ctx: Component_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.component_action_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitComponent_action_identifier?: (ctx: Component_action_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.coverpoint_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCoverpoint_identifier?: (ctx: Coverpoint_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.enum_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitEnum_identifier?: (ctx: Enum_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_class_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_class_identifier?: (ctx: Import_class_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.label_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLabel_identifier?: (ctx: Label_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.language_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitLanguage_identifier?: (ctx: Language_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.method_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitMethod_identifier?: (ctx: Method_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.symbol_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitSymbol_identifier?: (ctx: Symbol_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.variable_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitVariable_identifier?: (ctx: Variable_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.iterator_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitIterator_identifier?: (ctx: Iterator_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.index_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitIndex_identifier?: (ctx: Index_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.buffer_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBuffer_type_identifier?: (ctx: Buffer_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.covergroup_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitCovergroup_type_identifier?: (ctx: Covergroup_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.resource_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitResource_type_identifier?: (ctx: Resource_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.state_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitState_type_identifier?: (ctx: State_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.stream_type_identifier`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitStream_type_identifier?: (ctx: Stream_type_identifierContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.bool_literal`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBool_literal?: (ctx: Bool_literalContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitNumber?: (ctx: NumberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.based_hex_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBased_hex_number?: (ctx: Based_hex_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.based_dec_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBased_dec_number?: (ctx: Based_dec_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.dec_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitDec_number?: (ctx: Dec_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.based_bin_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBased_bin_number?: (ctx: Based_bin_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.based_oct_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitBased_oct_number?: (ctx: Based_oct_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.oct_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitOct_number?: (ctx: Oct_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.hex_number`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitHex_number?: (ctx: Hex_numberContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.string`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitString?: (ctx: StringContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.filename_string`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitFilename_string?: (ctx: Filename_stringContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.export_action`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitExport_action?: (ctx: Export_actionContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_class_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_class_decl?: (ctx: Import_class_declContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_class_extends`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_class_extends?: (ctx: Import_class_extendsContext) => Result;

	/**
	 * Visit a parse tree produced by `PSSParser.import_class_method_decl`.
	 * @param ctx the parse tree
	 * @return the visitor result
	 */
	visitImport_class_method_decl?: (ctx: Import_class_method_declContext) => Result;
}

