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
#include "ParseProfileInfo.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IScope.h"
#include "pssp/ast/IEnumDecl.h"
#include "DocCommentExtractor.h"

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

    /**
     * Collect every comment, not just the docstring of a declaration.
     *
     * Populates ScopeChild::comments -- on procedural statements as well as
     * declarations -- and ScopeChild::trailing_comments. Implies docstring
     * collection, since the docstring is derived from the same leading run.
     */
    virtual void setCollectComments(bool c) {
        m_collectComments = c;
        if (c) {
            m_collectDocStrings = true;
        }
    }

    virtual bool getCollectComments() {
        return m_collectComments;
    }

    virtual void setDocCommentTabWidth(int32_t w) {
        m_doc_opts.tab_width = w;
        if (m_doc_extractor) {
            m_doc_extractor->setOptions(m_doc_opts);
        }
    }

    virtual int32_t getDocCommentTabWidth() {
        return m_doc_opts.tab_width;
    }

    virtual void setDocCommentStrictMarkers(bool s) {
        m_doc_opts.strict_markers = s;
        if (m_doc_extractor) {
            m_doc_extractor->setOptions(m_doc_opts);
        }
    }

    virtual bool getDocCommentStrictMarkers() {
        return m_doc_opts.strict_markers;
    }

    /**
     * Establish *tok* as the doc anchor until the matching pop.  Use
     * DocAnchorScope rather than calling these directly.
     */
    void pushDocAnchor(Token *tok) {
        m_doc_anchors.push_back(tok);
    }

    void popDocAnchor() {
        if (!m_doc_anchors.empty()) {
            m_doc_anchors.pop_back();
        }
    }

    virtual void setEnableProfile(bool e) {
        m_enableProfile = e;
    }

    virtual bool getEnableProfile() {
        return m_enableProfile;
    }

    virtual bool hasProfileInfo() const {
        return m_profile.get() != nullptr;
    }

    virtual const ProfileSnapshot *getProfileInfo() const {
        return m_profile.get();
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

    /** 20.6 -- `target C function void f(int a) = """...""";` */
    virtual antlrcpp::Any visitTarget_template_function(PSSParser::Target_template_functionContext *ctx) override;

    ast::IExecBlockTag *mkExecBlockTag(PSSParser::Exec_block_tagContext *ctx);

    /** 20.5.4 -- PSS106 when a tag is written on an exec kind that rejects it. */
    void checkExecBlockTagPlacement(
        PSSParser::Exec_block_tagContext *tag_ctx,
        ast::ExecKind                     kind,
        const std::string                &kind_s);

    virtual antlrcpp::Any visitExec_super_stmt(PSSParser::Exec_super_stmtContext *ctx) override;
    
	// B.5 Functions

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

	// The `*_ann` rules put an annotation between a doc comment and the
	// declaration it documents.  These overrides exist only to anchor the
	// comment lookup; they add nothing to the AST.
	virtual antlrcpp::Any visitAction_body_item_ann(PSSParser::Action_body_item_annContext *ctx) override;

	virtual antlrcpp::Any visitComponent_body_item_ann(PSSParser::Component_body_item_annContext *ctx) override;

	virtual antlrcpp::Any visitActivity_stmt_ann(PSSParser::Activity_stmt_annContext *ctx) override;

	// B.13 Data types

 	virtual antlrcpp::Any visitChandle_type(PSSParser::Chandle_typeContext *ctx) override;

	virtual antlrcpp::Any visitInteger_type(PSSParser::Integer_typeContext *ctx) override;

    virtual antlrcpp::Any visitString_type(PSSParser::String_typeContext *context) override;

	virtual antlrcpp::Any visitBool_type(PSSParser::Bool_typeContext *ctx) override;

	virtual antlrcpp::Any visitFloat_type(PSSParser::Float_typeContext *ctx) override;

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

    virtual antlrcpp::Any visitOverride_stmt(PSSParser::Override_stmtContext *ctx) override;

    virtual antlrcpp::Any visitCovergroup_body_item(PSSParser::Covergroup_body_itemContext *ctx) override;

	virtual antlrcpp::Any visitForeach_constraint_item(PSSParser::Foreach_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitForall_constraint_item(PSSParser::Forall_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitIf_constraint_item(PSSParser::If_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitImplication_constraint_item(PSSParser::Implication_constraint_itemContext *ctx) override;
	
	virtual antlrcpp::Any visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitSoft_constraint_item(PSSParser::Soft_constraint_itemContext *ctx) override;

	virtual antlrcpp::Any visitDist_directive(PSSParser::Dist_directiveContext *ctx) override;

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

    /**
     * @param stop           last token of the construct, for its source extent
     * @param trailing_stop  token a same-line trailing comment follows.  For a
     *                       field this is the statement's `;`, not the
     *                       declarator's last token: the `;` sits between the
     *                       declarator and the comment, so looking right from
     *                       the declarator finds nothing.  Defaults to *stop*.
     */
    void addChild(ast::IScopeChild *c, Token *t, const ast::Location *loc=0, Token *ct=0,
                  Token *stop=0, Token *trailing_stop=0);

    void addChild(ast::ISymbolScope *c, Token *t, Token *end);

    void addChild(ast::INamedScopeChild *c, Token *t);

    void addChild(ast::IConstraintScope *c, Token *start, Token *end);

    void addChild(ast::IExecScope *c, Token *start, Token *end);

    void addChild(ast::IFunctionDefinition *c, Token *start, Token *end);

    void addChild(ast::INamedScope *c, Token *start, Token *end);

    void addChild(ast::IScope *c, Token *start, Token *end);

    void addDocstring(ast::IScopeChild *c, Token *t, Token *stop=0);

    /**
     * Attach the doc comment (and, when enabled, the comments) leading *t* to
     * *c*, for nodes that are built into
     * a typed list rather than through addChild -- enum items, function
     * parameters and template parameters (D9).
     *
     * Unlike addDocstring this ignores any active DocAnchorScope.  These nodes
     * sit *inside* a declaration that may itself have an anchor, and each one
     * carries its own comment; taking the enclosing anchor would give every
     * item in the list the declaration's docstring.
     */
    void attachDocstring(ast::IScopeChild *c, Token *t);

    /** Record text, raw source, form and comment location on *c* (E4). */
    void applyDocComment(ast::IScopeChild *c, const DocComment &dc);

    static ast::DocCommentForm toAstDocForm(pssp::DocCommentForm form);

    /**
     * Record the source extent of a construct that runs from *start* to *stop*
     * (E6): `endLocation`, and `location.extent` as the character span.  Both
     * are needed for a `[source]` link that highlights a range rather than a
     * single line.
     */
    void setExtent(ast::IScopeChild *c, Token *start, Token *stop);

    /**
     * The token a doc comment is looked up from: the innermost anchor
     * established by a DocAnchorScope, or *fallback* (the token the
     * constructing visitor happens to hold) when none is in force.
     */
    Token *docAnchor(Token *fallback) const {
        if (!m_doc_anchors.empty() && m_doc_anchors.back()) {
            // Both anchors exist to move the lookup *earlier* than the token
            // the constructing visitor holds: this one past a wrapper rule's
            // leading tokens (`rand`, `static const`), and the caller's past
            // any annotations attached to the declaration. Whichever reaches
            // further back is the start of the construct as written, and that
            // is where the comment sits.
            //
            // Taking this one unconditionally lost the docstring on
            // `/** doc */ @ann {...} C c1;`: component_data_declaration
            // anchors at `C`, which is *after* the annotation, so the comment
            // was no longer adjacent.
            if (!fallback
                || m_doc_anchors.back()->getTokenIndex()
                        <= fallback->getTokenIndex()) {
                return m_doc_anchors.back();
            }
        }
        return fallback;
    }

    /**
     * Partition the comments around *t* and attach them to *c*.
     *
     * Leading comments are the contiguous run ending on the line immediately
     * above *t*; a blank line cuts the run. A comment sharing a line with the
     * previous on-channel token belongs to the *previous* construct, so it is
     * left alone here and picked up by that construct's trailing scan.
     * Everything else is an orphan and lands on the enclosing scope.
     *
     * Does nothing unless comment collection is enabled; the docstring comes
     * from the DocCommentExtractor, not from this partition.
     */
    void attachComments(ast::IScopeChild *c, Token *t);

    /**
     * Claim a comment that starts on *t*'s line, after it, as *c*'s trailing
     * comment -- the `x = 1; // note` case. Returns its normalized text.
     */
    std::string attachTrailingComment(ast::IScopeChild *c, Token *t);

    /**
     * Collect the comments left dangling at the end of *s* -- those after the
     * scope's last construct and before its closing brace, which no
     * ScopeChild is in a position to claim.
     */
    void collectScopeTrailingComments(ast::IScopeChild *s, Token *end);

    /**
     * Strip comment delimiters, the `*` gutter of a block comment, and the
     * common indent. The result is what a consumer emits.
     */
    static std::string normalizeComment(const std::string &raw, bool is_block);

    /** Line on which *t* ends -- its start line plus any embedded newlines. */
    static int32_t tokenEndLine(Token *t);

    /** Build a Comment node for *t*, located and normalized. */
    ast::IComment *mkCommentFor(Token *t, ast::CommentPlacement placement);

    void attachPendingAnnotations(ast::IScopeChild *c);
    void discardPendingAnnotations(size_t mark);

    /** Where the docstring scan should start for the child now being added. */
    Token *docstringAnchor(Token *t);

    /**
     * True when *ctx* is a standalone annotation -- one terminated by `;`
     * (LRM 7.13), which attaches to a lexical location rather than to the
     * next declared element.
     */
    bool isStandaloneAnnotation(PSSParser::AnnotationContext *ctx);

    /** Report an element annotation that never found an element (LRM 7.13). */
    void reportUnattachedAnnotation(ast::IAnnotation *a);

    /**
     * Emit an error marker anchored at *t*, with printf-style formatting.
     * Safe when no marker listener is attached.
     */
    void addErrorMarker(Token *t, const char *fmt, ...);

    bool evalConstantExpression(PSSParser::Constant_expressionContext *ctx, int64_t &val);

    bool evalExpression(PSSParser::ExpressionContext *ctx, int64_t &val);

    bool evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, int64_t &val);

    bool evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, std::string &val);

    bool evalCompileHas(PSSParser::Ref_pathContext *ctx);

    /**
     * Evaluate a compile-time condition, reporting an error anchored at *t*
     * when its value cannot be determined (PSS 3.1 19.1.3).
     *
     * *construct* names the statement ("compile if" / "compile assert") and
     * *ctx* supplies the condition text quoted in the diagnostic.  Returns
     * false, with the error already reported, when the value is unavailable;
     * callers must then elaborate neither branch, since 19.1.1 promises only
     * that a disabled branch is syntactically correct.
     */
    bool evalCompileTimeCond(
        PSSParser::Constant_expressionContext   *ctx,
        int64_t                                 &val,
        const char                              *construct);

    void visitCompileIfItem(antlr4::ParserRuleContext *ctx);

    /**
     * Report the D2 deprecation (PSS104) for any `compile if` branch written
     * without enclosing braces. Called from every `visit*_compile_if` method
     * with both branches, so the diagnostic does not depend on which branch
     * the condition selects.
     */
    void checkCompileIfBranches(
        antlr4::ParserRuleContext *true_body,
        antlr4::ParserRuleContext *false_body);

    void checkCompileIfBraces(antlr4::ParserRuleContext *ctx);

    ast::IScope *getGlobalScope(ast::IScope *s);

    ast::IScopeChild *findNamedChild(ast::IScope *scope, const std::string &name);

    ast::IScopeChild *findNamedChildUp(ast::IScope *scope, const std::string &name);

    ast::IScopeChild *findPackagePath(
        ast::IScope *scope,
        const std::vector<std::string> &path,
        uint32_t &consumed);

    /**
     * Walk the trailing elements of *path*, starting from *target* and
     * element *path_i*, through scopes, enum declarations and typed fields.
     * Returns null when any element is missing.
     */
    ast::IScopeChild *walkPathMembers(
        ast::IScopeChild *target,
        const std::vector<std::string> &path,
        uint32_t path_i);

    /**
     * Resolve *path* against a previously-processed source unit, newest first
     * (PSS 3.1 19.1.2).  Each unit is tried as a whole -- root lookup plus the
     * member walk -- rather than sharing a root across units, so a package
     * declared in several units resolves against the fragment that actually
     * holds the member.
     */
    ast::IScopeChild *resolvePathTargetInPriorUnits(
        ast::IScope *cur_global,
        const std::vector<std::string> &path);

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

    /**
     * Wrap `elem_t` in one `array<>` per declared dimension.
     *
     * Dimensions are applied **right to left**: `A a[3][2]` denotes an array
     * of 3 arrays of 2, so the rightmost dimension is the innermost wrap.
     * §11.3.2 Example87 makes this observable -- given `A a_arr[3][2]`,
     * `a_arr[1]` is a sub-array of two handles, not an element. Applying the
     * dimensions left to right builds the transposed type, which is wrong for
     * every non-square declaration and accidentally right for square ones.
     *
     * Templated so the caller keeps whichever static type it started with;
     * `array<>` is itself a user-defined type, so the cast never fails.
     */
    template <class T> T *applyArrayDims(
        T                                                *elem_t,
        const std::vector<PSSParser::Array_dimContext *> &dims) {
        ast::IDataType *type = elem_t;
        for (std::vector<PSSParser::Array_dimContext *>::const_reverse_iterator
            it=dims.rbegin();
            it!=dims.rend(); it++) {
            type = mkDataTypeArray(
                type,
                mkExpr((*it)->constant_expression()->expression()));
        }
        return dynamic_cast<T *>(type);
    }

	template <class T> T *mkDataTypeT(PSSParser::Data_typeContext *ctx) {
		return dynamic_cast<T *>(mkDataType(ctx));
	}

	ast::IExprDomainOpenRangeList *mkDomainOpenRangeList(PSSParser::Domain_open_range_listContext *ctx);

	ast::IExprOpenRangeList *mkOpenRangeList(PSSParser::Open_range_listContext *ctx);

    ast::IScopeChild *mkExecStmt(PSSParser::Procedural_stmtContext *ctx);

    void addExecStmt(PSSParser::Procedural_stmtContext *ctx);

    /**
     * @param plat the enclosing declaration's `platform_qualifier`, or null.
     *        `is_target`/`is_solve` on the prototype were previously hardcoded
     *        to false at every call site, so the two flags carried no
     *        information; the qualifier is threaded in here so that all three
     *        declaration forms (function_decl -- which covers both the
     *        prototype and the definition spelling -- and import_function)
     *        record it the same way.
     * @param is_pure whether the declaration carried the `pure` qualifier
     *        (B.5). Like the platform qualifier, this was never recorded --
     *        `is_pure` was left at its default at every call site -- which
     *        made the flag useless to any check that needed it (PSS114).
     */
    ast::IFunctionPrototype *mkFunctionPrototype(
        PSSParser::Function_prototypeContext *ctx,
        PSSParser::Platform_qualifierContext *plat = 0,
        bool                                 is_pure = false);

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

	ast::IExpr *mkMsbWidth(
		ast::IExpr                              *msb,
		PSSParser::ExpressionContext            *lsb_ctx);

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

    /**
     * 4.7.1 -- scan a triple-quoted string body and build its TemplateString.
     *
     * `raw` is the content with the enclosing `"""` already stripped;
     * `base_line`/`base_col` are the file position of raw[0], 1-based.
     *
     * Returns 0 when the text holds no special elements, which is the common
     * case and keeps a plain string free of extra nodes. Diagnostics
     * (PSS108-PSS111) are emitted here.
     *
     * Defined in AstBuilderIntTemplate.cpp.
     */
    ast::ITemplateString *mkTemplateString(
        const std::string   &raw,
        int32_t             base_line,
        int32_t             base_col);

    /** Build the template for a string_literal token, or 0. */
    ast::ITemplateString *mkTemplateString(PSSParser::String_literalContext *ctx);

private:

    /**
     * Where the fragment currently being sub-parsed sits in the file.
     *
     * Every template fragment is parsed out of context, so ANTLR reports
     * positions relative to the fragment. `rebaseLoc` maps them back; `active`
     * is false during an ordinary parse, when positions are already absolute.
     */
    struct FragmentBase {
        int32_t line = 0;
        int32_t col = 0;
        bool    active = false;
    };

    /**
     * Map a fragment-relative (line, col) onto the file.
     *
     * The column offset applies **only on the fragment's first line** -- on
     * every later line the fragment's own column is already the file column.
     * That is the classic off-by-one here and it has a dedicated test.
     *
     * `col` is 1-based on the way in and on the way out.
     */
    void rebaseLoc(int32_t &line, int32_t &col) const;

    /** Sub-parse `text` as an `expression`. Returns 0 and sets `err` on failure. */
    ast::IExpr *fragmentExpr(
        const std::string   &text,
        int32_t             line,
        int32_t             col,
        std::string         &err);

    /** Emit one of the template diagnostics. `code` is 108..111. */
    void templateMarker(
        int32_t             code,
        const std::string   &detail,
        int32_t             line,
        int32_t             col,
        int32_t             extent);

    /**
     * Classify and build one `{% ... %}` directive, maintaining the block
     * stack. Appends whatever element it produces itself, because `if` has to
     * append the TemplateIf to the enclosing frame *before* pushing the clause
     * frame the body will go into.
     */
    void buildTemplateDirective(
        const std::string           &raw,
        const struct TemplateToken  &tok,
        struct TemplateBuildState   &st);

    /** Append an element to the current frame, stamping location and flags. */
    void appendTemplateElem(
        struct TemplateBuildState   &st,
        ast::ITemplateElem          *elem,
        const struct TemplateToken  &tok);

    /**
     * Register a template-local declaration in `scope`'s symtab and children.
     *
     * Follows visitProcedural_foreach_stmt exactly: the symbol lives on the
     * owning node, and TaskBuildSymbolTree is told not to re-home it.
     */
    void registerTemplateLocal(
        ast::ISymbolScope           *scope,
        ast::IProceduralStmtDataDeclaration *decl,
        const struct TemplateToken  &tok);

    /**
     * D2 cascade suppression: the previous syntax error's token index and
     * rule index. A new error within N tokens of this one, in the same rule,
     * is almost always ANTLR flailing through the same garbage region rather
     * than a second independent defect -- reset per `build()` so state never
     * leaks across files in a long-lived process.
     */
    ssize_t                                     m_last_syntax_error_token_idx;
    size_t                                      m_last_syntax_error_rule_idx;

    static dmgr::IDebug                         *m_dbg;
    int32_t                                     m_file_id;
	bool										m_collectDocStrings;
	bool										m_collectComments;
	/** Start of the enclosing attr_field, for doc-comment lookup. */
    bool                                        m_enableProfile;
    /**
     * The last parse's profile, already resolved away from the parser.
     *
     * Deliberately per-file and replaced on every `build()`: a caller wanting
     * corpus totals aggregates the snapshots itself.  Accumulating here would
     * throw away the per-file attribution the profiling harness is built on,
     * and there is no way to recover it afterwards.
     */
    std::unique_ptr<ProfileSnapshot>            m_profile;
    IMarkerListener								*m_marker_l;
	ast::IFactory								*m_factory;
	ast::IExpr									*m_expr;
	ast::IDataType								*m_type;
    std::vector<ast::IScope *>					m_scopes;
    /**
     * Source units this builder has already processed, in processing order.
     *
     * Compile-time expressions are evaluated during AST construction, so the
     * only view they have of the model is what the builder has built.  Holding
     * the prior units here is what lets a `compile if` condition read a
     * `static const` from an earlier file (PSS 3.1 19.1.2); without it every
     * cross-file reference resolves to null and reads as false.
     *
     * These are borrowed pointers to scopes owned by the caller (Parser._files
     * on the Python side), so the builder must not outlive them.
     */
    std::vector<ast::IGlobalScope *>            m_prior_units;
	ast::IScopeChild							*m_activity_stmt;
	ast::IExprId								*m_labeled_activity_id;
	ast::IConstraintStmt						*m_constraint;
    ast::IScopeChild                            *m_exec_stmt;
    int32_t                                     m_exec_stmt_cnt;
    std::vector<ast::IExecScope *>              m_exec_scope_s;
	std::vector<ast::IConstraintScope *>		m_constraint_s;
    std::unique_ptr<CommonTokenStream>			m_tokens;
    FragmentBase                                m_frag;
    DocCommentOptions                           m_doc_opts;
    std::unique_ptr<DocCommentExtractor>        m_doc_extractor;
    /**
     * Stack of doc anchors, innermost last.  A null entry means "no anchor is
     * in force" and is pushed by push_scope so a declaration nested inside a
     * scope cannot inherit the anchor of the wrapper that opened it.
     */
    std::vector<Token *>                        m_doc_anchors;
	std::vector<ast::IExprIdUP>					*m_type_id;
	uint32_t									m_field_depth;
	std::vector<ast::IField *>					m_fields;
    std::vector<ast::IAnnotation *>            m_pending_annotations;
    // Start token of the first pending element annotation, and of the batch
    // most recently attached to a child. A doc comment is written above the
    // annotations rather than above the declaration, so the docstring scan must
    // start from the annotation, not from the declaration's own first token.
    Token                                     *m_pending_annotation_tok = 0;
    Token                                     *m_attached_annotation_tok = 0;

};

}
