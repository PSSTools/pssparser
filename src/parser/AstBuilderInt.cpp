/*
 * AstBuilderInt.cpp
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#include "AstBuilderInt.h"

namespace pssp {

AstBuilderInt::AstBuilderInt(IMarkerListener *marker_l) : m_marker_l(marker_l) {
	// TODO Auto-generated constructor stub

}

AstBuilderInt::~AstBuilderInt() {
	// TODO Auto-generated destructor stub
}

void AstBuilderInt::build(std::istream *in) {
	;
}

antlrcpp::Any AstBuilderInt::visitCompilation_unit(PSSParser::Compilation_unitContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPortable_stimulus_description(PSSParser::Portable_stimulus_descriptionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_declaration(PSSParser::Package_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_body_item(PSSParser::Package_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_stmt(PSSParser::Import_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_import_pattern(PSSParser::Package_import_patternContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExtend_stmt(PSSParser::Extend_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConst_field_declaration(PSSParser::Const_field_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConst_data_declaration(PSSParser::Const_data_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConst_data_instantiation(PSSParser::Const_data_instantiationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStatic_const_field_declaration(PSSParser::Static_const_field_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_declaration(PSSParser::Action_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAbstract_action_declaration(PSSParser::Abstract_action_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_super_spec(PSSParser::Action_super_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_body_item(PSSParser::Action_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_declaration(PSSParser::Activity_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_field_declaration(PSSParser::Action_field_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitObject_ref_declaration(PSSParser::Object_ref_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFlow_ref_declaration(PSSParser::Flow_ref_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitResource_ref_declaration(PSSParser::Resource_ref_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitObject_ref_field(PSSParser::Object_ref_fieldContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFlow_object_type(PSSParser::Flow_object_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitResource_object_type(PSSParser::Resource_object_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAttr_field(PSSParser::Attr_fieldContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAccess_modifier(PSSParser::Access_modifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAttr_group(PSSParser::Attr_groupContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_handle_declaration(PSSParser::Action_handle_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_instantiation(PSSParser::Action_instantiationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_data_field(PSSParser::Activity_data_fieldContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_scheduling_constraint(PSSParser::Action_scheduling_constraintContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExec_block_stmt(PSSParser::Exec_block_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExec_block(PSSParser::Exec_blockContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExec_kind_identifier(PSSParser::Exec_kind_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExec_stmt(PSSParser::Exec_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExec_super_stmt(PSSParser::Exec_super_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAssign_op(PSSParser::Assign_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTarget_code_exec_block(PSSParser::Target_code_exec_blockContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTarget_file_exec_block(PSSParser::Target_file_exec_blockContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_declaration(PSSParser::Struct_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_kind(PSSParser::Struct_kindContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitObject_kind(PSSParser::Object_kindContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_super_spec(PSSParser::Struct_super_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_body_item(PSSParser::Struct_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFunction_decl(PSSParser::Function_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_prototype(PSSParser::Method_prototypeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_return_type(PSSParser::Method_return_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_parameter_list_prototype(PSSParser::Method_parameter_list_prototypeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_parameter(PSSParser::Method_parameterContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_parameter_dir(PSSParser::Method_parameter_dirContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFunction_qualifiers(PSSParser::Function_qualifiersContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_function_qualifiers(PSSParser::Import_function_qualifiersContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_qualifiers(PSSParser::Method_qualifiersContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTarget_template_function(PSSParser::Target_template_functionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_parameter_list(PSSParser::Method_parameter_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPss_function_defn(PSSParser::Pss_function_defnContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_stmt(PSSParser::Procedural_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_block_stmt(PSSParser::Procedural_block_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_var_decl_stmt(PSSParser::Procedural_var_decl_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_expr_stmt(PSSParser::Procedural_expr_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_return_stmt(PSSParser::Procedural_return_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_if_else_stmt(PSSParser::Procedural_if_else_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_match_stmt(PSSParser::Procedural_match_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_match_choice(PSSParser::Procedural_match_choiceContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_repeat_stmt(PSSParser::Procedural_repeat_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_foreach_stmt(PSSParser::Procedural_foreach_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_break_stmt(PSSParser::Procedural_break_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitProcedural_continue_stmt(PSSParser::Procedural_continue_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_declaration(PSSParser::Component_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_super_spec(PSSParser::Component_super_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_body_item(PSSParser::Component_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_field_declaration(PSSParser::Component_field_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_data_declaration(PSSParser::Component_data_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_pool_declaration(PSSParser::Component_pool_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitObject_bind_stmt(PSSParser::Object_bind_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitObject_bind_item_or_list(PSSParser::Object_bind_item_or_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_path(PSSParser::Component_pathContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_path_elem(PSSParser::Component_path_elemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_stmt(PSSParser::Activity_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLabeled_activity_stmt(PSSParser::Labeled_activity_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_if_else_stmt(PSSParser::Activity_if_else_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_repeat_stmt(PSSParser::Activity_repeat_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_replicate_stmt(PSSParser::Activity_replicate_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_sequence_block_stmt(PSSParser::Activity_sequence_block_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_constraint_stmt(PSSParser::Activity_constraint_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_foreach_stmt(PSSParser::Activity_foreach_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_action_traversal_stmt(PSSParser::Activity_action_traversal_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_select_stmt(PSSParser::Activity_select_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSelect_branch(PSSParser::Select_branchContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_match_stmt(PSSParser::Activity_match_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMatch_choice(PSSParser::Match_choiceContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_parallel_stmt(PSSParser::Activity_parallel_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_schedule_stmt(PSSParser::Activity_schedule_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_join_spec(PSSParser::Activity_join_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_join_branch_spec(PSSParser::Activity_join_branch_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_join_select_spec(PSSParser::Activity_join_select_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_join_none_spec(PSSParser::Activity_join_none_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_join_first_spec(PSSParser::Activity_join_first_specContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_bind_stmt(PSSParser::Activity_bind_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_bind_item_or_list(PSSParser::Activity_bind_item_or_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSymbol_declaration(PSSParser::Symbol_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSymbol_paramlist(PSSParser::Symbol_paramlistContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSymbol_param(PSSParser::Symbol_paramContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitActivity_super_stmt(PSSParser::Activity_super_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitOverrides_declaration(PSSParser::Overrides_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitOverride_stmt(PSSParser::Override_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_override(PSSParser::Type_overrideContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitInstance_override(PSSParser::Instance_overrideContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitData_declaration(PSSParser::Data_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitData_instantiation(PSSParser::Data_instantiationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitArray_dim(PSSParser::Array_dimContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitData_type(PSSParser::Data_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitContainer_type(PSSParser::Container_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitArray_size_expression(PSSParser::Array_size_expressionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitContainer_elem_type(PSSParser::Container_elem_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitContainer_key_type(PSSParser::Container_key_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitScalar_data_type(PSSParser::Scalar_data_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitChandle_type(PSSParser::Chandle_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitInteger_type(PSSParser::Integer_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitInteger_atom_type(PSSParser::Integer_atom_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDomain_open_range_list(PSSParser::Domain_open_range_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDomain_open_range_value(PSSParser::Domain_open_range_valueContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitString_type(PSSParser::String_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBool_type(PSSParser::Bool_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitUser_defined_datatype(PSSParser::User_defined_datatypeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEnum_declaration(PSSParser::Enum_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEnum_item(PSSParser::Enum_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEnum_type(PSSParser::Enum_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEnum_type_identifier(PSSParser::Enum_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTypedef_declaration(PSSParser::Typedef_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTemplate_param_decl_list(PSSParser::Template_param_decl_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTemplate_param_decl(PSSParser::Template_param_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_param_decl(PSSParser::Type_param_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitGeneric_type_param_decl(PSSParser::Generic_type_param_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCategory_type_param_decl(PSSParser::Category_type_param_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_restriction(PSSParser::Type_restrictionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_category(PSSParser::Type_categoryContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitValue_param_decl(PSSParser::Value_param_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTemplate_param_value_list(PSSParser::Template_param_value_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitTemplate_param_value(PSSParser::Template_param_valueContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstraint_declaration(PSSParser::Constraint_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstraint_body_item(PSSParser::Constraint_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDefault_constraint_item(PSSParser::Default_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDefault_constraint(PSSParser::Default_constraintContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDefault_disable_constraint(PSSParser::Default_disable_constraintContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitForall_constraint_item(PSSParser::Forall_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExpression_constraint_item(PSSParser::Expression_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImplication_constraint_item(PSSParser::Implication_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstraint_set(PSSParser::Constraint_setContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstraint_block(PSSParser::Constraint_blockContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitForeach_constraint_item(PSSParser::Foreach_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitIf_constraint_item(PSSParser::If_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSingle_stmt_constraint(PSSParser::Single_stmt_constraintContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_declaration(PSSParser::Covergroup_declarationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_port(PSSParser::Covergroup_portContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_body_item(PSSParser::Covergroup_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_option(PSSParser::Covergroup_optionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_instantiation(PSSParser::Covergroup_instantiationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitInline_covergroup(PSSParser::Inline_covergroupContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_type_instantiation(PSSParser::Covergroup_type_instantiationContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_portmap_list(PSSParser::Covergroup_portmap_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_portmap(PSSParser::Covergroup_portmapContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_coverpoint(PSSParser::Covergroup_coverpointContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBins_or_empty(PSSParser::Bins_or_emptyContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_coverpoint_body_item(PSSParser::Covergroup_coverpoint_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_coverpoint_binspec(PSSParser::Covergroup_coverpoint_binspecContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCoverpoint_bins(PSSParser::Coverpoint_binsContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_range_list(PSSParser::Covergroup_range_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_value_range(PSSParser::Covergroup_value_rangeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBins_keyword(PSSParser::Bins_keywordContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_cross(PSSParser::Covergroup_crossContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCross_item_or_null(PSSParser::Cross_item_or_nullContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_cross_body_item(PSSParser::Covergroup_cross_body_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_cross_binspec(PSSParser::Covergroup_cross_binspecContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_expression(PSSParser::Covergroup_expressionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_body_compile_if(PSSParser::Package_body_compile_ifContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_body_compile_if_item(PSSParser::Package_body_compile_if_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_body_compile_if(PSSParser::Action_body_compile_ifContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_body_compile_if_item(PSSParser::Action_body_compile_if_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_body_compile_if(PSSParser::Component_body_compile_ifContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_body_compile_if_item(PSSParser::Component_body_compile_if_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_body_compile_if(PSSParser::Struct_body_compile_ifContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_body_compile_if_item(PSSParser::Struct_body_compile_if_itemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCompile_has_expr(PSSParser::Compile_has_exprContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCompile_assert_stmt(PSSParser::Compile_assert_stmtContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstant_expression(PSSParser::Constant_expressionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExpression(PSSParser::ExpressionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConditional_expr(PSSParser::Conditional_exprContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLogical_or_op(PSSParser::Logical_or_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLogical_and_op(PSSParser::Logical_and_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBinary_or_op(PSSParser::Binary_or_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBinary_xor_op(PSSParser::Binary_xor_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBinary_and_op(PSSParser::Binary_and_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitInside_expr_term(PSSParser::Inside_expr_termContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitOpen_range_list(PSSParser::Open_range_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitOpen_range_value(PSSParser::Open_range_valueContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLogical_inequality_op(PSSParser::Logical_inequality_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitUnary_op(PSSParser::Unary_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExp_op(PSSParser::Exp_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPrimary(PSSParser::PrimaryContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitParen_expr(PSSParser::Paren_exprContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCast_expression(PSSParser::Cast_expressionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCasting_type(PSSParser::Casting_typeContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitVariable_ref_path(PSSParser::Variable_ref_pathContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_function_symbol_call(PSSParser::Method_function_symbol_callContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_call(PSSParser::Method_callContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFunction_symbol_call(PSSParser::Function_symbol_callContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFunction_symbol_id(PSSParser::Function_symbol_idContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFunction_id(PSSParser::Function_idContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStatic_ref_path(PSSParser::Static_ref_pathContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStatic_ref_path_elem(PSSParser::Static_ref_path_elemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMul_div_mod_op(PSSParser::Mul_div_mod_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAdd_sub_op(PSSParser::Add_sub_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitShift_op(PSSParser::Shift_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEq_neq_op(PSSParser::Eq_neq_opContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitConstant(PSSParser::ConstantContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitIdentifier(PSSParser::IdentifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitHierarchical_id_list(PSSParser::Hierarchical_id_listContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitHierarchical_id(PSSParser::Hierarchical_idContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitHierarchical_id_elem(PSSParser::Hierarchical_id_elemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_type_identifier(PSSParser::Action_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_identifier(PSSParser::Type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitType_identifier_elem(PSSParser::Type_identifier_elemContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitPackage_identifier(PSSParser::Package_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovercross_identifier(PSSParser::Covercross_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_identifier(PSSParser::Covergroup_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCoverpoint_target_identifier(PSSParser::Coverpoint_target_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitAction_identifier(PSSParser::Action_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStruct_identifier(PSSParser::Struct_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_identifier(PSSParser::Component_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitComponent_action_identifier(PSSParser::Component_action_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCoverpoint_identifier(PSSParser::Coverpoint_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitEnum_identifier(PSSParser::Enum_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_class_identifier(PSSParser::Import_class_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLabel_identifier(PSSParser::Label_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitLanguage_identifier(PSSParser::Language_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitMethod_identifier(PSSParser::Method_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitSymbol_identifier(PSSParser::Symbol_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitVariable_identifier(PSSParser::Variable_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitIterator_identifier(PSSParser::Iterator_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitIndex_identifier(PSSParser::Index_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBuffer_type_identifier(PSSParser::Buffer_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitCovergroup_type_identifier(PSSParser::Covergroup_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitResource_type_identifier(PSSParser::Resource_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitState_type_identifier(PSSParser::State_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitStream_type_identifier(PSSParser::Stream_type_identifierContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBool_literal(PSSParser::Bool_literalContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitNumber(PSSParser::NumberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBased_hex_number(PSSParser::Based_hex_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBased_dec_number(PSSParser::Based_dec_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitDec_number(PSSParser::Dec_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBased_bin_number(PSSParser::Based_bin_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitBased_oct_number(PSSParser::Based_oct_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitOct_number(PSSParser::Oct_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitHex_number(PSSParser::Hex_numberContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitString(PSSParser::StringContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitFilename_string(PSSParser::Filename_stringContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitExport_action(PSSParser::Export_actionContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_class_decl(PSSParser::Import_class_declContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_class_extends(PSSParser::Import_class_extendsContext *context) { return 0; }

antlrcpp::Any AstBuilderInt::visitImport_class_method_decl(PSSParser::Import_class_method_declContext *context) { return 0; }

void AstBuilderInt::syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) {
	if (m_marker_l) {

	}
}

}
