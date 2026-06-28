/*
 * AstBuilderInt.h
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <istream>
#include "dmgr/IDebugMgr.h"
#include "pssp/IMarkerListener.h"
#include "PSSParserBaseVisitor.h"
#include "BaseErrorListener.h"
#include "atn/ParseInfo.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IScope.h"
#include "pssp/ast/IEnumDecl.h"

using namespace antlr4;
using namespace antlrcpp;

namespace pssp {



class AstBuilderInt :
		public PSSParserBaseVisitor,
		public BaseErrorListener {
public:
	AstBuilderInt(
        dmgr::IDebugMgr         *dmgr,
		ast::IFactory			*factory,
		IMarkerListener 		*marker_l);

	virtual ~AstBuilderInt();

	void build(
			ast::IGlobalScope	*global,
			std::istream 		*in);

    pssp::ast::IFactory *getFactory() {
        return m_factory;
    }

    void setMarkerListener(IMarkerListener *l) {
        m_marker_l = l;
    }

    virtual void setCollectDocStrings(bool c) {
        m_collectDocStrings = c;
    }

    virtual bool getCollectDocStrings() {
        return m_collectDocStrings;
    }

    virtual void setEnableProfile(bool e) {
        m_enableProfile = e;
    }

    virtual bool getEnableProfile() {
        return m_enableProfile;
    }

    virtual bool hasProfileInfo() const {
        return !m_profile_decisions.empty();
    }

    virtual const std::vector<atn::DecisionInfo> *getProfileInfo() const {
        return m_profile_decisions.empty() ? nullptr : &m_profile_decisions;
    }

	// B.1 package declaration
	virtual antlrcpp::Any visitPackage_declaration(PSSParser::Package_declarationContext *ctx) override;

    virtual antlrcpp::Any visitPackage_body_compile_if(PSSParser::Package_body_compile_ifContext *ctx) override;

    virtual antlrcpp::Any visitAnnotation_body_compile_if(PSSParser::Annotation_body_compile_ifContext *ctx) override;

    virtual antlrcpp::Any visitCompile_assert_stmt(PSSParser::Compile_assert_stmtContext *ctx) override;

	virtual antlrcpp::Any visitImport_stmt(PSSParser::Import_stmtContext *ctx) override;

	virtual antlrcpp::Any visitPyimport_single_module(PSSParser::Pyimport_single_moduleContext *ctx) override;

    virtual antlrcpp::Any visitPyimport_from_module(PSSParser::Pyimport_from_moduleContext *ctx) override;

	virtual antlrcpp::Any visitExtend_stmt(PSSParser::Extend_stmtContext *ctx) override;

	virtual antlrcpp::Any visitAnnotation_declaration(PSSParser::Annotation_declarationContext *ctx) override;

	virtual antlrcpp::Any visitAnnotation_attr_field(PSSParser::Annotation_attr_fieldContext *ctx) override;

	virtual antlrcpp::Any visitAnnotation(PSSParser::AnnotationContext *ctx) override;

	virtual antlrcpp::Any visitConst_field_declaration(PSSParser::Const_field_declarationContext *ctx) override;

	// B.2 Action declaration

	virtual antlrcpp::Any visitAction_declaration(PSSParser::Action_declarationContext *ctx) override;

	virtual antlrcpp::Any visitAbstract_action_declaration(PSSParser::Abstract_action_declarationContext *ctx);

    virtual antlrcpp::Any visitOverride_action_declaration(PSSParser::Override_action_declarationContext *ctx) override;

    virtual antlrcpp::Any visitActivity_bind_stmt(PSSParser::Activity_bind_stmtContext *ctx) override;

    virtual antlrcpp::Any visitActivity_declaration(PSSParser::Activity_declarationContext *ctx) override;

    virtual antlrcpp::Any visitAction_body_compile_if(PSSParser::Action_body_compile_ifContext *ctx) override;

	virtual antlrcpp::Any visitFlow_ref_field_declaration(PSSParser::Flow_ref_field_declarationContext *ctx) override;
	
	virtual antlrcpp::Any visitResource_ref_field_declaration(PSSParser::Resource_ref_field_declarationContext *ctx) override;

	virtual antlrcpp::Any visitComponent_pool_declaration(PSSParser::Component_pool_declarationContext *ctx) override;

	virtual antlrcpp::Any visitObject_bind_stmt(PSSParser::Object_bind_stmtContext *ctx) override;

	virtual antlrcpp::Any visitInline_covergroup(PSSParser::Inline_covergroupContext *ctx) override;

    virtual antlrcpp::Any visitAction_handle_declaration(PSSParser::Action_handle_declarationContext *ctx) override;

	virtual antlrcpp::Any visitActivity_data_field(PSSParser::Activity_data_fieldContext *ctx) override;

	// B.3 Struct declarations
	virtual antlrcpp::Any visitStruct_declaration(PSSParser::Struct_declarationContext *ctx) override;

    virtual antlrcpp::Any visitStruct_body_compile_if(PSSParser::Struct_body_compile_ifContext *ctx) override;

	// B.4 Exec blocks
    virtual antlrcpp::Any visitExec_block(PSSParser::Exec_blockContext *ctx) override;

    virtual antlrcpp::Any visitTarget_code_exec_block(PSSParser::Target_code_exec_blockContext *ctx) override;

    virtual antlrcpp::Any visitTarget_file_exec_block(PSSParser::Target_file_exec_blockContext *ctx) override;

    virtual antlrcpp::Any visitExec_super_stmt(PSSParser::Exec_super_stmtContext *ctx) override;
    
	// B.5 Functions
    virtual antlrcpp::Any visitProcedural_function(PSSParser::Procedural_functionContext *ctx) override;

    virtual antlrcpp::Any visitFunction_decl(PSSParser::Function_declContext *ctx) override;

    virtual antlrcpp::Any visitFunction_prototype(PSSParser::Function_prototypeContext *ctx) override;

    virtual antlrcpp::Any visitImport_function(PSSParser::Import_functionContext *ctx) override;

    virtual antlrcpp::Any visitExport_function(PSSParser::Export_functionContext *ctx) override;

	// B.7 Procedural Statements
    virtual antlrcpp::Any visitProcedural_sequence_block_stmt(PSSParser::Procedural_sequence_block_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_assignment_stmt(PSSParser::Procedural_assignment_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_void_function_call_stmt(PSSParser::Procedural_void_function_call_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_return_stmt(PSSParser::Procedural_return_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_repeat_stmt(PSSParser::Procedural_repeat_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_foreach_stmt(PSSParser::Procedural_foreach_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_if_else_stmt(PSSParser::Procedural_if_else_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_match_stmt(PSSParser::Procedural_match_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_break_stmt(PSSParser::Procedural_break_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_continue_stmt(PSSParser::Procedural_continue_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_data_declaration(PSSParser::Procedural_data_declarationContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_yield_stmt(PSSParser::Procedural_yield_stmtContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_randomization_stmt(PSSParser::Procedural_randomization_stmtContext *ctx) override;

	// B.8 Component declarations

	virtual antlrcpp::Any visitComponent_declaration(PSSParser::Component_declarationContext *ctx) override;

    virtual antlrcpp::Any visitComponent_data_declaration(PSSParser::Component_data_declarationContext *ctx) override;

	virtual antlrcpp::Any visitComponent_body_compile_if(PSSParser::Component_body_compile_ifContext *ctx) override;

    virtual antlrcpp::Any visitMonitor_body_compile_if(PSSParser::Monitor_body_compile_ifContext *ctx) override;

	// Monitor declarations (PSS 3.0)
	virtual antlrcpp::Any visitMonitor_declaration(PSSParser::Monitor_declarationContext *ctx) override;

	virtual antlrcpp::Any visitAbstract_monitor_declaration(PSSParser::Abstract_monitor_declarationContext *ctx);

	virtual antlrcpp::Any visitMonitor_activity_declaration(PSSParser::Monitor_activity_declarationContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_sequence_block_stmt(PSSParser::Monitor_activity_sequence_block_stmtContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_concat_stmt(PSSParser::Monitor_activity_concat_stmtContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_eventually_stmt(PSSParser::Monitor_activity_eventually_stmtContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_overlap_stmt(PSSParser::Monitor_activity_overlap_stmtContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_schedule_stmt(PSSParser::Monitor_activity_schedule_stmtContext *ctx) override;

	virtual antlrcpp::Any visitMonitor_activity_monitor_traversal_stmt(PSSParser::Monitor_activity_monitor_traversal_stmtContext *ctx) override;

	virtual antlrcpp::Any visitCover_stmt(PSSParser::Cover_stmtContext *ctx) override;

	// B.9 Activity statements

	virtual antlrcpp::Any visitActivity_labeled_stmt(PSSParser::Activity_labeled_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_action_traversal_stmt(PSSParser::Activity_action_traversal_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_sequence_block_stmt(PSSParser::Activity_sequence_block_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_parallel_stmt(PSSParser::Activity_parallel_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_schedule_stmt(PSSParser::Activity_schedule_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_repeat_stmt(PSSParser::Activity_repeat_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_atomic_block_stmt(PSSParser::Activity_atomic_block_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_select_stmt(PSSParser::Activity_select_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_if_else_stmt(PSSParser::Activity_if_else_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_match_stmt(PSSParser::Activity_match_stmtContext *ctx) override;

	virtual antlrcpp::Any visitActivity_foreach_stmt(PSSParser::Activity_foreach_stmtContext *ctx) override;

	// B.11 Data declarations

	virtual antlrcpp::Any visitData_declaration(PSSParser::Data_declarationContext *ctx) override;

	virtual antlrcpp::Any visitAttr_field(PSSParser::Attr_fieldContext *ctx) override;

	// B.13 Data types

 	virtual antlrcpp::Any visitChandle_type(PSSParser::Chandle_typeContext *ctx) override;

	virtual antlrcpp::Any visitInteger_type(PSSParser::Integer_typeContext *ctx) override;

    virtual antlrcpp::Any visitString_type(PSSParser::String_typeContext *context) override;

	virtual antlrcpp::Any visitBool_type(PSSParser::Bool_typeContext *ctx) override;

	virtual antlrcpp::Any visitEnum_type(PSSParser::Enum_typeContext *ctx) override;
	
    virtual antlrcpp::Any visitEnum_declaration(PSSParser::Enum_declarationContext *ctx) override;

    virtual antlrcpp::Any visitPyobj_type(PSSParser::Pyobj_typeContext *ctx) override;

    virtual antlrcpp::Any visitTypedef_declaration(PSSParser::Typedef_declarationContext *ctx) override;

	virtual antlrcpp::Any visitReference_type(PSSParser::Reference_typeContext *ctx) override;

	// B.14 Constraints
	virtual antlrcpp::Any visitConstraint_declaration(PSSParser::Constraint_declarationContext *ctx) override;

    virtual antlrcpp::Any visitGeneric_constraint_bool(PSSParser::Generic_constraint_boolContext *ctx) override;

    virtual antlrcpp::Any visitGeneric_constraint_value(PSSParser::Generic_constraint_valueContext *ctx) override;

//	virtual antlrcpp::Any visitConstraint_set(PSSParser::Constraint_setContext *ctx) override;

	virtual antlrcpp::Any visitConstraint_block(PSSParser::Constraint_blockContext *ctx) override;

    virtual antlrcpp::Any visitConstraint_body_compile_if(PSSParser::Constraint_body_compile_ifContext *ctx) override;

	virtual antlrcpp::Any visitDefault_constraint(PSSParser::Default_constraintContext *ctx) override;

	virtual antlrcpp::Any visitDefault_disable_constraint(PSSParser::Default_disable_constraintContext *ctx) override;

	virtual antlrcpp::Any visitExpression_constraint_item(PSSParser::Expression_constraint_itemContext *ctx) override;

    virtual antlrcpp::Any visitProcedural_compile_if(PSSParser::Procedural_compile_ifContext *ctx) override;

    virtual antlrcpp::Any visitCovergroup_body_compile_if(PSSParser::Covergroup_body_compile_ifContext *ctx) override;

    virtual antlrcpp::Any visitOverride_compile_if(PSSParser::Override_compile_ifContext *ctx) override;

	virtual antlrcpp::Any visitForeach_constraint_item(PSSParser::Foreach_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitForall_constraint_item(PSSParser::Forall_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitIf_constraint_item(PSSParser::If_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitImplication_constraint_item(PSSParser::Implication_constraint_itemContext *ctx) override;
	
	virtual antlrcpp::Any visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *ctx) override;

	void visitConstraintSetItems(PSSParser::Constraint_setContext *ctx);

	// B.17 Expressions

	virtual antlrcpp::Any visitExpression(PSSParser::ExpressionContext *ctx) override;

	virtual antlrcpp::Any visitBool_literal(PSSParser::Bool_literalContext *ctx) override;

	virtual antlrcpp::Any visitString_literal(PSSParser::String_literalContext *ctx) override;

	virtual antlrcpp::Any visitNull_ref(PSSParser::Null_refContext *ctx) override;

	virtual antlrcpp::Any visitCast_expression(PSSParser::Cast_expressionContext *ctx) override;

	virtual antlrcpp::Any visitRef_path(PSSParser::Ref_pathContext *ctx) override;

    virtual antlrcpp::Any visitCompile_has_expr(PSSParser::Compile_has_exprContext *ctx) override;

	// B.18 Identifiers
	virtual antlrcpp::Any visitIdentifier(PSSParser::IdentifierContext *ctx) override;

    virtual antlrcpp::Any visitType_identifier(PSSParser::Type_identifierContext *context) override;


	// B.19 Numbers
	virtual antlrcpp::Any visitNumber(PSSParser::NumberContext *ctx) override;

    virtual antlrcpp::Any visitAggregate_literal(PSSParser::Aggregate_literalContext *ctx) override;

    virtual antlrcpp::Any visitEmpty_aggregate_literal(PSSParser::Empty_aggregate_literalContext *ctx) override;

    virtual antlrcpp::Any visitValue_list_literal(PSSParser::Value_list_literalContext *ctx) override;

    virtual antlrcpp::Any visitMap_literal(PSSParser::Map_literalContext *ctx) override;

    virtual antlrcpp::Any visitStruct_literal(PSSParser::Struct_literalContext *ctx) override;

    virtual void syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) override;


private:

    void addChild(ast::IScopeChild *c, Token *t, const ast::Location *loc=0, Token *ct=0);

    void addChild(ast::ISymbolScope *c, Token *t, Token *end);

    void addChild(ast::INamedScopeChild *c, Token *t);

    void addChild(ast::IConstraintScope *c, Token *start, Token *end);

    void addChild(ast::IExecScope *c, Token *start, Token *end);

    void addChild(ast::IFunctionDefinition *c, Token *start, Token *end);

    void addChild(ast::INamedScope *c, Token *start, Token *end);

    void addChild(ast::IScope *c, Token *start, Token *end);

    void addDocstring(ast::IScopeChild *c, Token *t);

    void attachPendingAnnotations(ast::IScopeChild *c);

    bool evalConstantExpression(PSSParser::Constant_expressionContext *ctx, int64_t &val);

    bool evalExpression(PSSParser::ExpressionContext *ctx, int64_t &val);

    bool evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, int64_t &val);

    bool evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, std::string &val);

    bool evalCompileHas(PSSParser::Ref_pathContext *ctx);

    void visitCompileIfItem(antlr4::ParserRuleContext *ctx);

    ast::IScope *getGlobalScope(ast::IScope *s);

    ast::IScopeChild *findNamedChild(ast::IScope *scope, const std::string &name);

    ast::IScopeChild *findNamedChildUp(ast::IScope *scope, const std::string &name);

    ast::IScopeChild *findPackagePath(
        ast::IScope *scope,
        const std::vector<std::string> &path,
        uint32_t &consumed);

    ast::IScope *resolveDataTypeScope(ast::IDataType *type);

    ast::IScopeChild *findImportedPathTarget(
        ast::IScope *start,
        const std::vector<std::string> &path);

    ast::IScopeChild *resolvePathTarget(
        ast::IScope *start,
        const std::vector<std::string> &path,
        bool is_global,
        bool search_imports=true);

    ast::IScopeChild *resolveRefPathTarget(PSSParser::Ref_pathContext *ctx);

    ast::IScopeChild *resolveRefPathTarget(ast::IScope *eval_scope, ast::IExprRefPath *expr);

    bool evalEnumItemExpression(ast::IEnumDecl *decl, ast::IExpr *expr, int64_t &val);
    bool evalScopeChildValue(ast::IScopeChild *target, int64_t &val);

    bool evalScopeChildValue(ast::IScopeChild *target, std::string &val);

    std::string processDocStringMultiLineComment(
    		const std::vector<Token *>		&mlc_tokens,
			const std::vector<Token *>		&ws_tokens);

    std::string processDocStringSingleLineComment(
    		const std::vector<Token *>		&slc_tokens,
			const std::vector<Token *>		&ws_tokens);

    ast::IScope *scope() const { return m_scopes.back(); }

    void push_scope(ast::IScope *s);

    void pop_scope();

	ast::IActivityJoinSpec *mkActivityJoinSpec(PSSParser::Activity_join_specContext *ctx);

    void addActivityStmt(
        ast::ISymbolScope                   *scope,
        PSSParser::Activity_stmt_annContext *ctx);

    void addSyntheticIntField(ast::ISymbolScope *scope, const std::string &name);
    void addStructBuiltinField(ast::IStruct *s, ast::StructKind kind);
	ast::IScopeChild *mkActivityStmt(PSSParser::Activity_stmt_annContext *ctx);

	ast::IConstraintStmt *mkConstraintSet(PSSParser::Constraint_setContext *ctx);

    std::vector<ast::IGenericConstraintParam *> mkGenericConstraintParams(
        PSSParser::Generic_constraint_paramsContext *ctx);

	ast::IDataType *mkDataType(PSSParser::Data_typeContext *ctx);

	ast::IDataTypeUserDefined *mkDataTypeUserDefined(PSSParser::Type_identifierContext *ctx);

    ast::IDataTypeUserDefined *mkDataTypeArray(
        ast::IDataType          *elem_t,
        ast::IExpr              *size);

	template <class T> T *mkDataTypeT(PSSParser::Data_typeContext *ctx) {
		return dynamic_cast<T *>(mkDataType(ctx));
	}

	ast::IExprDomainOpenRangeList *mkDomainOpenRangeList(PSSParser::Domain_open_range_listContext *ctx);

	ast::IExprOpenRangeList *mkOpenRangeList(PSSParser::Open_range_listContext *ctx);

    ast::IScopeChild *mkExecStmt(PSSParser::Procedural_stmtContext *ctx);

    void addExecStmt(PSSParser::Procedural_stmtContext *ctx);

    ast::IFunctionPrototype *mkFunctionPrototype(PSSParser::Function_prototypeContext *ctx);

    ast::IFunctionParamDecl *mkFunctionParamDecl(PSSParser::Function_parameterContext *ctx);

    std::vector<ast::IActionFieldInitializer *> mkActionFieldInitializers(
        PSSParser::Action_initializer_listContext    *ctx);

	ast::IExprId *mkId(PSSParser::IdentifierContext *ctx);

    std::string toString(PSSParser::IdentifierContext *ctx);

	ast::IExprHierarchicalId *mkHierarchicalId(PSSParser::Hierarchical_idContext *ctx);

	ast::IExprHierarchicalId *mkHierarchicalId(
        PSSParser::Static_ref_pathContext *root_ctx,
        PSSParser::Hierarchical_idContext *leaf_ctx);

	ast::IExprHierarchicalId *mkHierarchicalId(PSSParser::Member_path_elemContext *ctx);

    ast::IExprMemberPathElem *mkMemberPathElem(PSSParser::Member_path_elemContext *ctx);

	void mkTypeId(
		std::vector<ast::IExprIdUP>				&type_id,
		PSSParser::Type_identifierContext		*ctx);

	ast::ITypeIdentifier *mkTypeId(
		PSSParser::Type_identifierContext		*ctx);

	ast::ITypeIdentifierElem *mkTypeIdElem(
		PSSParser::Type_identifier_elemContext		*ctx);

	ast::ITypeIdentifierElem *mkTypeIdElem(
		PSSParser::IdentifierContext		    *ctx);

	ast::IExpr *mkExpr(
		PSSParser::ExpressionContext 			*ctx);

    ast::IExprBitSlice *mkExprBitSlice(
        PSSParser::Bit_sliceContext             *ctx);

    ast::IExprRefPath *mkExprRefPath(
        PSSParser::Ref_pathContext              *ctx);

    ast::IExprRefPathStatic *mkExprRefPathStatic(
        PSSParser::Static_ref_pathContext       *ctx);

    ast::ITemplateParamDeclList *mkTypeParamDecl(
        PSSParser::Template_param_decl_listContext *ctx);

    ast::ITemplateParamValueList *mkTemplateParamValueList(
        PSSParser::Template_param_value_listContext *ctx);

    void setLoc(ast::IScopeChild *c, Token *start);

    void setLoc(ast::IExprId *c, Token *start);

private:
    static dmgr::IDebug                         *m_dbg;
    int32_t                                     m_file_id;
	bool										m_collectDocStrings;
    bool                                        m_enableProfile;
    std::vector<atn::DecisionInfo>              m_profile_decisions;
    IMarkerListener								*m_marker_l;
	ast::IFactory								*m_factory;
	ast::IExpr									*m_expr;
	ast::IDataType								*m_type;
    std::vector<ast::IScope *>					m_scopes;
	ast::IScopeChild							*m_activity_stmt;
	ast::IExprId								*m_labeled_activity_id;
	ast::IConstraintStmt						*m_constraint;
    ast::IScopeChild                            *m_exec_stmt;
    int32_t                                     m_exec_stmt_cnt;
    std::vector<ast::IExecScope *>              m_exec_scope_s;
	std::vector<ast::IConstraintScope *>		m_constraint_s;
    std::unique_ptr<CommonTokenStream>			m_tokens;
	std::vector<ast::IExprIdUP>					*m_type_id;
	uint32_t									m_field_depth;
	std::vector<ast::IField *>					m_fields;
    std::vector<ast::IAnnotation *>            m_pending_annotations;

};

}
