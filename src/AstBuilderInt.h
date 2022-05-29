/*
 * AstBuilderInt.h
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <istream>
#include "pssp/IMarkerListener.h"
#include "PSSParserBaseVisitor.h"
#include "BaseErrorListener.h"
#include "GlobalScope.h"
#include "Scope.h"

using namespace antlr4;
using namespace antlrcpp;

namespace pssp {

class AstBuilderInt :
		public PSSParserBaseVisitor,
		public BaseErrorListener {
public:
	AstBuilderInt(IMarkerListener *marker_l);

	virtual ~AstBuilderInt();

	void build(
			GlobalScope		*global,
			std::istream 	*in);

    virtual antlrcpp::Any visitPackage_declaration(PSSParser::Package_declarationContext *context) override;

    virtual antlrcpp::Any visitImport_stmt(PSSParser::Import_stmtContext *context) override;

    virtual antlrcpp::Any visitPackage_import_pattern(PSSParser::Package_import_patternContext *context) override;

    virtual antlrcpp::Any visitExtend_stmt(PSSParser::Extend_stmtContext *context) override;

    virtual antlrcpp::Any visitConst_field_declaration(PSSParser::Const_field_declarationContext *context) override;

    virtual antlrcpp::Any visitConst_data_declaration(PSSParser::Const_data_declarationContext *context) override;

    virtual antlrcpp::Any visitConst_data_instantiation(PSSParser::Const_data_instantiationContext *context) override;

    virtual antlrcpp::Any visitStatic_const_field_declaration(PSSParser::Static_const_field_declarationContext *context) override;

    virtual antlrcpp::Any visitAction_declaration(PSSParser::Action_declarationContext *context) override;

    virtual antlrcpp::Any visitAbstract_action_declaration(PSSParser::Abstract_action_declarationContext *context) override;

    virtual antlrcpp::Any visitAction_super_spec(PSSParser::Action_super_specContext *context) override;

    virtual antlrcpp::Any visitAction_body_item(PSSParser::Action_body_itemContext *context) override;

    virtual antlrcpp::Any visitActivity_declaration(PSSParser::Activity_declarationContext *context) override;

    virtual antlrcpp::Any visitAction_field_declaration(PSSParser::Action_field_declarationContext *context) override;

    virtual antlrcpp::Any visitObject_ref_declaration(PSSParser::Object_ref_declarationContext *context) override;

    virtual antlrcpp::Any visitFlow_ref_declaration(PSSParser::Flow_ref_declarationContext *context) override;

    virtual antlrcpp::Any visitResource_ref_declaration(PSSParser::Resource_ref_declarationContext *context) override;

    virtual antlrcpp::Any visitObject_ref_field(PSSParser::Object_ref_fieldContext *context) override;

    virtual antlrcpp::Any visitFlow_object_type(PSSParser::Flow_object_typeContext *context) override;

    virtual antlrcpp::Any visitResource_object_type(PSSParser::Resource_object_typeContext *context) override;

    virtual antlrcpp::Any visitAttr_field(PSSParser::Attr_fieldContext *context) override;

    virtual antlrcpp::Any visitAccess_modifier(PSSParser::Access_modifierContext *context) override;

    virtual antlrcpp::Any visitAttr_group(PSSParser::Attr_groupContext *context) override;

    virtual antlrcpp::Any visitAction_handle_declaration(PSSParser::Action_handle_declarationContext *context) override;

    virtual antlrcpp::Any visitAction_instantiation(PSSParser::Action_instantiationContext *context) override;

    virtual antlrcpp::Any visitActivity_data_field(PSSParser::Activity_data_fieldContext *context) override;

    virtual antlrcpp::Any visitAction_scheduling_constraint(PSSParser::Action_scheduling_constraintContext *context) override;

    virtual antlrcpp::Any visitExec_block_stmt(PSSParser::Exec_block_stmtContext *context) override;

    virtual antlrcpp::Any visitExec_block(PSSParser::Exec_blockContext *context) override;

    virtual antlrcpp::Any visitExec_kind_identifier(PSSParser::Exec_kind_identifierContext *context) override;

    virtual antlrcpp::Any visitExec_stmt(PSSParser::Exec_stmtContext *context) override;

    virtual antlrcpp::Any visitExec_super_stmt(PSSParser::Exec_super_stmtContext *context) override;

    virtual antlrcpp::Any visitAssign_op(PSSParser::Assign_opContext *context) override;

    virtual antlrcpp::Any visitTarget_code_exec_block(PSSParser::Target_code_exec_blockContext *context) override;

    virtual antlrcpp::Any visitTarget_file_exec_block(PSSParser::Target_file_exec_blockContext *context) override;

    virtual antlrcpp::Any visitStruct_declaration(PSSParser::Struct_declarationContext *context) override;

    virtual antlrcpp::Any visitStruct_kind(PSSParser::Struct_kindContext *context) override;

    virtual antlrcpp::Any visitObject_kind(PSSParser::Object_kindContext *context) override;

    virtual antlrcpp::Any visitStruct_super_spec(PSSParser::Struct_super_specContext *context) override;

    virtual antlrcpp::Any visitStruct_body_item(PSSParser::Struct_body_itemContext *context) override;

    virtual antlrcpp::Any visitFunction_decl(PSSParser::Function_declContext *context) override;

    virtual antlrcpp::Any visitMethod_prototype(PSSParser::Method_prototypeContext *context) override;

    virtual antlrcpp::Any visitMethod_return_type(PSSParser::Method_return_typeContext *context) override;

    virtual antlrcpp::Any visitMethod_parameter_list_prototype(PSSParser::Method_parameter_list_prototypeContext *context) override;

    virtual antlrcpp::Any visitMethod_parameter(PSSParser::Method_parameterContext *context) override;

    virtual antlrcpp::Any visitMethod_parameter_dir(PSSParser::Method_parameter_dirContext *context) override;

    virtual antlrcpp::Any visitFunction_qualifiers(PSSParser::Function_qualifiersContext *context) override;

    virtual antlrcpp::Any visitImport_function_qualifiers(PSSParser::Import_function_qualifiersContext *context) override;

    virtual antlrcpp::Any visitMethod_qualifiers(PSSParser::Method_qualifiersContext *context) override;

    virtual antlrcpp::Any visitTarget_template_function(PSSParser::Target_template_functionContext *context) override;

    virtual antlrcpp::Any visitMethod_parameter_list(PSSParser::Method_parameter_listContext *context) override;

    virtual antlrcpp::Any visitPss_function_defn(PSSParser::Pss_function_defnContext *context) override;

    virtual antlrcpp::Any visitProcedural_stmt(PSSParser::Procedural_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_block_stmt(PSSParser::Procedural_block_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_var_decl_stmt(PSSParser::Procedural_var_decl_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_expr_stmt(PSSParser::Procedural_expr_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_return_stmt(PSSParser::Procedural_return_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_if_else_stmt(PSSParser::Procedural_if_else_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_match_stmt(PSSParser::Procedural_match_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_match_choice(PSSParser::Procedural_match_choiceContext *context) override;

    virtual antlrcpp::Any visitProcedural_repeat_stmt(PSSParser::Procedural_repeat_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_foreach_stmt(PSSParser::Procedural_foreach_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_break_stmt(PSSParser::Procedural_break_stmtContext *context) override;

    virtual antlrcpp::Any visitProcedural_continue_stmt(PSSParser::Procedural_continue_stmtContext *context) override;

    virtual antlrcpp::Any visitComponent_declaration(PSSParser::Component_declarationContext *context) override;

    virtual antlrcpp::Any visitComponent_super_spec(PSSParser::Component_super_specContext *context) override;

    virtual antlrcpp::Any visitComponent_body_item(PSSParser::Component_body_itemContext *context) override;

    virtual antlrcpp::Any visitComponent_field_declaration(PSSParser::Component_field_declarationContext *context) override;

    virtual antlrcpp::Any visitComponent_data_declaration(PSSParser::Component_data_declarationContext *context) override;

    virtual antlrcpp::Any visitComponent_pool_declaration(PSSParser::Component_pool_declarationContext *context) override;

    virtual antlrcpp::Any visitObject_bind_stmt(PSSParser::Object_bind_stmtContext *context) override;

    virtual antlrcpp::Any visitObject_bind_item_or_list(PSSParser::Object_bind_item_or_listContext *context) override;

    virtual antlrcpp::Any visitComponent_path(PSSParser::Component_pathContext *context) override;

    virtual antlrcpp::Any visitComponent_path_elem(PSSParser::Component_path_elemContext *context) override;

    virtual antlrcpp::Any visitActivity_stmt(PSSParser::Activity_stmtContext *context) override;

    virtual antlrcpp::Any visitLabeled_activity_stmt(PSSParser::Labeled_activity_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_if_else_stmt(PSSParser::Activity_if_else_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_repeat_stmt(PSSParser::Activity_repeat_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_replicate_stmt(PSSParser::Activity_replicate_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_sequence_block_stmt(PSSParser::Activity_sequence_block_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_constraint_stmt(PSSParser::Activity_constraint_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_foreach_stmt(PSSParser::Activity_foreach_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_action_traversal_stmt(PSSParser::Activity_action_traversal_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_select_stmt(PSSParser::Activity_select_stmtContext *context) override;

    virtual antlrcpp::Any visitSelect_branch(PSSParser::Select_branchContext *context) override;

    virtual antlrcpp::Any visitActivity_match_stmt(PSSParser::Activity_match_stmtContext *context) override;

    virtual antlrcpp::Any visitMatch_choice(PSSParser::Match_choiceContext *context) override;

    virtual antlrcpp::Any visitActivity_parallel_stmt(PSSParser::Activity_parallel_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_schedule_stmt(PSSParser::Activity_schedule_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_join_spec(PSSParser::Activity_join_specContext *context) override;

    virtual antlrcpp::Any visitActivity_join_branch_spec(PSSParser::Activity_join_branch_specContext *context) override;

    virtual antlrcpp::Any visitActivity_join_select_spec(PSSParser::Activity_join_select_specContext *context) override;

    virtual antlrcpp::Any visitActivity_join_none_spec(PSSParser::Activity_join_none_specContext *context) override;

    virtual antlrcpp::Any visitActivity_join_first_spec(PSSParser::Activity_join_first_specContext *context) override;

    virtual antlrcpp::Any visitActivity_bind_stmt(PSSParser::Activity_bind_stmtContext *context) override;

    virtual antlrcpp::Any visitActivity_bind_item_or_list(PSSParser::Activity_bind_item_or_listContext *context) override;

    virtual antlrcpp::Any visitSymbol_declaration(PSSParser::Symbol_declarationContext *context) override;

    virtual antlrcpp::Any visitSymbol_paramlist(PSSParser::Symbol_paramlistContext *context) override;

    virtual antlrcpp::Any visitSymbol_param(PSSParser::Symbol_paramContext *context) override;

    virtual antlrcpp::Any visitActivity_super_stmt(PSSParser::Activity_super_stmtContext *context) override;

    virtual antlrcpp::Any visitOverrides_declaration(PSSParser::Overrides_declarationContext *context) override;

    virtual antlrcpp::Any visitOverride_stmt(PSSParser::Override_stmtContext *context) override;

    virtual antlrcpp::Any visitType_override(PSSParser::Type_overrideContext *context) override;

    virtual antlrcpp::Any visitInstance_override(PSSParser::Instance_overrideContext *context) override;

    virtual antlrcpp::Any visitData_declaration(PSSParser::Data_declarationContext *context) override;

    virtual antlrcpp::Any visitData_instantiation(PSSParser::Data_instantiationContext *context) override;

    virtual antlrcpp::Any visitArray_dim(PSSParser::Array_dimContext *context) override;

    virtual antlrcpp::Any visitData_type(PSSParser::Data_typeContext *context) override;

    virtual antlrcpp::Any visitContainer_type(PSSParser::Container_typeContext *context) override;

    virtual antlrcpp::Any visitArray_size_expression(PSSParser::Array_size_expressionContext *context) override;

    virtual antlrcpp::Any visitContainer_elem_type(PSSParser::Container_elem_typeContext *context) override;

    virtual antlrcpp::Any visitContainer_key_type(PSSParser::Container_key_typeContext *context) override;

    virtual antlrcpp::Any visitScalar_data_type(PSSParser::Scalar_data_typeContext *context) override;

    virtual antlrcpp::Any visitChandle_type(PSSParser::Chandle_typeContext *context) override;

    virtual antlrcpp::Any visitInteger_type(PSSParser::Integer_typeContext *context) override;

    virtual antlrcpp::Any visitInteger_atom_type(PSSParser::Integer_atom_typeContext *context) override;

    virtual antlrcpp::Any visitDomain_open_range_list(PSSParser::Domain_open_range_listContext *context) override;

    virtual antlrcpp::Any visitDomain_open_range_value(PSSParser::Domain_open_range_valueContext *context) override;

    virtual antlrcpp::Any visitString_type(PSSParser::String_typeContext *context) override;

    virtual antlrcpp::Any visitBool_type(PSSParser::Bool_typeContext *context) override;

    virtual antlrcpp::Any visitUser_defined_datatype(PSSParser::User_defined_datatypeContext *context) override;

    virtual antlrcpp::Any visitEnum_declaration(PSSParser::Enum_declarationContext *context) override;

    virtual antlrcpp::Any visitEnum_item(PSSParser::Enum_itemContext *context) override;

    virtual antlrcpp::Any visitEnum_type(PSSParser::Enum_typeContext *context) override;

    virtual antlrcpp::Any visitEnum_type_identifier(PSSParser::Enum_type_identifierContext *context) override;

    virtual antlrcpp::Any visitTypedef_declaration(PSSParser::Typedef_declarationContext *context) override;

    virtual antlrcpp::Any visitTemplate_param_decl_list(PSSParser::Template_param_decl_listContext *context) override;

    virtual antlrcpp::Any visitTemplate_param_decl(PSSParser::Template_param_declContext *context) override;

    virtual antlrcpp::Any visitType_param_decl(PSSParser::Type_param_declContext *context) override;

    virtual antlrcpp::Any visitGeneric_type_param_decl(PSSParser::Generic_type_param_declContext *context) override;

    virtual antlrcpp::Any visitCategory_type_param_decl(PSSParser::Category_type_param_declContext *context) override;

    virtual antlrcpp::Any visitType_restriction(PSSParser::Type_restrictionContext *context) override;

    virtual antlrcpp::Any visitType_category(PSSParser::Type_categoryContext *context) override;

    virtual antlrcpp::Any visitValue_param_decl(PSSParser::Value_param_declContext *context) override;

    virtual antlrcpp::Any visitTemplate_param_value_list(PSSParser::Template_param_value_listContext *context) override;

    virtual antlrcpp::Any visitTemplate_param_value(PSSParser::Template_param_valueContext *context) override;

    virtual antlrcpp::Any visitConstraint_declaration(PSSParser::Constraint_declarationContext *context) override;

    virtual antlrcpp::Any visitConstraint_body_item(PSSParser::Constraint_body_itemContext *context) override;

    virtual antlrcpp::Any visitDefault_constraint_item(PSSParser::Default_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitDefault_constraint(PSSParser::Default_constraintContext *context) override;

    virtual antlrcpp::Any visitDefault_disable_constraint(PSSParser::Default_disable_constraintContext *context) override;

    virtual antlrcpp::Any visitForall_constraint_item(PSSParser::Forall_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitExpression_constraint_item(PSSParser::Expression_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitImplication_constraint_item(PSSParser::Implication_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitConstraint_set(PSSParser::Constraint_setContext *context) override;

    virtual antlrcpp::Any visitConstraint_block(PSSParser::Constraint_blockContext *context) override;

    virtual antlrcpp::Any visitForeach_constraint_item(PSSParser::Foreach_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitIf_constraint_item(PSSParser::If_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *context) override;

    virtual antlrcpp::Any visitSingle_stmt_constraint(PSSParser::Single_stmt_constraintContext *context) override;

    virtual antlrcpp::Any visitCovergroup_declaration(PSSParser::Covergroup_declarationContext *context) override;

    virtual antlrcpp::Any visitCovergroup_port(PSSParser::Covergroup_portContext *context) override;

    virtual antlrcpp::Any visitCovergroup_body_item(PSSParser::Covergroup_body_itemContext *context) override;

    virtual antlrcpp::Any visitCovergroup_option(PSSParser::Covergroup_optionContext *context) override;

    virtual antlrcpp::Any visitCovergroup_instantiation(PSSParser::Covergroup_instantiationContext *context) override;

    virtual antlrcpp::Any visitInline_covergroup(PSSParser::Inline_covergroupContext *context) override;

    virtual antlrcpp::Any visitCovergroup_type_instantiation(PSSParser::Covergroup_type_instantiationContext *context) override;

    virtual antlrcpp::Any visitCovergroup_portmap_list(PSSParser::Covergroup_portmap_listContext *context) override;

    virtual antlrcpp::Any visitCovergroup_portmap(PSSParser::Covergroup_portmapContext *context) override;

    virtual antlrcpp::Any visitCovergroup_coverpoint(PSSParser::Covergroup_coverpointContext *context) override;

    virtual antlrcpp::Any visitBins_or_empty(PSSParser::Bins_or_emptyContext *context) override;

    virtual antlrcpp::Any visitCovergroup_coverpoint_body_item(PSSParser::Covergroup_coverpoint_body_itemContext *context) override;

    virtual antlrcpp::Any visitCovergroup_coverpoint_binspec(PSSParser::Covergroup_coverpoint_binspecContext *context) override;

    virtual antlrcpp::Any visitCoverpoint_bins(PSSParser::Coverpoint_binsContext *context) override;

    virtual antlrcpp::Any visitCovergroup_range_list(PSSParser::Covergroup_range_listContext *context) override;

    virtual antlrcpp::Any visitCovergroup_value_range(PSSParser::Covergroup_value_rangeContext *context) override;

    virtual antlrcpp::Any visitBins_keyword(PSSParser::Bins_keywordContext *context) override;

    virtual antlrcpp::Any visitCovergroup_cross(PSSParser::Covergroup_crossContext *context) override;

    virtual antlrcpp::Any visitCross_item_or_null(PSSParser::Cross_item_or_nullContext *context) override;

    virtual antlrcpp::Any visitCovergroup_cross_body_item(PSSParser::Covergroup_cross_body_itemContext *context) override;

    virtual antlrcpp::Any visitCovergroup_cross_binspec(PSSParser::Covergroup_cross_binspecContext *context) override;

    virtual antlrcpp::Any visitCovergroup_expression(PSSParser::Covergroup_expressionContext *context) override;

    virtual antlrcpp::Any visitPackage_body_compile_if(PSSParser::Package_body_compile_ifContext *context) override;

    virtual antlrcpp::Any visitPackage_body_compile_if_item(PSSParser::Package_body_compile_if_itemContext *context) override;

    virtual antlrcpp::Any visitAction_body_compile_if(PSSParser::Action_body_compile_ifContext *context) override;

    virtual antlrcpp::Any visitAction_body_compile_if_item(PSSParser::Action_body_compile_if_itemContext *context) override;

    virtual antlrcpp::Any visitComponent_body_compile_if(PSSParser::Component_body_compile_ifContext *context) override;

    virtual antlrcpp::Any visitComponent_body_compile_if_item(PSSParser::Component_body_compile_if_itemContext *context) override;

    virtual antlrcpp::Any visitStruct_body_compile_if(PSSParser::Struct_body_compile_ifContext *context) override;

    virtual antlrcpp::Any visitStruct_body_compile_if_item(PSSParser::Struct_body_compile_if_itemContext *context) override;

    virtual antlrcpp::Any visitCompile_has_expr(PSSParser::Compile_has_exprContext *context) override;

    virtual antlrcpp::Any visitCompile_assert_stmt(PSSParser::Compile_assert_stmtContext *context) override;

    virtual antlrcpp::Any visitConstant_expression(PSSParser::Constant_expressionContext *context) override;

    virtual antlrcpp::Any visitExpression(PSSParser::ExpressionContext *context) override;

    virtual antlrcpp::Any visitConditional_expr(PSSParser::Conditional_exprContext *context) override;

    virtual antlrcpp::Any visitLogical_or_op(PSSParser::Logical_or_opContext *context) override;

    virtual antlrcpp::Any visitLogical_and_op(PSSParser::Logical_and_opContext *context) override;

    virtual antlrcpp::Any visitBinary_or_op(PSSParser::Binary_or_opContext *context) override;

    virtual antlrcpp::Any visitBinary_xor_op(PSSParser::Binary_xor_opContext *context) override;

    virtual antlrcpp::Any visitBinary_and_op(PSSParser::Binary_and_opContext *context) override;

    virtual antlrcpp::Any visitInside_expr_term(PSSParser::Inside_expr_termContext *context) override;

    virtual antlrcpp::Any visitOpen_range_list(PSSParser::Open_range_listContext *context) override;

    virtual antlrcpp::Any visitOpen_range_value(PSSParser::Open_range_valueContext *context) override;

    virtual antlrcpp::Any visitLogical_inequality_op(PSSParser::Logical_inequality_opContext *context) override;

    virtual antlrcpp::Any visitUnary_op(PSSParser::Unary_opContext *context) override;

    virtual antlrcpp::Any visitExp_op(PSSParser::Exp_opContext *context) override;

    virtual antlrcpp::Any visitPrimary(PSSParser::PrimaryContext *context) override;

    virtual antlrcpp::Any visitParen_expr(PSSParser::Paren_exprContext *context) override;

    virtual antlrcpp::Any visitCast_expression(PSSParser::Cast_expressionContext *context) override;

    virtual antlrcpp::Any visitCasting_type(PSSParser::Casting_typeContext *context) override;

    virtual antlrcpp::Any visitVariable_ref_path(PSSParser::Variable_ref_pathContext *context) override;

    virtual antlrcpp::Any visitMethod_function_symbol_call(PSSParser::Method_function_symbol_callContext *context) override;

    virtual antlrcpp::Any visitMethod_call(PSSParser::Method_callContext *context) override;

    virtual antlrcpp::Any visitFunction_symbol_call(PSSParser::Function_symbol_callContext *context) override;

    virtual antlrcpp::Any visitFunction_symbol_id(PSSParser::Function_symbol_idContext *context) override;

    virtual antlrcpp::Any visitFunction_id(PSSParser::Function_idContext *context) override;

    virtual antlrcpp::Any visitStatic_ref_path(PSSParser::Static_ref_pathContext *context) override;

    virtual antlrcpp::Any visitStatic_ref_path_elem(PSSParser::Static_ref_path_elemContext *context) override;

    virtual antlrcpp::Any visitMul_div_mod_op(PSSParser::Mul_div_mod_opContext *context) override;

    virtual antlrcpp::Any visitAdd_sub_op(PSSParser::Add_sub_opContext *context) override;

    virtual antlrcpp::Any visitShift_op(PSSParser::Shift_opContext *context) override;

    virtual antlrcpp::Any visitEq_neq_op(PSSParser::Eq_neq_opContext *context) override;

    virtual antlrcpp::Any visitConstant(PSSParser::ConstantContext *context) override;

    virtual antlrcpp::Any visitIdentifier(PSSParser::IdentifierContext *context) override;

    virtual antlrcpp::Any visitHierarchical_id_list(PSSParser::Hierarchical_id_listContext *context) override;

    virtual antlrcpp::Any visitHierarchical_id(PSSParser::Hierarchical_idContext *context) override;

    virtual antlrcpp::Any visitHierarchical_id_elem(PSSParser::Hierarchical_id_elemContext *context) override;

    virtual antlrcpp::Any visitAction_type_identifier(PSSParser::Action_type_identifierContext *context) override;

    virtual antlrcpp::Any visitType_identifier(PSSParser::Type_identifierContext *context) override;

    virtual antlrcpp::Any visitType_identifier_elem(PSSParser::Type_identifier_elemContext *context) override;

    virtual antlrcpp::Any visitPackage_identifier(PSSParser::Package_identifierContext *context) override;

    virtual antlrcpp::Any visitCovercross_identifier(PSSParser::Covercross_identifierContext *context) override;

    virtual antlrcpp::Any visitCovergroup_identifier(PSSParser::Covergroup_identifierContext *context) override;

    virtual antlrcpp::Any visitCoverpoint_target_identifier(PSSParser::Coverpoint_target_identifierContext *context) override;

    virtual antlrcpp::Any visitAction_identifier(PSSParser::Action_identifierContext *context) override;

    virtual antlrcpp::Any visitStruct_identifier(PSSParser::Struct_identifierContext *context) override;

    virtual antlrcpp::Any visitComponent_identifier(PSSParser::Component_identifierContext *context) override;

    virtual antlrcpp::Any visitComponent_action_identifier(PSSParser::Component_action_identifierContext *context) override;

    virtual antlrcpp::Any visitCoverpoint_identifier(PSSParser::Coverpoint_identifierContext *context) override;

    virtual antlrcpp::Any visitEnum_identifier(PSSParser::Enum_identifierContext *context) override;

    virtual antlrcpp::Any visitImport_class_identifier(PSSParser::Import_class_identifierContext *context) override;

    virtual antlrcpp::Any visitLabel_identifier(PSSParser::Label_identifierContext *context) override;

    virtual antlrcpp::Any visitLanguage_identifier(PSSParser::Language_identifierContext *context) override;

    virtual antlrcpp::Any visitMethod_identifier(PSSParser::Method_identifierContext *context) override;

    virtual antlrcpp::Any visitSymbol_identifier(PSSParser::Symbol_identifierContext *context) override;

    virtual antlrcpp::Any visitVariable_identifier(PSSParser::Variable_identifierContext *context) override;

    virtual antlrcpp::Any visitIterator_identifier(PSSParser::Iterator_identifierContext *context) override;

    virtual antlrcpp::Any visitIndex_identifier(PSSParser::Index_identifierContext *context) override;

    virtual antlrcpp::Any visitBuffer_type_identifier(PSSParser::Buffer_type_identifierContext *context) override;

    virtual antlrcpp::Any visitCovergroup_type_identifier(PSSParser::Covergroup_type_identifierContext *context) override;

    virtual antlrcpp::Any visitResource_type_identifier(PSSParser::Resource_type_identifierContext *context) override;

    virtual antlrcpp::Any visitState_type_identifier(PSSParser::State_type_identifierContext *context) override;

    virtual antlrcpp::Any visitStream_type_identifier(PSSParser::Stream_type_identifierContext *context) override;

    virtual antlrcpp::Any visitBool_literal(PSSParser::Bool_literalContext *context) override;

    virtual antlrcpp::Any visitNumber(PSSParser::NumberContext *context) override;

    virtual antlrcpp::Any visitBased_hex_number(PSSParser::Based_hex_numberContext *context) override;

    virtual antlrcpp::Any visitBased_dec_number(PSSParser::Based_dec_numberContext *context) override;

    virtual antlrcpp::Any visitDec_number(PSSParser::Dec_numberContext *context) override;

    virtual antlrcpp::Any visitBased_bin_number(PSSParser::Based_bin_numberContext *context) override;

    virtual antlrcpp::Any visitBased_oct_number(PSSParser::Based_oct_numberContext *context) override;

    virtual antlrcpp::Any visitOct_number(PSSParser::Oct_numberContext *context) override;

    virtual antlrcpp::Any visitHex_number(PSSParser::Hex_numberContext *context) override;

    virtual antlrcpp::Any visitString(PSSParser::StringContext *context) override;

    virtual antlrcpp::Any visitFilename_string(PSSParser::Filename_stringContext *context) override;

    virtual antlrcpp::Any visitExport_action(PSSParser::Export_actionContext *context) override;

    virtual antlrcpp::Any visitImport_class_decl(PSSParser::Import_class_declContext *context) override;

    virtual antlrcpp::Any visitImport_class_extends(PSSParser::Import_class_extendsContext *context) override;

    virtual antlrcpp::Any visitImport_class_method_decl(PSSParser::Import_class_method_declContext *context) override;

    virtual void syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) override;

private:
    void addChild(ScopeChild *c, Token *t);

    void addChild(NamedScopeChild *c, Token *t);

    void addChild(NamedScope *c, Token *t);

    void addDocstring(ScopeChild *c, Token *t);

    std::string processDocStringMultiLineComment(
    		const std::vector<Token *>		&mlc_tokens,
			const std::vector<Token *>		&ws_tokens);

    std::string processDocStringSingleLineComment(
    		const std::vector<Token *>		&slc_tokens,
			const std::vector<Token *>		&ws_tokens);

    Scope *scope() const { return m_scopes.back(); }

    void push_scope(Scope *s) { m_scopes.push_back(s); }

    void pop_scope() { m_scopes.pop_back(); }

private:
    IMarkerListener						*m_marker_l;
    std::vector<Scope *>				m_scopes;
    std::unique_ptr<CommonTokenStream>	m_tokens;

};

}

