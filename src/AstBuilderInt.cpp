/*
 * AstBuilderInt.cpp
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#ifdef _WIN32
#ifdef UNDEFINED
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
#else
#include <sys/time.h>
#endif
#include <vector>
#include <cstdarg>
#include "dmgr/impl/DebugMacros.h"
#include "AstBuilderInt.h"
#include "PSSLexer.h"
#include "atn/ParseInfo.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IField.h"
#include "pssp/ast/IFieldClaim.h"
#include "pssp/ast/IFieldCompRef.h"
#include "pssp/ast/IFieldRef.h"
#include "pssp/ast/IActionHandleField.h"
#include "pssp/ast/IDataTypeEnum.h"
#include "pssp/ast/IDataTypeUserDefined.h"
#include "pssp/ast/IEnumItem.h"
#include "pssp/ast/IEnumDecl.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/IExprIn.h"
#include "pssp/ast/IExprOpenRangeList.h"
#include "pssp/ast/IExprOpenRangeValue.h"
#include "pssp/ast/INamedScope.h"
#include "pssp/ast/IPackageScope.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/ast/Location.h"
#include "DocAnchorScope.h"
#include "Marker.h"
#include "pssp/IMarkerCollector.h"

namespace pssp {



using namespace ast;

AstBuilderInt::AstBuilderInt(
    dmgr::IDebugMgr     *dmgr,
	ast::IFactory		*factory,
	IMarkerListener 	*marker_l) : m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("pssp::AstBuilderInt", dmgr);
	m_collectDocStrings = false;
	m_collectComments = false;
    m_enableProfile = false;
	m_field_depth = 0;
	m_labeled_activity_id = 0;
	m_constraint = 0;
	m_last_syntax_error_token_idx = -1;
	m_last_syntax_error_rule_idx = static_cast<size_t>(-1);

}

AstBuilderInt::~AstBuilderInt() {
	// TODO Auto-generated destructor stub
}

static uint64_t time_ms() {
    uint64_t ret = 0;
#ifndef _WIN32
    struct timeval tv;
    gettimeofday(&tv, 0);
    ret = tv.tv_sec*1000;
    ret += tv.tv_usec/1000;
#else
#ifdef UNDEFINED
    static const uint64_t EPOCH = ((uint64_t) 116444736000000000ULL);

    SYSTEMTIME  system_time;
    FILETIME    file_time;
    uint64_t    time;

    GetSystemTime( &system_time );
    SystemTimeToFileTime( &system_time, &file_time );
    time =  ((uint64_t)file_time.dwLowDateTime )      ;
    time += ((uint64_t)file_time.dwHighDateTime) << 32;

    ret = ((time - EPOCH) / 10000000L);
    ret *= 1000;
    ret += system_time.wMilliseconds;
#endif
#endif
    return ret;
}


void AstBuilderInt::build(
			ast::IGlobalScope		*global,
			std::istream 			*in) {

    m_file_id = global->getFileid();

    // Clear any previous profiling data
    m_profile.reset();

    // D2 cascade-suppression state is per-file, not per-process.
    m_last_syntax_error_token_idx = -1;
    m_last_syntax_error_rule_idx = static_cast<size_t>(-1);

    uint64_t parse_s = time_ms();
	ANTLRInputStream input(*in);
	PSSLexer lexer(&input);
	m_tokens = std::unique_ptr<CommonTokenStream>(new CommonTokenStream(&lexer));

	if (m_collectComments) {
		// A trailing comment sits to the *right* of the construct that owns
		// it, and the stream only buffers as far as the parser's lookahead
		// has reached -- which, mid-rule, is short of it. Buffer the lot up
		// front. Leading comments never needed this, which is why the
		// docstring path has always worked without it.
		m_tokens->fill();
	}

	m_doc_extractor = std::unique_ptr<DocCommentExtractor>(
		new DocCommentExtractor(m_tokens.get(), m_file_id, m_doc_opts));
	PSSParser parser(m_tokens.get());

	parser.removeErrorListeners();
	parser.addErrorListener(this);

    parser.setProfile(m_enableProfile);

	PSSParser::Compilation_unitContext *ctx = parser.compilation_unit();
    uint64_t parse_e = time_ms();
    DEBUG("Parse time: %lld", (parse_e-parse_s));

	// Only proceed to build out the AST if there are no syntax errors
	if (!m_marker_l || !m_marker_l->hasSeverity(MarkerSeverityE::Error)) {
        uint64_t build_ast_s = time_ms();
		push_scope(global);
		ctx->accept(this);
		pop_scope();
        uint64_t build_ast_e = time_ms();
        DEBUG("Build AST: %lld", (build_ast_e-build_ast_s));

        // This unit is now a "previously-processed source unit" for every unit
        // built after it, and supplies the types and constants their
        // compile-time expressions may reference (PSS 3.1 19.1.2).
        m_prior_units.push_back(global);
	}

    if (m_enableProfile) {
        // Snapshot the profiling data while the parser is still alive -- and,
        // just as importantly, while the token stream it recorded events
        // against is still the current one.  ANTLR's event records hold raw
        // pointers into both; `mkProfileSnapshot` resolves every one of them
        // to a line, a column and a string, so nothing here outlives its
        // referent.  Deferring the work to `getProfileInfo()` would be a
        // use-after-free the moment a second file is parsed.
        m_profile = std::unique_ptr<ProfileSnapshot>(
            new ProfileSnapshot(mkProfileSnapshot(parser)));

        // Log summary for debugging
        for (std::vector<DecisionSnapshot>::const_iterator
            it=m_profile->decisions.begin();
            it!=m_profile->decisions.end(); it++) {
            if (it->ambiguity_count) {
                DEBUG("Ambiguity: decision %d in rule '%s' (%d occurrences)",
                    it->decision, it->rule_name.c_str(), it->ambiguity_count);
            }
        }
    }
}

antlrcpp::Any AstBuilderInt::visitPackage_declaration(
	PSSParser::Package_declarationContext *ctx) {
	IPackageScope *pkg = m_factory->mkPackageScope();

    setLoc(pkg, ctx->start);

	// TODO: populate Id list
	std::vector<PSSParser::Package_identifierContext *> id =
		ctx->package_id_path()->package_identifier();
	for (std::vector<PSSParser::Package_identifierContext *>::const_iterator
		it=id.begin();
		it!=id.end(); it++) {
		PSSParser::Package_identifierContext *id = (*it);
		pkg->getId().push_back(IExprIdUP(mkId((*it)->identifier())));
	}

	addChild(pkg, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
	push_scope(pkg);
	std::vector<PSSParser::Package_body_item_annContext *> items = ctx->package_body_item_ann();
	for (std::vector<PSSParser::Package_body_item_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}
	pop_scope();

	return 0;
}

antlrcpp::Any AstBuilderInt::visitPackage_body_compile_if(PSSParser::Package_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(ctx->true_body, ctx->false_body);
    if (!evalCompileTimeCond(ctx->cond, cond, "compile if")) {
        // Reported as an error: elaborate neither branch (19.1.1 promises only
        // that a disabled branch is syntactically correct).
    } else if (cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitImport_stmt(PSSParser::Import_stmtContext *ctx) {
	DEBUG_ENTER("visitImport_stmt");
	bool is_wildcard = false;
	IExprId *alias = 0;
	
	if (ctx->package_import_pattern()->package_import_qualifier()) {
		if (ctx->package_import_pattern()->package_import_qualifier()->package_import_wildcard()) {
			is_wildcard = true;
		} else {
			alias = mkId(ctx->package_import_pattern()->package_import_qualifier()->
				package_import_alias()->package_identifier()->identifier());
		}
	}

	IPackageImportStmt *imp = m_factory->mkPackageImportStmt(is_wildcard, alias);
    setLoc(imp, ctx->start);

	imp->setPath(mkTypeId(ctx->package_import_pattern()->type_identifier()));
	addChild(imp, ctx->start);
	DEBUG_LEAVE("visitImport_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitPyimport_single_module(PSSParser::Pyimport_single_moduleContext *ctx) {
    DEBUG_ENTER("visitPyimport_single_module");
    ast::IPyImportStmt *imp = m_factory->mkPyImportStmt();

    std::vector<PSSParser::IdentifierContext *> path = ctx->pyimport_mod_path()->identifier();
    for (std::vector<PSSParser::IdentifierContext *>::const_iterator
        it=path.begin();
        it!=path.end(); it++) {
        imp->getPath().push_back(ast::IExprIdUP(mkId(*it)));
    }
    if (ctx->identifier()) {
        // Have an alias
        imp->setAlias(mkId(ctx->identifier()));
    }

    setLoc(imp, ctx->start);
    addChild(imp, ctx->start);
    DEBUG_LEAVE("visitPyimport_single_module");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitPyimport_from_module(PSSParser::Pyimport_from_moduleContext *ctx) {
    DEBUG_ENTER("visitPyimport_from_module");
    ast::IPyImportFromStmt *imp = m_factory->mkPyImportFromStmt();
    DEBUG_LEAVE("visitPyimport_from_module");
    return 0;
}

static std::map<std::string,ast::ExtendTargetE> ExtendKind_m = {
	{"action", ast::ExtendTargetE::Action},
	{"annotation", ast::ExtendTargetE::Annotation},
	{"buffer", ast::ExtendTargetE::Buffer},
	{"component", ast::ExtendTargetE::Component},
	{"enum", ast::ExtendTargetE::Enum},
	{"resource", ast::ExtendTargetE::Resource},
	{"state", ast::ExtendTargetE::State},
	{"stream", ast::ExtendTargetE::Stream},
	{"struct", ast::ExtendTargetE::Struct}
};

static FieldAttr accessModifierToFieldAttr(PSSParser::Access_modifierContext *ctx) {
    if (!ctx) {
        return FieldAttr::NoFlags;
    } else if (ctx->TOK_PRIVATE()) {
        return FieldAttr::Private;
    } else if (ctx->TOK_PROTECTED()) {
        return FieldAttr::Protected;
    } else {
        return FieldAttr::NoFlags;
    }
}

antlrcpp::Any AstBuilderInt::visitExtend_stmt(PSSParser::Extend_stmtContext *ctx) {
	DEBUG_ENTER("visitExtend_stmt");
	ExtendTargetE kind;
    
    if (ctx->is_action) {
        kind = ast::ExtendTargetE::Action;
    } else if (ctx->is_annotation) {
        kind = ast::ExtendTargetE::Annotation;
    } else if (ctx->is_component) {
        kind = ast::ExtendTargetE::Component;
    } else if (ctx->is_enum) {
        kind = ast::ExtendTargetE::Enum;
    } else if (ctx->struct_kind() && ctx->struct_kind()->img) {
        kind = ast::ExtendTargetE::Struct;
    } else {
        std::map<std::string,ast::ExtendTargetE>::const_iterator it =
            ExtendKind_m.find(ctx->struct_kind()->object_kind()->getText());
        if (it != ExtendKind_m.end()) {
            kind = it->second;
        } else {
            DEBUG_ERROR("Error: No match for extend kind");
        }
    }

	if (kind == ast::ExtendTargetE::Enum) {
		IExtendEnum *ext = m_factory->mkExtendEnum(mkTypeId(ctx->type_identifier()));
		std::vector<PSSParser::Enum_itemContext *> items = ctx->enum_item();
        setLoc(ext, ctx->start);

		for (std::vector<PSSParser::Enum_itemContext *>::const_iterator
			it=items.begin();
			it!=items.end(); it++) {
			ast::IExprId *id = mkId((*it)->identifier());
			ast::IExpr *value = 0;

			if ((*it)->constant_expression()) {
				value = mkExpr((*it)->constant_expression()->expression());
			}
			ast::IEnumItem *item = m_factory->mkEnumItem(id, value);
			// The extend site, not the base declaration: an item contributed
			// by `extend enum` is written here.
			setLoc(item, (*it)->start);
			attachDocstring(item, (*it)->start);
			ext->getItems().push_back(ast::IEnumItemUP(item));
		}
		
		addChild(ext, ctx->start);
	} else {
		IExtendType *ext = m_factory->mkExtendType(
			kind,
			mkTypeId(ctx->type_identifier()));
        setLoc(ext, ctx->start);

		addChild(ext, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
		push_scope(ext);
		switch (kind) {
			case ast::ExtendTargetE::Action: {
				std::vector<PSSParser::Action_body_item_annContext *> items =
					ctx->action_body_item_ann();
                DEBUG("Extend Action: %d items", items.size());
				for (std::vector<PSSParser::Action_body_item_annContext *>::const_iterator
					it=items.begin();
					it!=items.end(); it++) {
					(*it)->accept(this);
				}
			} break;
			case ast::ExtendTargetE::Annotation: {
				std::vector<PSSParser::Annotation_body_itemContext *> items =
					ctx->annotation_body_item();
                DEBUG("Extend Annotation: %d items", items.size());
				for (std::vector<PSSParser::Annotation_body_itemContext *>::const_iterator
					it=items.begin();
					it!=items.end(); it++) {
					(*it)->accept(this);
				}
			} break;
			case ast::ExtendTargetE::Component: {
				std::vector<PSSParser::Component_body_item_annContext *> items =
					ctx->component_body_item_ann();
                DEBUG("Extend Component: %d items", items.size());
				for (std::vector<PSSParser::Component_body_item_annContext *>::const_iterator
					it=items.begin();
					it!=items.end(); it++) {
					(*it)->accept(this);
				}
			} break;
			case ast::ExtendTargetE::Buffer:
			case ast::ExtendTargetE::Resource:
			case ast::ExtendTargetE::State:
			case ast::ExtendTargetE::Stream:
			case ast::ExtendTargetE::Struct: {
				std::vector<PSSParser::Struct_body_itemContext *> items =
					ctx->struct_body_item();
                DEBUG("Extend Struct: %d items", items.size());
				for (std::vector<PSSParser::Struct_body_itemContext *>::const_iterator
					it=items.begin();
					it!=items.end(); it++) {
					(*it)->accept(this);
				}
				
			} break;
            default:
                DEBUG_ERROR("Error: unhandled extension-type target: %d\n", kind);
                break;
		}

		pop_scope();
	}

	DEBUG_LEAVE("visitExtend_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAnnotation_declaration(PSSParser::Annotation_declarationContext *ctx) {
	DEBUG_ENTER("visitAnnotation_declaration");

	ast::ITypeIdentifier *super_t = 0;
	if (ctx->annotation_super_spec()) {
		super_t = mkTypeId(ctx->annotation_super_spec()->type_identifier());
	}

	ast::IAnnotationDecl *annotation = m_factory->mkAnnotationDecl(
		mkId(ctx->annotation_identifier()->identifier()),
		super_t);
    setLoc(annotation, ctx->start);

	if (ctx->template_param_decl_list()) {
        annotation->setParams(mkTypeParamDecl(ctx->template_param_decl_list()));
	}

	addChild(annotation, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
	push_scope(annotation);

	std::vector<PSSParser::Annotation_body_itemContext *> items = ctx->annotation_body_item();
	for (std::vector<PSSParser::Annotation_body_itemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}

	pop_scope();

	DEBUG_LEAVE("visitAnnotation_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAnnotation_body_compile_if(PSSParser::Annotation_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(ctx->true_body, ctx->false_body);
    if (!evalCompileTimeCond(ctx->cond, cond, "compile if")) {
        // Reported as an error: elaborate neither branch (19.1.1 promises only
        // that a disabled branch is syntactically correct).
    } else if (cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

/**
 * The `*_ann` rules wrap a body item in `annotation*`.  When an annotation is
 * present it sits between a leading doc comment and the declaration, so the
 * declaration's own start token is no longer adjacent to the comment.
 *
 * The anchor is established only when an annotation is actually there: with
 * none, `ctx->start` is already the declaration's start token and the override
 * is a no-op.
 */
antlrcpp::Any AstBuilderInt::visitAction_body_item_ann(PSSParser::Action_body_item_annContext *ctx) {
	return visitChildren(ctx);
}

antlrcpp::Any AstBuilderInt::visitComponent_body_item_ann(PSSParser::Component_body_item_annContext *ctx) {
	return visitChildren(ctx);
}

antlrcpp::Any AstBuilderInt::visitActivity_stmt_ann(PSSParser::Activity_stmt_annContext *ctx) {
	return visitChildren(ctx);
}

antlrcpp::Any AstBuilderInt::visitAnnotation_attr_field(PSSParser::Annotation_attr_fieldContext *ctx) {
	DEBUG_ENTER("visitAnnotation_attr_field");
	// D2: `annotation_attr_field` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);

	m_field_depth++;
	ctx->data_declaration()->accept(this);
	m_field_depth--;

	for (std::vector<ast::IField *>::const_iterator
		it=m_fields.begin();
		it!=m_fields.end(); it++) {
		FieldAttr attr = (*it)->getAttr();

		if (ctx->TOK_STATIC()) {
			attr |= FieldAttr::Static;
			attr |= FieldAttr::Const;
		}

		(*it)->setAttr(attr);
	}

	if (!m_field_depth) {
		m_fields.clear();
	}

	DEBUG_LEAVE("visitAnnotation_attr_field");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAnnotation(PSSParser::AnnotationContext *ctx) {
    DEBUG_ENTER("visitAnnotation");

    ast::IAnnotation *annotation = m_factory->mkAnnotation(
        mkTypeId(ctx->type_identifier()));
    setLoc(annotation, ctx->start);

    if (ctx->annotation_params_list()) {
        for (auto *item : ctx->annotation_params_list()->annotation_param_item()) {
            ast::IAnnotationParam *param = m_factory->mkAnnotationParam(
                mkId(item->identifier()),
                mkExpr(item->constant_expression()->expression()));
            setLoc(param, item->start);
            annotation->getParameters().push_back(ast::IAnnotationParamUP(param));
        }
    }

    // pyastbuilder leaves non-ctor `bool` members uninitialized (the generated
    // Annotation ctor initializes only m_type), so this must be set on both
    // paths rather than only when the flag is true.
    annotation->setIs_standalone(ctx->is_standalone != nullptr);

    if (ctx->is_standalone) {
        // §7.13: a standalone annotation is anchored at its lexical location in
        // the enclosing scope. It never attaches to a following element, so it
        // must not enter the pending list -- otherwise it would both steal the
        // next declaration's annotation slot and suppress the dangling-
        // annotation diagnostic below.
        addChild(annotation, ctx->start);
    } else {
        if (m_pending_annotations.empty()) {
            m_pending_annotation_tok = ctx->start;
        }
        m_pending_annotations.push_back(annotation);
    }

    DEBUG_LEAVE("visitAnnotation");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitConst_field_declaration(PSSParser::Const_field_declarationContext *ctx) {
	DEBUG_ENTER("visitConst_field_declaration");
	// D2: `const_field_declaration` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);

	m_field_depth++;
	ctx->data_declaration()->accept(this);
	m_field_depth--;

	// The clear used to come *first*, so the loop below ran over an empty
	// vector and `const int K = 4;` was recorded with no attributes at all --
	// indistinguishable from an ordinary field. Every other site that stamps
	// field attributes clears afterwards; this one now does too.
	for (std::vector<ast::IField *>::const_iterator
		it=m_fields.begin();
		it!=m_fields.end(); it++) {
		FieldAttr attr = (*it)->getAttr() | FieldAttr::Const;
		if (ctx->TOK_STATIC()) {
			attr |= FieldAttr::Static;
		}
		(*it)->setAttr(attr);
	}

	if (!m_field_depth) {
		m_fields.clear();
	}

	DEBUG_LEAVE("visitConst_field_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitCompile_assert_stmt(PSSParser::Compile_assert_stmtContext *ctx) {
    int64_t cond = 0;
    if (!evalCompileTimeCond(ctx->cond, cond, "compile assert")) {
        // Indeterminable: already reported, and distinct from a condition that
        // evaluated to false.  Reporting it as a plain assertion failure is
        // what made a cross-file `static const` look like a failing assert.
    } else if (!cond) {
        if (m_marker_l) {
            ast::Location loc;
            loc.fileid = m_file_id;
            loc.lineno = ctx->start->getLine();
            loc.linepos = ctx->start->getCharPositionInLine()+1;
            loc.extent = ctx->getText().size();
            std::string msg = "compile assert failed";
            if (ctx->msg) {
                std::string text = ctx->msg->getText();
                if (text.size() >= 2) {
                    text = text.substr(1, text.size()-2);
                }
                msg += ": " + text;
            }
            Marker m(msg, MarkerSeverityE::Error, loc);
            m_marker_l->marker(&m);
        }
    }
    return 0;
}

// B.2 Action declaration

antlrcpp::Any AstBuilderInt::visitAction_declaration(PSSParser::Action_declarationContext *ctx) {
	DEBUG_ENTER("visitAction_declaration");

	ast::ITypeIdentifier *super_t = 0;
	if (ctx->action_super_spec()) {
		super_t = mkTypeId(ctx->action_super_spec()->type_identifier());
	}

	ast::IAction *action = m_factory->mkAction(
		mkId(ctx->action_identifier()->identifier()),
		super_t,
		false);
    setLoc(action, ctx->start);

    // Add in a ref field
    ast::IFieldCompRef *comp = m_factory->mkFieldCompRef(
        m_factory->mkExprId("comp", false),
        0 // Type: must back-patch later
    );
    comp->setIndex(action->getChildren().size());
    action->getChildren().push_back(ast::IScopeChildUP(comp));

	if (ctx->template_param_decl_list()) {
        action->setParams(mkTypeParamDecl(ctx->template_param_decl_list()));
	}

	addChild(action, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
	push_scope(action);

	std::vector<PSSParser::Action_body_item_annContext *> items = ctx->action_body_item_ann();

	for (std::vector<PSSParser::Action_body_item_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}

	pop_scope();

	DEBUG_LEAVE("visitAction_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAbstract_action_declaration(PSSParser::Abstract_action_declarationContext *ctx) {
	DEBUG_ENTER("visitAbstract_action_declaration");
	// D2: `abstract_action_declaration` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);
	ctx->action_declaration()->accept(this);
	ast::IAction *action = dynamic_cast<ast::IAction *>(scope()->getChildren().back().get());
	action->setIs_abstract(true);
    setLoc(action, ctx->start);
	DEBUG_LEAVE("visitAbstract_action_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitOverride_action_declaration(PSSParser::Override_action_declarationContext *ctx) {
    DEBUG_ENTER("visitOverride_action_declaration");

    // LRM 19.2.2: an override action is a *new* action in the declaring
    // component that implicitly inherits from the one it overrides. So it is
    // built as an Action, not -- as it was until now -- an IExtendType
    // targeting the same name. An extension would have added these members to
    // the base action everywhere it is used, which is the opposite of what
    // overriding means.
    //
    // The super type spells the action's own name, and that is not a mistake:
    // `inh1_c::base_a` inherits `base_c::base_a`. Resolving it therefore
    // cannot use the ordinary lookup, which would find this very declaration
    // and cycle -- TaskResolveOverrideActions starts from the enclosing
    // component's base chain instead, and reports 19.2.2a when nothing there
    // declares the name.
    ast::ITypeIdentifier *super_t = m_factory->mkTypeIdentifier();
    super_t->getElems().push_back(ast::ITypeIdentifierElemUP(
        m_factory->mkTypeIdentifierElem(
            mkId(ctx->action_identifier()->identifier()), 0)));

    ast::IAction *action = m_factory->mkAction(
        mkId(ctx->action_identifier()->identifier()),
        super_t,
        false);
    action->setIs_override(true);
    setLoc(action, ctx->start);

    // The `comp` ref field a normal action declaration installs; an override
    // is an action like any other and needs it too.
    ast::IFieldCompRef *comp = m_factory->mkFieldCompRef(
        m_factory->mkExprId("comp", false),
        0 // Type: must back-patch later
    );
    comp->setIndex(action->getChildren().size());
    action->getChildren().push_back(ast::IScopeChildUP(comp));

    addChild(action, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
    push_scope(action);

    std::vector<PSSParser::Action_body_item_annContext *> items = ctx->action_body_item_ann();
    for (auto *item : items) {
        item->accept(this);
    }

    pop_scope();

    DEBUG_LEAVE("visitOverride_action_declaration");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_bind_stmt(PSSParser::Activity_bind_stmtContext *ctx) {
    DEBUG_ENTER("visitActivity_bind_stmt");
    ast::IExprHierarchicalId *lhs;

    lhs = mkHierarchicalId(ctx->hierarchical_id());
    ast::IActivityBindStmt *stmt = m_factory->mkActivityBindStmt(lhs);

    if (ctx->activity_bind_item_or_list()->hierarchical_id()) {
        stmt->getRhs().push_back(
            mkHierarchicalId(ctx->activity_bind_item_or_list()->hierarchical_id()));
    } else {
        std::vector<PSSParser::Hierarchical_idContext *> items = ctx->activity_bind_item_or_list()->hierarchical_id_list()->hierarchical_id();
        for (std::vector<PSSParser::Hierarchical_idContext *>::const_iterator
            it=items.begin(); 
            it!=items.end(); it++) {
            stmt->getRhs().push_back(mkHierarchicalId((*it)));
        }
    }
    setLoc(stmt, ctx->start);
    m_activity_stmt = stmt;
    
    DEBUG_LEAVE("visitActivity_bind_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_declaration(PSSParser::Activity_declarationContext *ctx) {
    DEBUG_ENTER("visitActivity_declaration");
    ast::IActivityDecl *activity = m_factory->mkActivityDecl("");
    setLoc(activity, ctx->start);

	std::vector<PSSParser::Activity_stmt_annContext *> items = ctx->activity_stmt_ann();
	for (std::vector<PSSParser::Activity_stmt_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        addActivityStmt(activity, *it);
	}
    
	m_activity_stmt = activity;

    addChild(activity, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
    
    DEBUG_LEAVE("visitActivity_declaration");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitAction_body_compile_if(PSSParser::Action_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(ctx->true_body, ctx->false_body);
    if (!evalCompileTimeCond(ctx->cond, cond, "compile if")) {
        // Reported as an error: elaborate neither branch (19.1.1 promises only
        // that a disabled branch is syntactically correct).
    } else if (cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitFlow_ref_field_declaration(PSSParser::Flow_ref_field_declarationContext *ctx) {
	DEBUG_ENTER("visitFlow_ref_field_declaration");

	std::vector<PSSParser::Object_ref_fieldContext *> items = ctx->object_ref_field();
	for (std::vector<PSSParser::Object_ref_fieldContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		ast::IDataTypeUserDefined *type = 0;

		type = mkDataTypeUserDefined(ctx->flow_object_type()->type_identifier());

		type = applyArrayDims(type, (*it)->array_dim());

		ast::IFieldRef *field = m_factory->mkFieldRef(
			mkId((*it)->identifier()),
			type,
			ctx->is_input);
        setLoc(field, (*it)->identifier()->start);
		addChild(field, ctx->start);
	}

	DEBUG_LEAVE("visitFlow_ref_field_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitResource_ref_field_declaration(PSSParser::Resource_ref_field_declarationContext *ctx) {
	DEBUG_ENTER("visitResource_ref_field_declaration");

	std::vector<PSSParser::Object_ref_fieldContext *> items = ctx->object_ref_field();
	for (std::vector<PSSParser::Object_ref_fieldContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		ast::IDataTypeUserDefined *type = mkDataTypeUserDefined(
			ctx->resource_object_type()->resource_type_identifier()->type_identifier());

		type = applyArrayDims(type, (*it)->array_dim());

		ast::IFieldClaim *field = m_factory->mkFieldClaim(
			mkId((*it)->identifier()),
			type,
			ctx->lock);
        setLoc(field, (*it)->identifier()->start);
		addChild(field, ctx->start);
	}

	DEBUG_LEAVE("visitResource_ref_field_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitComponent_pool_declaration(PSSParser::Component_pool_declarationContext *ctx) {
	DEBUG_ENTER("visitComponent_pool_declaration");
	// Grammar:
	//   TOK_POOL ('[' expression ']')? type_identifier identifier ';'
	ast::IDataTypeUserDefined *type = mkDataTypeUserDefined(ctx->type_identifier());

	ast::IExpr *size = 0;
	if (ctx->expression()) {
		size = mkExpr(ctx->expression());
	}

	ast::IFieldPool *pool = m_factory->mkFieldPool(
		mkId(ctx->identifier()),
		type,
		size);
	setLoc(pool, ctx->identifier()->start);
	addChild(pool, ctx->start);

	DEBUG_LEAVE("visitComponent_pool_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitObject_bind_stmt(PSSParser::Object_bind_stmtContext *ctx) {
	DEBUG_ENTER("visitObject_bind_stmt");
	// Grammar:
	//   TOK_BIND hierarchical_id object_bind_item_or_list ';'
	// Targets are captured as plain dotted-path text (no ref resolution), so
	// the node is inert during link. The wildcard form (`bind p *;`) sets
	// is_wildcard and leaves targets empty.
	std::string pool_path = ctx->hierarchical_id()->getText();

	bool is_wildcard = false;
	std::vector<std::string> targets; // explicit dotted bind-item paths

	PSSParser::Object_bind_item_or_listContext *list = ctx->object_bind_item_or_list();
	std::vector<PSSParser::Object_bind_item_pathContext *> paths = list->object_bind_item_path();
	for (std::vector<PSSParser::Object_bind_item_pathContext *>::const_iterator
		it=paths.begin(); it!=paths.end(); it++) {
		PSSParser::Object_bind_item_pathContext *path = *it;
		PSSParser::Object_bind_itemContext *item = path->object_bind_item();
		if (item && item->TOK_ASTERISK()) {
			is_wildcard = true;
		} else {
			targets.push_back(path->getText());
		}
	}

	ast::IComponentBind *bind = m_factory->mkComponentBind(pool_path, is_wildcard);
	for (std::vector<std::string>::const_iterator
		it=targets.begin(); it!=targets.end(); it++) {
		bind->getTargets().push_back(*it);
	}
	setLoc(bind, ctx->start);
	addChild(bind, ctx->start);

	DEBUG_LEAVE("visitObject_bind_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitInline_covergroup(PSSParser::Inline_covergroupContext *ctx) {
	DEBUG_ENTER("visitInline_covergroup");
	// Grammar:
	//   TOK_COVERGROUP '{' covergroup_body_item* '}' identifier ';'
	ast::ICovergroup *cg = m_factory->mkCovergroup(mkId(ctx->identifier()));

	// NOTE: ANTLR rule-list accessors return a fresh vector by value, so the
	// vector must be bound to a local before iterating (begin()/end() on two
	// separate temporaries is undefined behaviour).
	std::vector<PSSParser::Covergroup_body_itemContext *> items = ctx->covergroup_body_item();
	for (std::vector<PSSParser::Covergroup_body_itemContext *>::const_iterator
		it=items.begin(); it!=items.end(); it++) {
		PSSParser::Covergroup_body_itemContext *item = *it;

		if (item->covergroup_coverpoint()) {
			PSSParser::Covergroup_coverpointContext *cp_ctx = item->covergroup_coverpoint();
			// Name: explicit label, else the (textual) target identifier.
			ast::IExprId *cp_name;
			if (cp_ctx->coverpoint_identifier()) {
				cp_name = mkId(cp_ctx->coverpoint_identifier()->identifier());
			} else {
				cp_name = m_factory->mkExprId(cp_ctx->target->getText(), false);
			}
			ast::IExpr *target = cp_ctx->target ? mkExpr(cp_ctx->target) : 0;
			ast::ICovergroupCoverpoint *cp = m_factory->mkCovergroupCoverpoint(cp_name, target);
			setLoc(cp, cp_ctx->start);
			cg->getCoverpoints().push_back(ast::ICovergroupCoverpointUP(cp));
		} else if (item->covergroup_cross()) {
			PSSParser::Covergroup_crossContext *cx_ctx = item->covergroup_cross();
			ast::ICovergroupCross *cx = m_factory->mkCovergroupCross(
				mkId(cx_ctx->covercross_identifier()->identifier()));
			setLoc(cx, cx_ctx->start);
			std::vector<PSSParser::Coverpoint_identifierContext *> cp_ids =
				cx_ctx->coverpoint_identifier();
			for (std::vector<PSSParser::Coverpoint_identifierContext *>::const_iterator
				cp_it=cp_ids.begin(); cp_it!=cp_ids.end(); cp_it++) {
				cx->getCoverpoint_names().push_back(
					ast::IExprIdUP(mkId((*cp_it)->identifier())));
			}
			cg->getCrosses().push_back(ast::ICovergroupCrossUP(cx));
		}
		// covergroup_option / compile_if are ignored for now.
	}

	setLoc(cg, ctx->identifier()->start);
	addChild(cg, ctx->start);

	DEBUG_LEAVE("visitInline_covergroup");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAction_handle_declaration(PSSParser::Action_handle_declarationContext *ctx) {
	DEBUG_ENTER("visitAction_handle_declaration");

	std::vector<PSSParser::Action_instantiationContext *> items = ctx->action_instantiation();
	for (std::vector<PSSParser::Action_instantiationContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        ast::IDataType *type = mkDataTypeUserDefined(ctx->action_type_identifier()->type_identifier());
        ast::IExprId *name = 0;
        antlr4::Token *name_tok = 0;
        PSSParser::Action_initializer_listContext *init_l = 0;

        if ((*it)->action_handle_array_instance()) {
            name = mkId((*it)->action_handle_array_instance()->action_identifier()->identifier());
            name_tok = (*it)->action_handle_array_instance()->action_identifier()->start;
            type = applyArrayDims(
                type, (*it)->action_handle_array_instance()->array_dim());
        } else {
            name = mkId((*it)->action_handle_single_instance()->action_identifier()->identifier());
            name_tok = (*it)->action_handle_single_instance()->action_identifier()->start;
            init_l = (*it)->action_handle_single_instance()->action_initializer_list();
        }

        ast::IActionHandleField *field = m_factory->mkActionHandleField(
            name,
            type);
        setLoc(field, name_tok);

        if (init_l) {
            std::vector<ast::IActionFieldInitializer *> inits = mkActionFieldInitializers(init_l);
            for (std::vector<ast::IActionFieldInitializer *>::const_iterator
                init_it=inits.begin();
                init_it!=inits.end(); init_it++) {
                field->getInitializers().push_back(ast::IActionFieldInitializerUP(*init_it));
            }
        }

        addChild(field, ctx->start);
	}

	DEBUG_LEAVE("visitAction_handle_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_data_field(PSSParser::Activity_data_fieldContext *ctx) {
	DEBUG_ENTER("visitActivity_data_field");
	// D2: `activity_data_field` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);
	m_field_depth++;
	m_field_depth--;

	for (std::vector<ast::IField *>::const_iterator
		it=m_fields.begin();
		it!=m_fields.end(); it++) {
		(*it)->setAttr((*it)->getAttr() | FieldAttr::Action);
	}

	if (!m_field_depth) {
		m_fields.clear();
	}
	DEBUG_LEAVE("visitActivity_data_field");
	return 0;
}

static std::map<std::string,ast::StructKind> StructKind_m = {
	{"struct", ast::StructKind::Struct},
	{"buffer", ast::StructKind::Buffer},
	{"resource", ast::StructKind::Resource},
	{"state", ast::StructKind::State},
	{"stream", ast::StructKind::Stream}
};

// B.3 Struct
antlrcpp::Any AstBuilderInt::visitStruct_declaration(PSSParser::Struct_declarationContext *ctx) {
	DEBUG_ENTER("visitStruct_declaration");
	ast::IExprId *id = mkId(ctx->identifier());

	ast::ITypeIdentifier *super_t = 0;


	PSSParser::Struct_super_specContext *super_t_ctx = ctx->struct_super_spec();
	if (super_t_ctx) {
		super_t = mkTypeId(super_t_ctx->type_identifier());
	}

	ast::IStruct *s = m_factory->mkStruct(
		id,
		super_t,
		StructKind_m.find(ctx->struct_kind()->getText())->second);
    setLoc(s, ctx->identifier()->start);

    if (ctx->template_param_decl_list()) {
        s->setParams(mkTypeParamDecl(ctx->template_param_decl_list()));
    }

	addChild(s, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
	push_scope(s);
	ast::StructKind kind = StructKind_m.find(ctx->struct_kind()->getText())->second;
	std::vector<PSSParser::Struct_body_itemContext *> body = ctx->struct_body_item();
	for (std::vector<PSSParser::Struct_body_itemContext *>::const_iterator
		it=body.begin();
		it!=body.end(); it++) {
		(*it)->accept(this);
	}

	// Inject LRM built-in fields so the name resolver accepts references to
	// them: `initial` (bool) on state structs, `instance_id` (int) on resource
	// structs. Skip if the user explicitly declares a field of the same name.
	// Mirrors the synthetic `comp` field added to actions (field resolution
	// for type members walks getChildren(), not the symbol table).
	addStructBuiltinField(s, kind);

	pop_scope();

	DEBUG_LEAVE("visitStruct_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitStruct_body_compile_if(PSSParser::Struct_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(ctx->true_body, ctx->false_body);
    if (!evalCompileTimeCond(ctx->cond, cond, "compile if")) {
        // Reported as an error: elaborate neither branch (19.1.1 promises only
        // that a disabled branch is syntactically correct).
    } else if (cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_body_compile_if(PSSParser::Monitor_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(
        ctx->monitor_body_compile_if_item(0),
        ctx->monitor_body_compile_if_item().size() > 1 ? ctx->monitor_body_compile_if_item(1) : nullptr);
    if (!evalCompileTimeCond(ctx->constant_expression(), cond, "compile if")) {
        // Reported as an error: elaborate neither branch.
    } else if (cond) {
        visitCompileIfItem(ctx->monitor_body_compile_if_item(0));
    } else if (ctx->monitor_body_compile_if_item().size() > 1) {
        visitCompileIfItem(ctx->monitor_body_compile_if_item(1));
    }
    return 0;
}

/* TODO: setLoc checkpoint */

// B.4 Exec blocks

static std::map<std::string, ast::ExecKind> exec_kind_m = {
    { "body", ast::ExecKind::ExecKind_Body },
    { "header", ast::ExecKind::ExecKind_Header },
    { "declaration", ast::ExecKind::ExecKind_Declaration },
    { "run_start", ast::ExecKind::ExecKind_RunStart },
    { "run_end", ast::ExecKind::ExecKind_RunEnd },
    { "init", ast::ExecKind::ExecKind_InitUp },
    { "init_down", ast::ExecKind::ExecKind_InitDown },
    { "init_up", ast::ExecKind::ExecKind_InitUp },
    { "pre_solve", ast::ExecKind::ExecKind_PreSolve },
    { "post_solve", ast::ExecKind::ExecKind_PostSolve },
    { "pre_body", ast::ExecKind::ExecKind_PreBody }
};

antlrcpp::Any AstBuilderInt::visitExec_block(PSSParser::Exec_blockContext *ctx) {
    DEBUG_ENTER("visitExec_block");
    std::map<std::string, ast::ExecKind>::const_iterator kind_it;
    kind_it = exec_kind_m.find(ctx->exec_kind()->identifier()->getText());

    if (kind_it == exec_kind_m.end()) {
	    if (m_marker_l) {
            char tmp[1024];
            std::string msg;
		    ast::Location loc;
		    loc.fileid = m_file_id;
		    loc.lineno = (int32_t)ctx->exec_kind()->identifier()->start->getLine();
		    loc.linepos = (int32_t)ctx->exec_kind()->identifier()->start->getCharPositionInLine()+1;

            snprintf(tmp, sizeof(tmp), 
                "unknown exec-block kind \"%s\" specified. Expect one of ", 
                ctx->exec_kind()->identifier()->getText().c_str());
            msg = tmp;
            msg += "(body, header, declaration, run_start, run_end, init, init_down, init_up, pre_solve, post_solve, pre_body)";

		    Marker m(
				msg,
				MarkerSeverityE::Error,
				loc);
		    m_marker_l->marker(&m);
	    }

        // Stub for now
        kind_it = exec_kind_m.find("body");
    }
    ast::IExecBlock *exec = m_factory->mkExecBlock(
        "<exec>",
        kind_it->second);

    m_exec_scope_s.push_back(exec);
    std::vector<PSSParser::Exec_stmtContext *> items = ctx->exec_stmt();
    for (std::vector<PSSParser::Exec_stmtContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        if ((*it)->exec_super_stmt()) {
            // `super;` -- the other alternative of `exec_stmt`. This branch
            // did not exist, so procedural_stmt() came back null and went
            // straight into mkExecStmt(), which segfaulted the parser (plan
            // phase 1.2). Building the node rather than skipping the
            // statement: dropping it would link cleanly and lose the one
            // thing that distinguishes extending a base exec from replacing
            // it.
            ast::IProceduralStmtSuper *stmt = m_factory->mkProceduralStmtSuper();
            setLoc(stmt, (*it)->start);
            stmt->setIndex(m_exec_scope_s.back()->getChildren().size());
            m_exec_scope_s.back()->getChildren().push_back(
                ast::IScopeChildUP(stmt));
            continue;
        }
        addExecStmt((*it)->procedural_stmt());
    }
    m_exec_scope_s.pop_back();

    addChild(exec, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

    DEBUG_LEAVE("visitExec_block");
    return 0;
}

/**
 * Exec kinds that may carry a tag (20.5.4).
 *
 * A tag exists to let a generator coalesce equivalent emitted code, so it is
 * meaningful only where the code is emitted once per *type*. `body` runs per
 * traversal and the solve execs run during solving, so neither can be
 * deduplicated this way.
 */
static bool execKindAcceptsTag(ast::ExecKind kind) {
    switch (kind) {
        case ast::ExecKind::ExecKind_Header:
        case ast::ExecKind::ExecKind_Declaration:
        case ast::ExecKind::ExecKind_RunStart:
        case ast::ExecKind::ExecKind_RunEnd:
        case ast::ExecKind::ExecKind_File:
            return true;
        default:
            return false;
    }
}

ast::IExecBlockTag *AstBuilderInt::mkExecBlockTag(
        PSSParser::Exec_block_tagContext *ctx) {
    if (!ctx) {
        return 0;
    }
    ast::IExecBlockTag *tag = m_factory->mkExecBlockTag(mkTypeId(ctx->type_identifier()));
    setLoc(tag, ctx->start);

    if (ctx->struct_literal()) {
        ctx->struct_literal()->accept(this);
        tag->setLiteral(dynamic_cast<ast::IExprAggrStruct *>(m_expr));
        m_expr = 0;
    }

    return tag;
}

/**
 * Report a tag written on an exec kind that does not accept one.
 *
 * The restriction is semantic, not grammatical -- the tag is spelled the same
 * way everywhere -- but it needs nothing beyond the exec kind, which is known
 * here, so there is no reason to defer it to the linker.
 */
void AstBuilderInt::checkExecBlockTagPlacement(
        PSSParser::Exec_block_tagContext *tag_ctx,
        ast::ExecKind                     kind,
        const std::string                &kind_s) {
    if (!tag_ctx || execKindAcceptsTag(kind) || !m_marker_l) {
        return;
    }
    char tmp[1024];
    snprintf(tmp, sizeof(tmp),
        "exec block tag is not permitted on '%s' exec blocks",
        kind_s.c_str());

    ast::Location loc;
    loc.fileid = m_file_id;
    loc.lineno = (int32_t)tag_ctx->start->getLine();
    loc.linepos = (int32_t)tag_ctx->start->getCharPositionInLine()+1;

    Marker m(tmp, MarkerSeverityE::Error, loc);
    m_marker_l->marker(&m);
}

/** Strip the quoting from a string_literal's text. */
static std::string execTemplateText(PSSParser::String_literalContext *ctx) {
    if (ctx->DOUBLE_QUOTED_STRING()) {
        std::string value = ctx->DOUBLE_QUOTED_STRING()->getText();
        return value.substr(1, value.size()-2);
    } else {
        std::string value = ctx->TRIPLE_DOUBLE_QUOTED_STRING()->getText();
        return value.substr(3, value.size()-6);
    }
}

antlrcpp::Any AstBuilderInt::visitTarget_code_exec_block(PSSParser::Target_code_exec_blockContext *ctx) {
    DEBUG_ENTER("visitTarget_code_exec_block");

    std::string kind_s = ctx->exec_kind()->identifier()->getText();
    std::map<std::string, ast::ExecKind>::const_iterator kind_it =
        exec_kind_m.find(kind_s);
    ast::ExecKind kind = (kind_it != exec_kind_m.end())?
        kind_it->second:ast::ExecKind::ExecKind_Body;

    checkExecBlockTagPlacement(ctx->exec_block_tag(), kind, kind_s);

    ast::IExecTargetTemplateBlock *exec = m_factory->mkExecTargetTemplateBlock(
        kind,
        execTemplateText(ctx->string_literal()));
    // `data` stays the raw text; `template` is present only when the body has
    // special elements (§4.7.1), which keeps a plain string free of extra nodes.
    exec->setTemplate(mkTemplateString(ctx->string_literal()));
    exec->setLanguage(ctx->language_identifier()->identifier()->getText());
    exec->setTag(mkExecBlockTag(ctx->exec_block_tag()));

    addChild(exec, ctx->start);

    DEBUG_LEAVE("visitTarget_code_exec_block");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitTarget_file_exec_block(PSSParser::Target_file_exec_blockContext *ctx) {
    DEBUG_ENTER("visitTarget_file_exec_block");

    // `exec file` has no exec_kind of its own; ExecKind_File stands in so that
    // downstream code has a single discriminator to switch on.
    checkExecBlockTagPlacement(
        ctx->exec_block_tag(), ast::ExecKind::ExecKind_File, "file");

    ast::IExecTargetTemplateBlock *exec = m_factory->mkExecTargetTemplateBlock(
        ast::ExecKind::ExecKind_File,
        execTemplateText(ctx->string_literal()));
    exec->setTemplate(mkTemplateString(ctx->string_literal()));

    // P5-G1: `filename_string ::= string_literal`, so the filename may now be
    // triple-quoted and carry mustache expressions (§20.5.3). execTemplateText
    // strips whichever quote form was used -- the previous substr(1, n-2) would
    // have mangled a triple-quoted filename.
    exec->setFilename(execTemplateText(ctx->filename_string()->string_literal()));
    exec->setFilename_template(
        mkTemplateString(ctx->filename_string()->string_literal()));
    exec->setTag(mkExecBlockTag(ctx->exec_block_tag()));

    addChild(exec, ctx->start);

    DEBUG_LEAVE("visitTarget_file_exec_block");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitTarget_template_function(
        PSSParser::Target_template_functionContext *ctx) {
    DEBUG_ENTER("visitTarget_template_function");

    // 20.6. Before this existed the construct parsed and was discarded
    // entirely -- no node, no marker (P5-C2).
    //
    // NOTE: the template text is kept verbatim in `data` and is not yet
    // scanned for special elements. P5-I1b adds the `template` field and the
    // scan; this node exists so there is something to attach it to.
    ast::ITargetTemplateFunction *fn = m_factory->mkTargetTemplateFunction(
        mkFunctionPrototype(ctx->function_prototype(), 0),
        ctx->language_identifier()->identifier()->getText(),
        execTemplateText(ctx->string_literal()));
    fn->setIs_static(ctx->TOK_STATIC() != 0);
    fn->setTemplate(mkTemplateString(ctx->string_literal()));

    addChild(fn, ctx->start);

    DEBUG_LEAVE("visitTarget_template_function");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitExec_super_stmt(PSSParser::Exec_super_stmtContext *ctx) {
    DEBUG_ENTER("visitExec_super_stmt");
    DEBUG("TODO: visitExec_super_stmt");
    DEBUG_LEAVE("visitExec_super_stmt");
    return 0;
}

// B.5 Functions
//
// One visitor for both spellings, because the grammar now has one rule for
// both: a declaration ends at `;`, a definition carries a `{ ... }` body. The
// two were separate rules until the profiling harness showed what that cost in
// prediction -- see the note on `function_decl` in PSSParser.g4. The AST is
// unchanged: a declaration still builds a bare IFunctionPrototype and a
// definition still wraps one in an IFunctionDefinition.
antlrcpp::Any AstBuilderInt::visitFunction_decl(PSSParser::Function_declContext *ctx) {
    DEBUG_ENTER("visitFunction_decl");

    // The qualifier goes through mkFunctionPrototype rather than being applied
    // afterwards: the old if/else recorded only `target` for `target solve`.
    ast::IFunctionPrototype *proto = mkFunctionPrototype(
        ctx->function_prototype(),
        ctx->platform_qualifier(),
        ctx->TOK_PURE() != 0);

    if (ctx->TOK_SEMICOLON()) {
        // A prototype: declared here, defined elsewhere (LRM 20.2.1).
        addChild(proto, ctx->start);
        DEBUG_LEAVE("visitFunction_decl (prototype)");
        return 0;
    }

    ast::IExecScope *body = m_factory->mkExecScope("<func-body>");
    std::vector<PSSParser::Procedural_stmtContext *> items = ctx->procedural_stmt();
    DEBUG("Function has %d statements", items.size());
    m_exec_scope_s.push_back(body);
    for (std::vector<PSSParser::Procedural_stmtContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        addExecStmt(*it);
    }
    m_exec_scope_s.pop_back();
    collectScopeTrailingComments(body, ctx->stop);
    DEBUG("Result is %d statements in body", body->getChildren().size());

    ast::PlatQual platqual = ast::PlatQual::PlatQual_None;

    if (ctx->platform_qualifier()) {
        if (ctx->platform_qualifier()->TOK_TARGET()) {
            platqual = ast::PlatQual::PlatQual_Target;
        } else {
            platqual = ast::PlatQual::PlatQual_Solve;
        }
    }

    ast::IFunctionDefinition *func = m_factory->mkFunctionDefinition(
        proto,
        body,
        platqual
    );

    addChild(func, ctx->start);
    DEBUG_LEAVE("visitFunction_decl (definition)");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitFunction_prototype(PSSParser::Function_prototypeContext *ctx) {
    DEBUG_ENTER("visitFunction_prototype");
    DEBUG("TODO: visitFunction_prototype");
    DEBUG_LEAVE("visitFunction_prototype");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitImport_function(PSSParser::Import_functionContext *ctx) {
    DEBUG_ENTER("visitImport_function");
    if (ctx->type_identifier()) {
        // Two-step import specification
    } else {
        // One-step import specification
        ast::PlatQual platqual = ast::PlatQual::PlatQual_None;

        if (ctx->platform_qualifier()) {
            if (ctx->platform_qualifier()->TOK_TARGET()) {
                platqual = ast::PlatQual::PlatQual_Target;
            } else {
                platqual = ast::PlatQual::PlatQual_Solve;
            }
        }

        ast::IFunctionImportProto *func = m_factory->mkFunctionImportProto(
            platqual,
            "",
            mkFunctionPrototype(ctx->function_prototype(), ctx->platform_qualifier())
            );


        addChild(func, ctx->start);
    }
    DEBUG_LEAVE("visitImport_function");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitExport_function(PSSParser::Export_functionContext *ctx) {
    DEBUG_ENTER("visitExport_function");

    ast::IExportFunction *func = m_factory->mkExportFunction(
        ast::PlatQual::PlatQual_Target,
        mkId(ctx->function_identifier()->identifier()));
    setLoc(func, ctx->start);
    addChild(func, ctx->start);

    DEBUG_LEAVE("visitExport_function");
    return 0;
}

// B.7 Procedural Statements
antlrcpp::Any AstBuilderInt::visitProcedural_sequence_block_stmt(PSSParser::Procedural_sequence_block_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_sequence_block_stmt");
    ast::IExecScope *block = m_factory->mkExecScope("<sequence>");
    m_exec_scope_s.push_back(block);

    std::vector<PSSParser::Procedural_stmtContext *> items = ctx->procedural_stmt();
    for (std::vector<PSSParser::Procedural_stmtContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        addExecStmt(*it);
    }

    m_exec_scope_s.pop_back();
    collectScopeTrailingComments(block, ctx->stop);

    m_exec_stmt = block;
    m_exec_stmt_cnt++;
    DEBUG_LEAVE("visitProcedural_sequence_block_stmt (%d)", block->getChildren().size());
    return 0;
}

static std::map<std::string, ast::AssignOp> assign_op_m = {
    { "=", ast::AssignOp::AssignOp_Eq },
    { "+=", ast::AssignOp::AssignOp_PlusEq },
    { "-=", ast::AssignOp::AssignOp_MinusEq },
    { "<<=", ast::AssignOp::AssignOp_ShlEq },
    { ">>=", ast::AssignOp::AssignOp_ShrEq },
    { "|=", ast::AssignOp::AssignOp_OrEq },
    { "&=", ast::AssignOp::AssignOp_AndEq }
};

antlrcpp::Any AstBuilderInt::visitProcedural_assignment_stmt(PSSParser::Procedural_assignment_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_assignment_stmt");
    ast::IExpr *lhs = mkExprRefPath(ctx->ref_path());
    ast::AssignOp op = assign_op_m.find(ctx->assign_op()->getText())->second;
    ast::IExpr *rhs = mkExpr(ctx->expression());

    ast::IProceduralStmtAssignment *stmt = m_factory->mkProceduralStmtAssignment(
        lhs,
        op,
        rhs);

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_assignment_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_void_function_call_stmt(PSSParser::Procedural_void_function_call_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_void_function_call_stmt");
    IExprRefPathStatic *prefix = 0;

    if (ctx->function_call()->is_global || 
        ctx->function_call()->type_identifier_elem().size() > 0) {
        // Have a static component
        prefix = m_factory->mkExprRefPathStatic(ctx->function_call()->is_global);

        std::vector<PSSParser::Type_identifier_elemContext *> items =
            ctx->function_call()->type_identifier_elem();
        for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
            it=items.begin();
            it!=items.end(); it++) {
            prefix->getBase().push_back(ast::ITypeIdentifierElemUP(mkTypeIdElem(*it)));
        }
    }

    IExprHierarchicalId *hid = m_factory->mkExprHierarchicalId();
    std::vector<PSSParser::Member_path_elemContext *> path =
        ctx->function_call()->function_ref_path()->member_path_elem();
    for (std::vector<PSSParser::Member_path_elemContext *>::const_iterator
        it=path.begin();
        it!=path.end(); it++) {
        hid->getElems().push_back(ast::IExprMemberPathElemUP(mkMemberPathElem(*it)));
    }

    // Now, round up the parameter list
    std::vector<PSSParser::ExpressionContext *> items =
        ctx->function_call()->function_ref_path()->function_parameter_list()->expression();
    ast::IMethodParameterList *params = m_factory->mkMethodParameterList();
    for (std::vector<PSSParser::ExpressionContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        params->getParameters().push_back(ast::IExprUP(mkExpr(*it)));
    }

    hid->getElems().push_back(ast::IExprMemberPathElemUP(
        m_factory->mkExprMemberPathElem(
            mkId(ctx->function_call()->function_ref_path()->identifier()),
            params)
    ));

    if (prefix && hid) {
        DEBUG("Creating an ExprRefPathStaticRooted expression");
        ast::IProceduralStmtExpr *stmt = m_factory->mkProceduralStmtExpr(
            m_factory->mkExprRefPathStaticRooted(
                prefix,
                hid));
        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    } else {
        DEBUG("Creating an ExprRefPathContext expression");
        ast::IProceduralStmtExpr *stmt = m_factory->mkProceduralStmtExpr(
            m_factory->mkExprRefPathContext(hid));
        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    }

    DEBUG_LEAVE("visitProcedural_void_function_call_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_return_stmt(PSSParser::Procedural_return_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_return_stmt");
    ast::IExpr *expr = ctx->expression()?mkExpr(ctx->expression()):0;
    ast::IProceduralStmtReturn *stmt = m_factory->mkProceduralStmtReturn(expr);
    // Without this the statement has no location, so a diagnostic about it
    // has to point at the enclosing function's name instead -- unhelpful in a
    // body with more than one `return`.
    setLoc(stmt, ctx->start);

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_return_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_repeat_stmt(PSSParser::Procedural_repeat_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_repeat_stmt");
    if (ctx->is_repeat) {
        ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());
        ast::IProceduralStmtRepeat *stmt = m_factory->mkProceduralStmtRepeat(
            "<repeat>",
            body,
            (ctx->identifier())?mkId(ctx->identifier()):0,
            mkExpr(ctx->expression()));

        ast::IExprId *id = 0;
        if (stmt->getIt_id()) {
            // Add a variable to the scope
            id = m_factory->mkExprId(
                    stmt->getIt_id()->getId(),
                    stmt->getIt_id()->getIs_escaped());
            id->setLocation(stmt->getIt_id()->getLocation());
        } else {
            id = m_factory->mkExprId("_", false);
        }

        ast::IProceduralStmtDataDeclaration *var = m_factory->mkProceduralStmtDataDeclaration(
            id,
            0,
            0);
        var->setIndex(stmt->getChildren().size());
        if (stmt->getIt_id()) {
            stmt->getSymtab().insert({id->getId(), stmt->getChildren().size()});
        }
        stmt->getChildren().push_back(ast::IScopeChildUP(var));

        // `repeat (...) ;` -- an empty statement -- leaves body null.
        if (body) {
            body->setIndex(stmt->getChildren().size());
        }

        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    } else if (ctx->is_repeat_while) {
        ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());
        // `repeat ; while (...);` -- an empty statement -- leaves body null.
        if (body) {
            body->setIndex(0);
        }
        ast::IProceduralStmtRepeatWhile *stmt = m_factory->mkProceduralStmtRepeatWhile(
            body,
            mkExpr(ctx->expression()));
        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    } else { // 'while'
        ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());
        // `while (...);` -- an empty statement -- leaves body null.
        if (body) {
            body->setIndex(0);
        }
        ast::IProceduralStmtWhile *stmt = m_factory->mkProceduralStmtWhile(
            body,
            mkExpr(ctx->expression()));
        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    }

//    m_exec_stmt = 0;
//    m_exec_stmt_cnt--;


    DEBUG_LEAVE("visitProcedural_repeat_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_foreach_stmt(PSSParser::Procedural_foreach_stmtContext *ctx) {
    DEBUG_ENTER("visitProcedural_foreach_stmt");

    // Collection reference. Grammar uses a general `expression`, which (being
    // greedy) folds a trailing `[idx]` into a subscript on the path.
    ast::IExpr *expr = mkExpr(ctx->expression());
    ast::IExprRefPathContext *path = dynamic_cast<ast::IExprRefPathContext *>(expr);

    ast::IExprId *it_id  = ctx->iterator_identifier()
                           ? mkId(ctx->iterator_identifier()->identifier()) : 0;
    ast::IExprId *idx_id = ctx->index_identifier()
                           ? mkId(ctx->index_identifier()->identifier())    : 0;

    // If no explicit index_identifier was parsed, recover it from the trailing
    // subscript that expression parsing greedily consumed (mirrors
    // visitForeach_constraint_item).
    if (!idx_id && path && path->getHier_id()->getElems().back()->getSubscript().size()) {
        std::vector<ast::IExprUP> &subscript = path->getHier_id()->getElems().back()->getSubscript();
        ast::IExprRefPathContext *idx_ref = dynamic_cast<ast::IExprRefPathContext *>(subscript.back().get());
        if (idx_ref && idx_ref->getHier_id()->getElems().size() == 1
                && !idx_ref->getHier_id()->getElems().back()->getSubscript().size()) {
            ast::IExprId *idx = idx_ref->getHier_id()->getElems().back()->getId();
            idx_id = m_factory->mkExprId(idx->getId(), idx->getIs_escaped());
            idx_id->setLocation(idx->getLocation());
            subscript.pop_back();
        }
    }

    ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());

    ast::IProceduralStmtForeach *stmt = m_factory->mkProceduralStmtForeach(
        "<foreach>",
        body,
        path,
        it_id,
        idx_id);

    // Register iterator and index variables in the scope's symtab so the body
    // can resolve them (mirrors visitProcedural_repeat_stmt's index var).
    if (it_id) {
        ast::IExprId *id = m_factory->mkExprId(it_id->getId(), it_id->getIs_escaped());
        id->setLocation(it_id->getLocation());
        ast::IProceduralStmtDataDeclaration *var = m_factory->mkProceduralStmtDataDeclaration(id, 0, 0);
        var->setIndex(stmt->getChildren().size());
        stmt->getSymtab().insert({id->getId(), stmt->getChildren().size()});
        stmt->getChildren().push_back(ast::IScopeChildUP(var));
    }
    if (idx_id) {
        ast::IExprId *id = m_factory->mkExprId(idx_id->getId(), idx_id->getIs_escaped());
        id->setLocation(idx_id->getLocation());
        ast::IProceduralStmtDataDeclaration *var = m_factory->mkProceduralStmtDataDeclaration(id, 0, 0);
        var->setIndex(stmt->getChildren().size());
        stmt->getSymtab().insert({id->getId(), stmt->getChildren().size()});
        stmt->getChildren().push_back(ast::IScopeChildUP(var));
    }

    if (body) {
        body->setIndex(stmt->getChildren().size());
    }

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_foreach_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_if_else_stmt(PSSParser::Procedural_if_else_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_if_else_stmt");

    ast:IProceduralStmtIfElse *stmt = m_factory->mkProceduralStmtIfElse();

    ast::IExpr *cond = mkExpr(ctx->expression());
    ast::IScopeChild *if_s = mkExecStmt(ctx->procedural_stmt(0));
    ast::IProceduralStmtIfClause *clause = m_factory->mkProceduralStmtIfClause(
        cond,
        if_s);
    DEBUG("Add initial if clause");
    stmt->getIf_then().push_back(ast::IProceduralStmtIfClauseUP(clause));

    PSSParser::Procedural_stmtContext *else_ctx = ctx->procedural_stmt(1);

    // Process else-if stmts
    while (else_ctx && else_ctx->procedural_if_else_stmt()) {
        cond = mkExpr(else_ctx->procedural_if_else_stmt()->expression());
        if_s = mkExecStmt(else_ctx->procedural_if_else_stmt()->procedural_stmt(0));
        clause = m_factory->mkProceduralStmtIfClause(
            cond,
            if_s);
        DEBUG("Add if-then clause");
        stmt->getIf_then().push_back(ast::IProceduralStmtIfClauseUP(clause));
        else_ctx = else_ctx->procedural_if_else_stmt()->procedural_stmt(1);
    }

    // Now, add final 'else' if present
    if (else_ctx) {
        DEBUG("Add final 'else' clause");
        ast::IScopeChild *else_s = mkExecStmt(else_ctx);
        stmt->setElse_then(else_s);
    } else {
        DEBUG("No final 'else' clause");
    }

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;
    DEBUG_LEAVE("visitProcedural_if_else_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_match_stmt(PSSParser::Procedural_match_stmtContext *ctx) {
    DEBUG_ENTER("visitProcedural_match_stmt");

    ast::IExpr *cond_expr = mkExpr(ctx->expression());
    ast::IProceduralStmtMatch *stmt = m_factory->mkProceduralStmtMatch(cond_expr);

    for (auto *choice : ctx->procedural_match_choice()) {
        bool is_default = (choice->TOK_DEFAULT() != nullptr);
        ast::IExprOpenRangeList *cond = (is_default || !choice->open_range_list())
                                        ? nullptr
                                        : mkOpenRangeList(choice->open_range_list());
        ast::IScopeChild *body = mkExecStmt(choice->procedural_stmt());
        ast::IProceduralStmtMatchChoice *mc = m_factory->mkProceduralStmtMatchChoice(
            is_default, cond, body);
        stmt->getChoices().push_back(ast::IProceduralStmtMatchChoiceUP(mc));
    }

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_match_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_break_stmt(PSSParser::Procedural_break_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_break_stmt");
    ast::IProceduralStmtBreak *stmt = m_factory->mkProceduralStmtBreak();

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;
    DEBUG_LEAVE("visitProcedural_break_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_continue_stmt(PSSParser::Procedural_continue_stmtContext *ctx) { 
    DEBUG_ENTER("visitProcedural_continue_stmt");
    ast::IProceduralStmtContinue *stmt = m_factory->mkProceduralStmtContinue();

    m_exec_stmt = stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_continue_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_data_declaration(PSSParser::Procedural_data_declarationContext *ctx) { 
    DEBUG_ENTER("visitProcedural_data_declaration");

    std::vector<PSSParser::Procedural_data_instantiationContext *> items = ctx->procedural_data_instantiation();
    for (std::vector<PSSParser::Procedural_data_instantiationContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ast::IDataType *type = mkDataType(ctx->data_type());
        ast::IExprId *name = mkId((*it)->identifier());
        ast::IExpr *init = ((*it)->expression())?mkExpr((*it)->expression()):0;

        type = applyArrayDims(type, (*it)->array_dim());

        ast::IProceduralStmtDataDeclaration *decl = m_factory->mkProceduralStmtDataDeclaration(
            name,
            type,
            init);
        decl->setIndex(m_exec_scope_s.back()->getChildren().size());

        // This visitor pushes straight into the exec scope rather than
        // returning through mkExecStmt, so it has to record its own
        // provenance. `int a, b;` is one source statement and several decls;
        // only the first carries the comment, per the no-duplication rule.
        if (ctx->getStart()) {
            decl->setLocation({
                m_file_id,
                (int32_t)ctx->getStart()->getLine(),
                (int32_t)ctx->getStart()->getCharPositionInLine()+1
            });
            if (m_collectDocStrings && it == items.begin()) {
                attachDocstring(decl, ctx->getStart());
            }
        }

        m_exec_scope_s.back()->getChildren().push_back(ast::IScopeChildUP(decl));

        std::unordered_map<std::string,int32_t>::const_iterator var_it =
            m_exec_scope_s.back()->getSymtab().find(decl->getName()->getId());
        if (var_it != m_exec_scope_s.back()->getSymtab().end()) {
            // TODO: duplicate
	        if (m_marker_l) {
                char tmp[1024];
                std::string msg;
		        ast::Location loc = decl->getLocation();

                snprintf(tmp, sizeof(tmp), "duplicate variable declaration %s",  
                    decl->getName()->getId().c_str());
                msg = tmp;
                msg += ", previously declared"; 

		        Marker m(
				    msg,
				    MarkerSeverityE::Error,
				    loc);
    		    m_marker_l->marker(&m);
            }
        } else {
            m_exec_scope_s.back()->getSymtab().insert({
                decl->getName()->getId(),
                decl->getIndex()
            });
        }
    }

    // We've already added to the super scope
    m_exec_stmt = 0;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_data_declaration");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_yield_stmt(PSSParser::Procedural_yield_stmtContext *ctx) {
    DEBUG_ENTER("visitProcedural_yield_stmt");

    m_exec_stmt = m_factory->mkProceduralStmtYield();
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_yield_stmt");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_randomization_stmt(PSSParser::Procedural_randomization_stmtContext *ctx) {
    DEBUG_ENTER("visitProcedural_randomization_stmt");

    // Get the target expression(s)
    ast::IExpr *target = 0;
    if (ctx->procedural_randomization_target()) {
        // TODO: Process randomization target properly
        // For now, create a simple null target
    }

    // TODO: Handle constraints from procedural_randomization_term
    // if (ctx->procedural_randomization_term() && ctx->procedural_randomization_term()->constraint_set())

    // Create the randomize statement
    ast::IProceduralStmtRandomize *rand_stmt = m_factory->mkProceduralStmtRandomize(target);
    setLoc(rand_stmt, ctx->start);

    m_exec_stmt = rand_stmt;
    m_exec_stmt_cnt++;

    DEBUG_LEAVE("visitProcedural_randomization_stmt");
    return 0;
}

// B.8 Component declarations

antlrcpp::Any AstBuilderInt::visitComponent_declaration(PSSParser::Component_declarationContext *ctx) {
	DEBUG_ENTER("visitComponent_declaration");
	ast::ITypeIdentifier *super_t = 0;

	if (ctx->component_super_spec()) {
		super_t = mkTypeId(ctx->component_super_spec()->type_identifier());
	}

	ast::IComponent *comp = m_factory->mkComponent(
		mkId(ctx->component_identifier()->identifier()),
		super_t);

    // 'pure component' declares every function of the component pure (P5-X3).
    // The grammar has always accepted the token; until this, nothing read it,
    // so PSS114 reported a call to any function of `reg_c` as non-pure.
    comp->setIs_pure(ctx->TOK_PURE() != 0);

    if (ctx->template_param_decl_list()) {
        comp->setParams(mkTypeParamDecl(ctx->template_param_decl_list()));
    }

	addChild(comp, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	push_scope(comp);

    if (!super_t) {
        // TODO: add in predefined methods
        DEBUG("Add set_executor() method (%s)", comp->getName()->getId().c_str());
        ast::IFunctionPrototype *set_executor = m_factory->mkFunctionPrototype(
            m_factory->mkExprId("set_executor", false),
            0,
            false,
            true);
        set_executor->setIs_core(true);
        comp->getChildren().push_back(ast::IScopeChildUP(set_executor));
    } else {
        DEBUG("Have base type. Not adding set_executor() method (%s)",
            comp->getName()->getId().c_str());
    }

#ifdef UNDEFINED
    ast::IFunctionPrototype *set_default_executor = m_factory->mkFunctionPrototype(
        m_factory->mkExprId("set_default_executor", false),
        0,
        false,
        true);
    addChild(set_default_executor, 0, 0);
#endif // UNDEFINED

	std::vector<PSSParser::Component_body_item_annContext *> body = ctx->component_body_item_ann();
	for (std::vector<PSSParser::Component_body_item_annContext *>::const_iterator
		it=body.begin();
		it!=body.end(); it++) {
		(*it)->accept(this);
	}
	pop_scope();

	DEBUG_LEAVE("visitComponent_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitComponent_body_compile_if(PSSParser::Component_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(ctx->true_body, ctx->false_body);
    if (!evalCompileTimeCond(ctx->cond, cond, "compile if")) {
        // Reported as an error: elaborate neither branch (19.1.1 promises only
        // that a disabled branch is syntactically correct).
    } else if (cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitComponent_data_declaration(PSSParser::Component_data_declarationContext *ctx) {
    DEBUG_ENTER("visitComponent_data_declaration");
	// D2: `component_data_declaration` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);

    m_field_depth++;
    ctx->data_declaration()->accept(this);
    m_field_depth--;

    for (std::vector<ast::IField *>::const_iterator
        it=m_fields.begin();
        it!=m_fields.end(); it++) {
        FieldAttr attr = (*it)->getAttr();

        attr |= accessModifierToFieldAttr(ctx->access_modifier());

        if (ctx->is_static) {
            attr |= FieldAttr::Static;
            attr |= FieldAttr::Const;
        }
        if (ctx->is_instance) {
            attr |= FieldAttr::Instance;
        }
        if (ctx->is_mutable) {
            attr |= FieldAttr::Mutable;
        }

        (*it)->setAttr(attr);
    }

    if (!m_field_depth) {
        m_fields.clear();
    }

    DEBUG_LEAVE("visitComponent_data_declaration");
    return 0;
}

// Monitor declarations (PSS 3.0)

antlrcpp::Any AstBuilderInt::visitMonitor_declaration(PSSParser::Monitor_declarationContext *ctx) {
	DEBUG_ENTER("visitMonitor_declaration");
	ast::ITypeIdentifier *super_t = 0;

	if (ctx->monitor_super_spec()) {
		super_t = mkTypeId(ctx->monitor_super_spec()->type_identifier());
	}

	ast::IMonitor *monitor = m_factory->mkMonitor(
		mkId(ctx->monitor_identifier()->identifier()),
		super_t);
	monitor->setIs_abstract(false);
    setLoc(monitor, ctx->start);

	if (ctx->template_param_decl_list()) {
        monitor->setParams(mkTypeParamDecl(ctx->template_param_decl_list()));
	}

	addChild(monitor, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
	push_scope(monitor);

	std::vector<PSSParser::Monitor_body_itemContext *> items = ctx->monitor_body_item();

	for (std::vector<PSSParser::Monitor_body_itemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}

	pop_scope();

	DEBUG_LEAVE("visitMonitor_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAbstract_monitor_declaration(PSSParser::Abstract_monitor_declarationContext *ctx) {
	DEBUG_ENTER("visitAbstract_monitor_declaration");
	// D2: `abstract_monitor_declaration` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);
	ast::ITypeIdentifier *super_t = 0;

	PSSParser::Monitor_declarationContext *decl_ctx = ctx->monitor_declaration();

	if (decl_ctx->monitor_super_spec()) {
		super_t = mkTypeId(decl_ctx->monitor_super_spec()->type_identifier());
	}

	ast::IMonitor *monitor = m_factory->mkMonitor(
		mkId(decl_ctx->monitor_identifier()->identifier()),
		super_t);
	monitor->setIs_abstract(true);
    setLoc(monitor, decl_ctx->start);

	if (decl_ctx->template_param_decl_list()) {
        monitor->setParams(mkTypeParamDecl(decl_ctx->template_param_decl_list()));
	}

	addChild(monitor, decl_ctx->start, decl_ctx->TOK_RCBRACE()->getSymbol());
	push_scope(monitor);

	std::vector<PSSParser::Monitor_body_itemContext *> items = decl_ctx->monitor_body_item();

	for (std::vector<PSSParser::Monitor_body_itemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}

	pop_scope();

	DEBUG_LEAVE("visitAbstract_monitor_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_declaration(PSSParser::Monitor_activity_declarationContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_declaration");

	ast::IMonitorActivityDecl *activity = m_factory->mkMonitorActivityDecl("");
    setLoc(activity, ctx->start);

	addChild(activity, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	// TODO: Handle monitor activity statements
	std::vector<PSSParser::Monitor_activity_stmtContext *> stmts = ctx->monitor_activity_stmt();
	for (std::vector<PSSParser::Monitor_activity_stmtContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		// (*it)->accept(this);
	}

	DEBUG_LEAVE("visitMonitor_activity_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_sequence_block_stmt(PSSParser::Monitor_activity_sequence_block_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_sequence_block_stmt");

	ast::IMonitorActivitySequence *seq = m_factory->mkMonitorActivitySequence("");
    setLoc(seq, ctx->start);

	addChild(seq, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	// Monitor activity statements - for now, just traverse them
	// TODO: Properly handle monitor activity statements once visitor pattern is clear
	std::vector<PSSParser::Monitor_activity_stmtContext *> stmts = ctx->monitor_activity_stmt();
	for (std::vector<PSSParser::Monitor_activity_stmtContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		// (*it)->accept(this);
	}

	DEBUG_LEAVE("visitMonitor_activity_sequence_block_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_concat_stmt(PSSParser::Monitor_activity_concat_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_concat_stmt");

	// Concat is represented as a scope containing statements
	ast::IMonitorActivitySequence *concat = m_factory->mkMonitorActivitySequence("");
    setLoc(concat, ctx->start);

	addChild(concat, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	// TODO: Handle monitor activity statements
	std::vector<PSSParser::Monitor_activity_stmtContext *> stmts = ctx->monitor_activity_stmt();
	for (std::vector<PSSParser::Monitor_activity_stmtContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		// (*it)->accept(this);
	}

	DEBUG_LEAVE("visitMonitor_activity_concat_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_eventually_stmt(PSSParser::Monitor_activity_eventually_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_eventually_stmt");

	// For now, create a simple eventually statement with null condition
	// TODO: Handle condition properly when spec is clearer
	ast::IMonitorActivityEventually *eventually = m_factory->mkMonitorActivityEventually(
		0,  // condition
		0   // body
	);
    setLoc(eventually, ctx->start);

	// Add to current scope as a child
	ast::ISymbolScope *sym_scope = dynamic_cast<ast::ISymbolScope *>(scope());
	if (sym_scope) {
		eventually->setIndex(sym_scope->getChildren().size());
		sym_scope->getChildren().push_back(ast::IScopeChildUP(eventually));
	}

	DEBUG_LEAVE("visitMonitor_activity_eventually_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_overlap_stmt(PSSParser::Monitor_activity_overlap_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_overlap_stmt");

	// Overlap is represented as a scope containing statements
	ast::IMonitorActivitySequence *overlap = m_factory->mkMonitorActivitySequence("");
    setLoc(overlap, ctx->start);

	addChild(overlap, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	// TODO: Handle monitor activity statements
	std::vector<PSSParser::Monitor_activity_stmtContext *> stmts = ctx->monitor_activity_stmt();
	for (std::vector<PSSParser::Monitor_activity_stmtContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		// (*it)->accept(this);
	}

	DEBUG_LEAVE("visitMonitor_activity_overlap_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_schedule_stmt(PSSParser::Monitor_activity_schedule_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_schedule_stmt");

	ast::IMonitorActivitySchedule *schedule = m_factory->mkMonitorActivitySchedule("");
    setLoc(schedule, ctx->start);

	addChild(schedule, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

	// TODO: Handle monitor activity statements
	std::vector<PSSParser::Monitor_activity_stmtContext *> stmts = ctx->monitor_activity_stmt();
	for (std::vector<PSSParser::Monitor_activity_stmtContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		// (*it)->accept(this);
	}

	DEBUG_LEAVE("visitMonitor_activity_schedule_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_activity_monitor_traversal_stmt(PSSParser::Monitor_activity_monitor_traversal_stmtContext *ctx) {
	DEBUG_ENTER("visitMonitor_activity_monitor_traversal_stmt");

	// TODO: Properly construct target reference path
	ast::IExprRefPath *target = 0;
	ast::IConstraintStmt *with_c = 0;

	ast::IMonitorActivityMonitorTraversal *traversal = m_factory->mkMonitorActivityMonitorTraversal(
		target,
		with_c
	);
    setLoc(traversal, ctx->start);

	// Add to current scope as a child
	ast::ISymbolScope *sym_scope = dynamic_cast<ast::ISymbolScope *>(scope());
	if (sym_scope) {
		traversal->setIndex(sym_scope->getChildren().size());
		sym_scope->getChildren().push_back(ast::IScopeChildUP(traversal));
	}

	DEBUG_LEAVE("visitMonitor_activity_monitor_traversal_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitCover_stmt(PSSParser::Cover_stmtContext *ctx) {
	DEBUG_ENTER("visitCover_stmt");

	// TODO: Implement cover statement visitor
	// For now, just create a placeholder
	DEBUG("Cover statement visitor not yet implemented");

	DEBUG_LEAVE("visitCover_stmt");
	return 0;
}

// B.9 Activity statements

antlrcpp::Any AstBuilderInt::visitActivity_labeled_stmt(PSSParser::Activity_labeled_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_labeled_stmt");
	if (ctx->identifier()) {
		m_labeled_activity_id = mkId(ctx->identifier());
	} else {
		m_labeled_activity_id = 0;
	}
	ctx->labeled_activity_stmt()->accept(this);

	m_labeled_activity_id = 0;

	DEBUG_LEAVE("visitActivity_labeled_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_action_traversal_stmt(PSSParser::Activity_action_traversal_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_action_traversal_stmt");
	ast::IActivityLabeledStmt *stmt = 0;
	ast::IConstraintStmt *with_c = 0;

	PSSParser::Inline_constraints_or_emptyContext *with_ctx = 0;
	if (ctx->action_handle_traversal_stmt()) {
		with_ctx = ctx->action_handle_traversal_stmt()->inline_constraints_or_empty();
	} else {
		with_ctx = ctx->action_type_traversal_stmt()->inline_constraints_or_empty();
	}

	if (with_ctx->constraint_set()) {
		with_c = mkConstraintSet(with_ctx->constraint_set());
	}

	if (ctx->action_type_traversal_stmt()) {
		// By-type traversal
		stmt = m_factory->mkActivityActionTypeTraversal(
			mkDataTypeUserDefined(ctx->action_type_traversal_stmt()->type_identifier()),
			with_c);
        PSSParser::Action_initializer_listContext *init_l =
            ctx->action_type_traversal_stmt()->action_initializer_list();
        if (init_l) {
            std::vector<ast::IActionFieldInitializer *> inits = mkActionFieldInitializers(init_l);
            ast::IActivityActionTypeTraversal *typed = dynamic_cast<ast::IActivityActionTypeTraversal *>(stmt);
            for (std::vector<ast::IActionFieldInitializer *>::const_iterator
                it=inits.begin();
                it!=inits.end(); it++) {
                typed->getInitializers().push_back(ast::IActionFieldInitializerUP(*it));
            }
        }
	} else {
		// Handle traversal
		ast::IExprHierarchicalId *path = m_factory->mkExprHierarchicalId();
		ast::IExprMemberPathElem *elem = m_factory->mkExprMemberPathElem(
			mkId(ctx->action_handle_traversal_stmt()->identifier()),
			0);
        std::vector<PSSParser::ExpressionContext *> subscripts =
            ctx->action_handle_traversal_stmt()->expression();
        for (std::vector<PSSParser::ExpressionContext *>::const_iterator
            it=subscripts.begin();
            it!=subscripts.end(); it++) {
            elem->getSubscript().push_back(ast::IExprUP(mkExpr(*it)));
        }
		path->getElems().push_back(ast::IExprMemberPathElemUP(elem));
		ast::IExprRefPathContext *target = m_factory->mkExprRefPathContext(path);

		stmt = m_factory->mkActivityActionHandleTraversal(
			target,
			with_c);
        PSSParser::Action_initializer_listContext *init_l =
            ctx->action_handle_traversal_stmt()->action_initializer_list();
        if (init_l) {
            std::vector<ast::IActionFieldInitializer *> inits = mkActionFieldInitializers(init_l);
            ast::IActivityActionHandleTraversal *typed = dynamic_cast<ast::IActivityActionHandleTraversal *>(stmt);
            for (std::vector<ast::IActionFieldInitializer *>::const_iterator
                it=inits.begin();
                it!=inits.end(); it++) {
                typed->getInitializers().push_back(ast::IActionFieldInitializerUP(*it));
            }
        }
	}

	if (m_labeled_activity_id) {
		stmt->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	m_activity_stmt = stmt;

	DEBUG_LEAVE("visitActivity_action_traversal_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_sequence_block_stmt(PSSParser::Activity_sequence_block_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_sequence_block_stmt");
	ast::IActivitySequence *seq = m_factory->mkActivitySequence("");

	if (m_labeled_activity_id) {
		seq->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	std::vector<PSSParser::Activity_stmt_annContext *> items = ctx->activity_stmt_ann();
	for (std::vector<PSSParser::Activity_stmt_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        addActivityStmt(seq, *it);
	}

	m_activity_stmt = seq;

	DEBUG_LEAVE("visitActivity_sequence_block_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_parallel_stmt(PSSParser::Activity_parallel_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_parallel_stmt");

	ast::IActivityJoinSpec *spec = 0;
	if (ctx->activity_join_spec()) {
		spec = mkActivityJoinSpec(ctx->activity_join_spec());
	}

	ast::IActivityParallel *par = m_factory->mkActivityParallel("", spec);

	if (m_labeled_activity_id) {
		par->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}


	std::vector<PSSParser::Activity_stmt_annContext *> items = ctx->activity_stmt_ann();
	for (std::vector<PSSParser::Activity_stmt_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        addActivityStmt(par, *it);
	}

	m_activity_stmt = par;

	DEBUG_LEAVE("visitActivity_parallel_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_schedule_stmt(PSSParser::Activity_schedule_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_schedule_stmt");

	ast::IActivityJoinSpec *spec = 0;
	if (ctx->activity_join_spec()) {
		spec = mkActivityJoinSpec(ctx->activity_join_spec());
	}

	ast::IActivitySchedule *sched = m_factory->mkActivitySchedule("", spec);

	if (m_labeled_activity_id) {
		sched->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	std::vector<PSSParser::Activity_stmt_annContext *> items = ctx->activity_stmt_ann();
	for (std::vector<PSSParser::Activity_stmt_annContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        addActivityStmt(sched, *it);
	}

	m_activity_stmt = sched;

	DEBUG_LEAVE("visitActivity_schedule_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_repeat_stmt(PSSParser::Activity_repeat_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_repeat_stmt");

	IActivityLabeledStmt *stmt = 0;

	if (ctx->is_repeat) {
		ast::IExprId *label = m_labeled_activity_id;
        ast::IScopeChild *body = mkActivityStmt(ctx->activity_stmt_ann());
        if (!body) {
            body = m_factory->mkActivitySequence("");
        }

        // Register the loop variable as a synthetic field in the body scope so
        // `with` constraints inside the loop body can reference it by name.
        if (ctx->loop_var) {
            auto *body_scope = dynamic_cast<ast::ISymbolScope*>(body);
            if (body_scope) {
                addSyntheticIntField(body_scope, ctx->loop_var->getText());
            }
        }

		ast::IActivityRepeatCount *rstmt = m_factory->mkActivityRepeatCount(
			(ctx->loop_var)?mkId(ctx->loop_var):0,
			mkExpr(ctx->expression()),
            body);
        stmt = rstmt;
	} else {
		// do { body } while (cond);
		ast::IScopeChild *body = mkActivityStmt(ctx->activity_stmt_ann());
		if (!body) {
			body = m_factory->mkActivitySequence("");
		}
		ast::IActivityRepeatWhile *rw = m_factory->mkActivityRepeatWhile(
			mkExpr(ctx->expression()),
			body);
		stmt = rw;
	}

	if (m_labeled_activity_id) {
		stmt->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	m_activity_stmt = stmt;

	DEBUG_LEAVE("visitActivity_repeat_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_atomic_block_stmt(PSSParser::Activity_atomic_block_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_atomic_block_stmt");

	// Create a sequence to hold the atomic block statements
	ast::IActivitySequence *seq = m_factory->mkActivitySequence("");
	
	std::vector<PSSParser::Activity_stmt_annContext *> stmts = ctx->activity_stmt_ann();
	for (std::vector<PSSParser::Activity_stmt_annContext *>::const_iterator
		it=stmts.begin();
		it!=stmts.end(); it++) {
		addActivityStmt(seq, *it);
	}

	ast::IActivityAtomicBlock *atomic = m_factory->mkActivityAtomicBlock(seq);
	setLoc(atomic, ctx->start);

	if (m_labeled_activity_id) {
		atomic->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	m_activity_stmt = atomic;

	DEBUG_LEAVE("visitActivity_atomic_block_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_select_stmt(PSSParser::Activity_select_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_select_stmt");

	ast::IActivitySelect *sel = m_factory->mkActivitySelect();

	if (m_labeled_activity_id) {
		sel->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	for (auto *b : ctx->select_branch()) {
		ast::IExpr *guard  = b->guard  ? mkExpr(b->guard)  : nullptr;
		ast::IExpr *weight = b->weight ? mkExpr(b->weight) : nullptr;
		ast::IScopeChild *body = mkActivityStmt(b->activity_stmt_ann());
		if (!body) {
			body = m_factory->mkActivitySequence("");
		}
		ast::IActivitySelectBranch *branch = m_factory->mkActivitySelectBranch(guard, weight, body);
		sel->getBranches().push_back(ast::IActivitySelectBranchUP(branch));
	}

	m_activity_stmt = sel;

	DEBUG_LEAVE("visitActivity_select_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_if_else_stmt(PSSParser::Activity_if_else_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_if_else_stmt");

	ast::IExpr *cond = mkExpr(ctx->expression());
	ast::IScopeChild *true_body  = mkActivityStmt(ctx->activity_stmt_ann(0));
	ast::IScopeChild *false_body = (ctx->activity_stmt_ann().size() > 1)
	                               ? mkActivityStmt(ctx->activity_stmt_ann(1))
	                               : nullptr;

	// mkActivityIfElse takes IActivityStmt*; the bodies are IScopeChild* which
	// also implement IActivityStmt via the generated hierarchy.
	ast::IActivityIfElse *ife = m_factory->mkActivityIfElse(
		cond,
		dynamic_cast<ast::IActivityStmt*>(true_body),
		dynamic_cast<ast::IActivityStmt*>(false_body));

	if (m_labeled_activity_id) {
		ife->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	m_activity_stmt = ife;

	DEBUG_LEAVE("visitActivity_if_else_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_match_stmt(PSSParser::Activity_match_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_match_stmt");

	ast::IExpr *cond_expr = mkExpr(ctx->expression());
	ast::IActivityMatch *match = m_factory->mkActivityMatch(cond_expr);

	if (m_labeled_activity_id) {
		match->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	for (auto *choice : ctx->match_choice()) {
		bool is_default = (choice->is_default != nullptr);
		ast::IExprOpenRangeList *cond = is_default
		                               ? nullptr
		                               : mkOpenRangeList(choice->open_range_list());
		ast::IScopeChild *body = mkActivityStmt(choice->activity_stmt_ann());
		if (!body) {
			body = m_factory->mkActivitySequence("");
		}
		ast::IActivityMatchChoice *mc = m_factory->mkActivityMatchChoice(is_default, cond, body);
		match->getChoices().push_back(ast::IActivityMatchChoiceUP(mc));
	}

	m_activity_stmt = match;

	DEBUG_LEAVE("visitActivity_match_stmt");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitActivity_foreach_stmt(PSSParser::Activity_foreach_stmtContext *ctx) {
	DEBUG_ENTER("visitActivity_foreach_stmt");

	ast::IExprId *it_id  = ctx->it_id  ? mkId(ctx->it_id->identifier())  : nullptr;
	ast::IExprId *idx_id = ctx->idx_id ? mkId(ctx->idx_id->identifier()) : nullptr;

	// B.9: the traversal target is an `expression`, not a bare identifier, so
	// `foreach (a.b[0].c)` is legal. Every conforming target is a reference to
	// a collection, which is what ExprRefPathContext models.
	ast::IExpr *target_e = mkExpr(ctx->expression());
	ast::IExprRefPathContext *target =
		dynamic_cast<ast::IExprRefPathContext *>(target_e);

	if (!target) {
		ast::Location loc;
		loc.fileid = m_file_id;
		loc.lineno = ctx->expression()->start->getLine();
		loc.linepos = ctx->expression()->start->getCharPositionInLine()+1;
		loc.extent = ctx->expression()->getText().size();
		Marker m(
			"foreach traversal target must be a reference to a collection",
			MarkerSeverityE::Error,
			loc);
		if (m_marker_l) { m_marker_l->marker(&m); }
	} else if (!idx_id) {
		// Expressions are greedy, so `foreach (a[i])` parses the index variable
		// as a subscript of `a` rather than matching the optional [idx_id].
		// Lift a trailing single-identifier subscript back out. This mirrors
		// visitForeach_constraint_item, which has the same grammar shape.
		std::vector<ast::IExprUP> &subscript =
			target->getHier_id()->getElems().back()->getSubscript();
		if (subscript.size()) {
			ast::IExprRefPathContext *sub_c =
				dynamic_cast<ast::IExprRefPathContext *>(subscript.back().get());
			if (sub_c && sub_c->getHier_id()->getElems().size() == 1 &&
				!sub_c->getHier_id()->getElems().back()->getSubscript().size()) {
				ast::IExprId *idx = sub_c->getHier_id()->getElems().back()->getId();
				idx_id = m_factory->mkExprId(idx->getId(), idx->getIs_escaped());
				idx_id->setLocation(idx->getLocation());
				subscript.pop_back();
			}
		}
	}

	ast::IScopeChild *body = mkActivityStmt(ctx->activity_stmt_ann());
	if (!body) {
		body = m_factory->mkActivitySequence("");
	}

	// Register iterator and index variables as synthetic fields in the body scope
	// so `with` constraints inside the loop body can reference them by name.
	// Use the resolved it_id/idx_id nodes rather than the parse context: idx_id
	// may have been lifted out of a greedy subscript above, in which case
	// ctx->idx_id is null but the loop still declares an index variable.
	if (auto *body_scope = dynamic_cast<ast::ISymbolScope*>(body)) {
		if (it_id)  addSyntheticIntField(body_scope, it_id->getId());
		if (idx_id) addSyntheticIntField(body_scope, idx_id->getId());
	}

	ast::IActivityForeach *fe = m_factory->mkActivityForeach(it_id, idx_id, target, body);

	if (m_labeled_activity_id) {
		fe->setLabel(m_labeled_activity_id);
		m_labeled_activity_id = 0;
	}

	m_activity_stmt = fe;

	DEBUG_LEAVE("visitActivity_foreach_stmt");
	return 0;
}

// B.11 Data declarations

antlrcpp::Any AstBuilderInt::visitData_declaration(PSSParser::Data_declarationContext *ctx) {
	DEBUG_ENTER("visitData_declaration");

	std::vector<PSSParser::Data_instantiationContext *> items = ctx->data_instantiation();
	for (std::vector<PSSParser::Data_instantiationContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        DEBUG("Name: %s", (*it)->identifier()->getText().c_str());
		ast::IDataType *type = mkDataType(ctx->data_type());
		ast::IExpr *init = 0;

		type = applyArrayDims(type, (*it)->array_dim());

		if ((*it)->constant_expression()) {
			init = mkExpr((*it)->constant_expression()->expression());
		}

		ast::IField *field = m_factory->mkField(
			mkId((*it)->identifier()),
			type,
			FieldAttr::NoFlags,
			init);

        // Give the field a location that matches the field identifier
        // Note: we supply the token to use when looking for doc comments
		addChild(
            field, 
            (*it)->identifier()->start,
            &field->getName()->getLocation(),
            ctx->data_type()->start,
            (*it)->stop,
            ctx->stop);

		if (m_field_depth > 0) {
			m_fields.push_back(field);
		}
	}
	DEBUG_LEAVE("visitData_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAttr_field(PSSParser::Attr_fieldContext *ctx) {
	DEBUG_ENTER("visitAttr_field");
	// D2: `attr_field` contributes tokens ahead of the declaration it wraps, so the
	// comment sits to the left of *this* rule, not of the delegate.
	DocAnchorScope doc_anchor(this, ctx->start);

	m_field_depth++;
	ctx->data_declaration()->accept(this);
	m_field_depth--;

	for (std::vector<ast::IField *>::const_iterator
		it=m_fields.begin();
		it!=m_fields.end(); it++) {
		FieldAttr attr = (*it)->getAttr();

		attr |= accessModifierToFieldAttr(ctx->access_modifier());

		if (ctx->is_rand) {
			attr |= FieldAttr::Rand;
		}

		if (ctx->is_const) {
			attr |= FieldAttr::Static;
			attr |= FieldAttr::Const;
		}

		(*it)->setAttr(attr);
	}

	if (!m_field_depth) {
		m_fields.clear();
	}
	DEBUG_LEAVE("visitAttr_field");
	return 0;
}

// B.13 Data types
antlrcpp::Any AstBuilderInt::visitChandle_type(PSSParser::Chandle_typeContext *ctx) {
	DEBUG_ENTER("visitChandle_type");
	m_type = m_factory->mkDataTypeChandle();
	DEBUG_LEAVE("visitChandle_type");
	return 0;
}

/**
 * Width of `[msb : lsb]`, given the width expression already built for `msb`.
 *
 * B.13 has no range form at all -- `integer_type ::= integer_atom_type
 * [ [ constant_expression ] ] [ in [ domain_open_range_list ] ]` -- so
 * `bit[7:0]` is a PSS 1.x/2.x ingestion extension rather than conformant 3.1
 * (D7). It is treated as another way of writing `bit[8]`, with the low bound
 * required to be 0, so `bit[7:1]` is rejected. The grammar accepts an expression
 * there regardless, so that the diagnostic comes from here and names the
 * problem, rather than from ANTLR as an unexplained syntax error.
 */
ast::IExpr *AstBuilderInt::mkMsbWidth(
		ast::IExpr                  *msb,
		PSSParser::ExpressionContext *lsb_ctx) {
	ast::IExpr *lsb = mkExpr(lsb_ctx);
	ast::IExprUnsignedNumber *lsb_n =
		dynamic_cast<ast::IExprUnsignedNumber *>(lsb);

	if (!lsb_n || lsb_n->getValue() != 0) {
		ast::Location loc;
		loc.fileid = m_file_id;
		loc.lineno = (int32_t)lsb_ctx->start->getLine();
		loc.linepos = (int32_t)lsb_ctx->start->getCharPositionInLine()+1;
		loc.extent = (int32_t)lsb_ctx->getText().size();

		char tmp[1024];
		snprintf(tmp, sizeof(tmp),
			"unexpected low bound '%s' in an integer width; "
			"only '0' is permitted, as in 'bit[7:0]'",
			lsb_ctx->getText().c_str());

		Marker m(tmp, MarkerSeverityE::Error, loc);
		if (m_marker_l) { m_marker_l->marker(&m); }

		delete lsb;
		return msb;
	}

	delete lsb;

	// `bit[7:0]` and `bit[8]` are the same type, so where the bound is a
	// literal they are also the same AST -- nothing downstream should have to
	// know which spelling it came from. Where it is not (`bit[W:0]`), the
	// addition is left for the width to be evaluated with, which is what
	// happens to `bit[W]` anyway.
	ast::IExprUnsignedNumber *msb_n =
		dynamic_cast<ast::IExprUnsignedNumber *>(msb);

	if (msb_n) {
		char img[32];
		snprintf(img, sizeof(img), "%llu",
			(unsigned long long)(msb_n->getValue()+1));
		ast::IExpr *ret = m_factory->mkExprUnsignedNumber(
			img, msb_n->getWidth(), msb_n->getValue()+1);
		delete msb;
		return ret;
	}

	return m_factory->mkExprBin(
		msb,
		ast::ExprBinOp::BinOp_Add,
		m_factory->mkExprUnsignedNumber("1", 32, 1));
}

antlrcpp::Any AstBuilderInt::visitInteger_type(PSSParser::Integer_typeContext *ctx) {
	DEBUG_ENTER("visitInteger_type");

	ast::IExpr *width = 0;
	ast::IExprDomainOpenRangeList *in = 0;

	if (ctx->lhs) {
		width = mkExpr(ctx->lhs);

		if (ctx->rhs) {
			width = mkMsbWidth(width, ctx->rhs);
		}
	} else {
        if (ctx->integer_atom_type()->TOK_INT()) {
            width = m_factory->mkExprUnsignedNumber("32", 32, 32);
        } else {
            width = m_factory->mkExprUnsignedNumber("1", 32, 1);
        }
    }

	if (ctx->is_in) {
		in = mkDomainOpenRangeList(ctx->domain);
	}

	ast::IDataTypeInt *type = m_factory->mkDataTypeInt(
		ctx->integer_atom_type()->TOK_INT(),
		width,
		in
	);

	m_type = type;

	DEBUG_LEAVE("visitInteger_type");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitString_type(PSSParser::String_typeContext *ctx) {
    DEBUG_ENTER("visitString_type");
    m_type = m_factory->mkDataTypeString(ctx->has_range);
    if (ctx->has_range) {
        DEBUG("TODO: capture string-type range");
    }
    DEBUG_LEAVE("visitString_type");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitBool_type(PSSParser::Bool_typeContext *ctx) {
	DEBUG_ENTER("visitBool_type");
	m_type = m_factory->mkDataTypeBool();
	DEBUG_LEAVE("visitBool_type");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitFloat_type(PSSParser::Float_typeContext *ctx) {
	DEBUG_ENTER("visitFloat_type");
	m_type = m_factory->mkDataTypeFloat(ctx->TOK_FLOAT64() != nullptr);
	DEBUG_LEAVE("visitFloat_type");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitEnum_type(PSSParser::Enum_typeContext *ctx) {
	DEBUG_ENTER("visitEnum_type");

	ast::IDataTypeUserDefined *dt = mkDataTypeUserDefined(ctx->enum_type_identifier()->type_identifier());
	ast::IExprOpenRangeList *in = 0;

	if (ctx->TOK_IN()) {
		ctx->open_range_list()->accept(this);
		in = dynamic_cast<ast::IExprOpenRangeList*>(m_expr);
	}

	ast::IDataTypeEnum *type_enum = m_factory->mkDataTypeEnum(dt, in);

	m_type = type_enum;
	DEBUG_LEAVE("visitEnum_type");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitPyobj_type(PSSParser::Pyobj_typeContext *ctx) {
    DEBUG_ENTER("visitPyobj_type");
    // Create a user-defined data type with a direct
    // reference to ::std_pkg::pyobj

    ast::IDataTypePyObj *dt = m_factory->mkDataTypePyObj();

    m_type = dt;
    DEBUG_LEAVE("visitPyobj_type");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitEnum_declaration(PSSParser::Enum_declarationContext *ctx) {
	DEBUG_ENTER("visitEnum_declaration");

	ast::IEnumDecl *decl = m_factory->mkEnumDecl(mkId(ctx->enum_identifier()->identifier()));

	// Optional base type (21.13.1): `enum mode_e : bit[4] { ... }`. Carried on
	// the declaration so type checking and packed-struct layout can see it.
	if (ctx->base_type) {
		decl->setBase_type(mkDataType(ctx->base_type));
	}

	std::vector<PSSParser::Enum_itemContext *> items = ctx->enum_item();
	for (std::vector<PSSParser::Enum_itemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		ast::IExpr *value = 0;

		if ((*it)->constant_expression()) {
			value = mkExpr((*it)->constant_expression()->expression());
		}

		ast::IEnumItem *item = m_factory->mkEnumItem(
			mkId((*it)->identifier()),
			value);
		setLoc(item, (*it)->start);
		attachDocstring(item, (*it)->start);
		decl->getItems().push_back(ast::IEnumItemUP(item));
	}

	// Pre-compute enum item indices for compile-time evaluation.
	// Items may reference prior items (e.g. B = A + 1).
	{
		int64_t next_val = 0;
		for (auto &item : decl->getItems()) {
			if (item->getValue()) {
				// Try evaluating the expression, resolving references
				// to prior enum items within the same enum.
				int64_t computed = 0;
				if (evalEnumItemExpression(decl, item->getValue(), computed)) {
					item->setIndex(computed);
					next_val = computed + 1;
				} else {
					item->setIndex(next_val++);
				}
			} else {
				item->setIndex(next_val++);
			}
		}
	}

	addChild(decl, ctx->start);

	DEBUG_LEAVE("visitEnum_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitTypedef_declaration(PSSParser::Typedef_declarationContext *ctx) {
	DEBUG_ENTER("visitTypedef_declaration");

	ast::IDataType *type = 0;
	if (ctx->data_type()) {
		type = mkDataType(ctx->data_type());
	}

	// B.13: the declared name is an `identifier`, not a `type_identifier` --
	// `typedef int a::b;` is not legal PSS.
	ast::IExprId *name = 0;
	if (ctx->identifier()) {
		name = mkId(ctx->identifier());
	}

	if (name) {
		ast::ITypedefDeclaration *decl = m_factory->mkTypedefDeclaration(name, type);
		addChild(decl, ctx->start);
	}

	DEBUG_LEAVE("visitTypedef_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitReference_type(PSSParser::Reference_typeContext *ctx) {
	DEBUG_ENTER("visitReference_type");

	ast::IDataTypeUserDefined *type = 0;
	ctx->entity_type_identifier()->accept(this);
	type = dynamic_cast<ast::IDataTypeUserDefined *>(m_type);

	if (!type && m_type) {
		DEBUG_ERROR("visitReference_type: entity_type_identifier returned non-user-defined type");
	}

	ast::IDataTypeRef *ref = m_factory->mkDataTypeRef(type);

	m_type = ref;
	DEBUG_LEAVE("visitReference_type");
	return 0;
}


// B.14 Constraints
antlrcpp::Any AstBuilderInt::visitConstraint_declaration(PSSParser::Constraint_declarationContext *ctx) {
	DEBUG_ENTER("visitConstraint_declaration");
	std::string name;

	if (ctx->identifier()) {
		name = ctx->identifier()->getText();
	}

	ast::IConstraintBlock *constraint = m_factory->mkConstraintBlock(
		name,
		ctx->is_dynamic);

	addChild(constraint, ctx->start);
	m_constraint_s.push_back(constraint);

	if (ctx->constraint_set()) {
        DEBUG("constraint_set");
		// An anonymous `constraint { ... }` carries its body via constraint_set.
		// When that is a brace block, add its items DIRECTLY to this block (as
		// the named `constraint id { ... }` form does) rather than letting
		// visitConstraint_block wrap them in an extra ConstraintScope. The
		// wrapper desyncs ref-path resolution from symbol-tree navigation for
		// constructs that introduce symbols (e.g. nested forall iterators).
		if (ctx->constraint_set()->constraint_block()) {
			std::vector<PSSParser::Constraint_body_itemContext *> items =
				ctx->constraint_set()->constraint_block()->constraint_body_item();
			for (std::vector<PSSParser::Constraint_body_itemContext *>::const_iterator
				it=items.begin(); it!=items.end(); it++) {
				(*it)->accept(this);
			}
		} else {
			ctx->constraint_set()->accept(this);
		}
	} else {
		std::vector<PSSParser::Constraint_body_itemContext *> items = 
			ctx->constraint_block()->constraint_body_item();
        DEBUG("constraint_body: %d", items.size());
		for (std::vector<PSSParser::Constraint_body_itemContext *>::const_iterator
			it=items.begin();
			it!=items.end(); it++) {
			(*it)->accept(this);
		}
	}

	m_constraint_s.pop_back();

	DEBUG_LEAVE("visitConstraint_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitGeneric_constraint_bool(PSSParser::Generic_constraint_boolContext *ctx) {
    DEBUG_ENTER("visitGeneric_constraint_bool");

    ast::IGenericConstraintDeclBool *constraint = m_factory->mkGenericConstraintDeclBool(
        ctx->identifier()->getText(),
        false);
    constraint->setIs_static(ctx->is_static);
    setLoc(constraint, ctx->start);
    addChild(constraint, ctx->start);

    std::vector<ast::IGenericConstraintParam *> params =
        mkGenericConstraintParams(ctx->generic_constraint_params());
    for (std::vector<ast::IGenericConstraintParam *>::const_iterator
        it=params.begin();
        it!=params.end(); it++) {
        constraint->getParameters().push_back(ast::IGenericConstraintParamUP(*it));
    }

    m_constraint_s.push_back(constraint);
    ctx->constraint_set()->accept(this);
    m_constraint_s.pop_back();

    m_constraint = constraint;

    DEBUG_LEAVE("visitGeneric_constraint_bool");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitGeneric_constraint_value(PSSParser::Generic_constraint_valueContext *ctx) {
    DEBUG_ENTER("visitGeneric_constraint_value");

    ast::IGenericConstraintDeclValue *constraint = m_factory->mkGenericConstraintDeclValue();
    constraint->setIs_static(ctx->is_static);
    constraint->setName(mkId(ctx->identifier()));
    if (ctx->generic_constraint_data_type()->is_numeric) {
        constraint->setIs_return_numeric(true);
    } else {
        constraint->setReturn_type(mkDataType(ctx->generic_constraint_data_type()->data_type()));
    }
    constraint->setExpr(mkExpr(ctx->expression_constraint_item()->expression()));
    setLoc(constraint, ctx->start);
    addChild(constraint, ctx->start);

    std::vector<ast::IGenericConstraintParam *> params =
        mkGenericConstraintParams(ctx->generic_constraint_params());
    for (std::vector<ast::IGenericConstraintParam *>::const_iterator
        it=params.begin();
        it!=params.end(); it++) {
        constraint->getParameters().push_back(ast::IGenericConstraintParamUP(*it));
    }

    DEBUG_LEAVE("visitGeneric_constraint_value");
    return 0;
}

// antlrcpp::Any AstBuilderInt::visitConstraint_set(PSSParser::Constraint_setContext *ctx) {
// 	DEBUG_ENTER("visitConstraint_set");

// 	if (ctx->constraint_body_item()) {
// 		ctx->constraint_body_item()->accept(this);
// 	} else {
// 		ctx->constraint_block()->accept(this);
// 	}

// 	DEBUG_LEAVE("visitConstraint_set");
// 	return 0;
// }

antlrcpp::Any AstBuilderInt::visitConstraint_block(PSSParser::Constraint_blockContext *ctx) {
	DEBUG_ENTER("visitConstraint_block (%d)", m_constraint_s.size());

	ast::IConstraintScope *scope = m_factory->mkConstraintScope();
//	scope->setParent(m_constraint_s.back());
	m_constraint_s.push_back(scope);
	std::vector<PSSParser::Constraint_body_itemContext *> items = ctx->constraint_body_item();
    DEBUG("items: %d", items.size());
	for (std::vector<PSSParser::Constraint_body_itemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		(*it)->accept(this);
	}
	m_constraint_s.pop_back();

    DEBUG("scope: %d", scope->getConstraints().size());

	m_constraint = scope;
	if (m_constraint_s.size() > 0) {
        DEBUG("Add constraint to exiting parent");
        scope->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(scope));
	}
	attachPendingAnnotations(scope);

	DEBUG_LEAVE("visitConstraint_block (%d)", m_constraint_s.size());
	return 0;
}

antlrcpp::Any AstBuilderInt::visitConstraint_body_compile_if(PSSParser::Constraint_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(
        ctx->constraint_body_compile_if_item(0),
        ctx->constraint_body_compile_if_item().size() > 1 ? ctx->constraint_body_compile_if_item(1) : nullptr);
    if (!evalCompileTimeCond(ctx->constant_expression(), cond, "compile if")) {
        // Reported as an error: elaborate neither branch.
    } else if (cond) {
        visitCompileIfItem(ctx->constraint_body_compile_if_item(0));
    } else if (ctx->constraint_body_compile_if_item().size() > 1) {
        visitCompileIfItem(ctx->constraint_body_compile_if_item(1));
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitDefault_constraint(PSSParser::Default_constraintContext *ctx) {
	DEBUG_ENTER("visitDefault_constraint");
	DEBUG("TODO");
	DEBUG_LEAVE("visitDefault_constraint");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitDefault_disable_constraint(PSSParser::Default_disable_constraintContext *ctx) {
	DEBUG_ENTER("visitDefault_disable_constraint");
	DEBUG("TODO");
	DEBUG_LEAVE("visitDefault_disable_constraint");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitExpression_constraint_item(PSSParser::Expression_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitExpression_constraint_item");
	ast::IConstraintStmtExpr *c = m_factory->mkConstraintStmtExpr(
		mkExpr(ctx->expression()));
	m_constraint = c;
	if (m_constraint_s.size() > 0) {
        c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);
	DEBUG_LEAVE("visitExpression_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_compile_if(PSSParser::Procedural_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(
        ctx->procedural_compile_if_stmt(0),
        ctx->procedural_compile_if_stmt().size() > 1 ? ctx->procedural_compile_if_stmt(1) : nullptr);
    PSSParser::Procedural_compile_if_stmtContext *selected = 0;

    if (!evalCompileTimeCond(ctx->constant_expression(), cond, "compile if")) {
        // Reported as an error: elaborate neither branch.
    } else if (cond) {
        selected = ctx->procedural_compile_if_stmt(0);
    } else if (ctx->procedural_compile_if_stmt().size() > 1) {
        selected = ctx->procedural_compile_if_stmt(1);
    }

    // Unlike every other compile-if scope, this one cannot elaborate its
    // branch by simply accepting the children.  A procedural statement is
    // built into `m_exec_stmt` and appended by the *caller*, one statement per
    // `procedural_stmt`; a compile if contributes zero or more.  Accepting the
    // children directly built the statements and then dropped them on the
    // floor -- the enclosing block only ever appends the single m_exec_stmt.
    // So append them here, as procedural_data_declaration does, and report
    // "one statement handled, nothing to append" to the caller.
    if (selected) {
        std::vector<PSSParser::Procedural_stmtContext *> stmts = selected->procedural_stmt();
        for (std::vector<PSSParser::Procedural_stmtContext *>::const_iterator
            it=stmts.begin();
            it!=stmts.end(); it++) {
            addExecStmt(*it);
        }
    }

    // NOTE: a compile if used as the *unbraced* body of an if/foreach --
    // `if (c) compile if (F) { ... }` -- appends into the enclosing block
    // rather than the branch.  The LRM spells this scope as a braced block, so
    // that shape is pathological; it is called out here rather than guarded.
    m_exec_stmt = 0;
    m_exec_stmt_cnt++;

    return 0;
}

antlrcpp::Any AstBuilderInt::visitCovergroup_body_compile_if(PSSParser::Covergroup_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(
        ctx->covergroup_body_compile_if_item(0),
        ctx->covergroup_body_compile_if_item().size() > 1 ? ctx->covergroup_body_compile_if_item(1) : nullptr);
    if (!evalCompileTimeCond(ctx->constant_expression(), cond, "compile if")) {
        // Reported as an error: elaborate neither branch.
    } else if (cond) {
        visitCompileIfItem(ctx->covergroup_body_compile_if_item(0));
    } else if (ctx->covergroup_body_compile_if_item().size() > 1) {
        visitCompileIfItem(ctx->covergroup_body_compile_if_item(1));
    }
    return 0;
}

// B.10/B.15 make `annotation` an alternative of override_stmt and
// covergroup_body_item, so the grammar must accept it. Neither construct is
// represented in the AST yet -- there is no visitType_override /
// visitInstance_override, and covergroup body items are only walked (partially)
// by visitInline_covergroup -- so an annotation here has no model element to
// attach to for reasons that have nothing to do with the source. Drop it rather
// than letting it reach pop_scope and be reported as dangling (PSS100), which
// would reject conforming 3.1 code. Remove these two overrides once the
// constructs themselves are built.
antlrcpp::Any AstBuilderInt::visitOverride_stmt(PSSParser::Override_stmtContext *ctx) {
    size_t mark = m_pending_annotations.size();
    visitChildren(ctx);
    discardPendingAnnotations(mark);
    return 0;
}

antlrcpp::Any AstBuilderInt::visitCovergroup_body_item(PSSParser::Covergroup_body_itemContext *ctx) {
    size_t mark = m_pending_annotations.size();
    visitChildren(ctx);
    discardPendingAnnotations(mark);
    return 0;
}

antlrcpp::Any AstBuilderInt::visitOverride_compile_if(PSSParser::Override_compile_ifContext *ctx) {
    int64_t cond = 0;
    checkCompileIfBranches(
        ctx->override_compile_if_stmt(0),
        ctx->override_compile_if_stmt().size() > 1 ? ctx->override_compile_if_stmt(1) : nullptr);
    if (!evalCompileTimeCond(ctx->constant_expression(), cond, "compile if")) {
        // Reported as an error: elaborate neither branch.
    } else if (cond) {
        visitCompileIfItem(ctx->override_compile_if_stmt(0));
    } else if (ctx->override_compile_if_stmt().size() > 1) {
        visitCompileIfItem(ctx->override_compile_if_stmt(1));
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitForeach_constraint_item(PSSParser::Foreach_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitForeach_constraint_item");
    ast::IExpr *expr = mkExpr(ctx->expression());
	ast::IConstraintStmtForeach *c = m_factory->mkConstraintStmtForeach(expr);
    ast::IConstraintSymbolScope *symtab = m_factory->mkConstraintSymbolScope("<foreach>");
    ast::IExprRefPathContext *expr_c = dynamic_cast<ast::IExprRefPathContext *>(expr);

    c->setSymtab(symtab);
    symtab->setConstraint(c);
	
	if (ctx->idx_id) {
		ast::IConstraintStmtField *it = m_factory->mkConstraintStmtField(
			mkId(ctx->idx_id->identifier()),
			0 // TODO: what do we do about datatype here?
		);
		c->setIdx(it);
        symtab->getSymtab().insert({
            it->getName()->getId(),
            symtab->getChildren().size()});
        DEBUG("Set index of iteration variable: %d", symtab->getChildren().size());
        it->setIndex(symtab->getChildren().size());
        symtab->getChildren().push_back(ast::IScopeChildUP(it, false));
	} else if (expr_c) {
        // Expressions are greedy, which means the index variable will end up
        // being interpreted as an array subscript much of the time.
        // Fix this up here...
        if (expr_c->getHier_id()->getElems().back()->getSubscript().size()) {
            std::vector<ast::IExprUP> &subscript = expr_c->getHier_id()->getElems().back()->getSubscript();
            ast::IExprRefPathContext *idx_id = dynamic_cast<ast::IExprRefPathContext *>(subscript.back().get());
            if (idx_id && idx_id->getHier_id()->getElems().size() == 1) {
                ast::IExprId *idx = idx_id->getHier_id()->getElems().back()->getId();
                ast::IExprId *idx_i = m_factory->mkExprId(
                    idx->getId(),
                    idx->getIs_escaped());
                idx_i->setLocation(idx->getLocation());
		        ast::IConstraintStmtField *it = m_factory->mkConstraintStmtField(idx_i, 0);
        		c->setIdx(it);
                symtab->getSymtab().insert({
                    it->getName()->getId(),
                    symtab->getChildren().size()});
                DEBUG("Set index of iteration variable: %d", symtab->getChildren().size());
                it->setIndex(symtab->getChildren().size());
                symtab->getChildren().push_back(ast::IScopeChildUP(it, false));

                DEBUG("Have a subscript %p", idx);
                subscript.pop_back();
            }
        }
        // No `else` pushing a placeholder child. One used to stand here --
        // `getChildren().push_back(ast::IScopeChildUP(0))`, "a bit odd, but put
        // a placeholder in anyway" -- and it put a **null** into a symbol
        // scope's child list, which segfaulted the linker (P7-X3).
        //
        // This branch is the `foreach (i : a)` form: `a` is the expression and
        // carries no subscript, so no index field is built here and `setIdx()`
        // is never called. Nothing ever referred to slot 0; it existed only to
        // keep the numbering aligned with a `setIdx()` that does not happen.
        // The iterator pushed just below takes its index from
        // `getChildren().size()` and inserts the same value into the symtab, so
        // the two stay consistent whether or not a slot precedes it.
        //
        // The crash needed the identifier to *miss* the foreach symtab, because
        // only then does resolution fall through to the enum search that walks
        // every child. `foreach (i : a) { i == 1; }` found `i` in the symtab and
        // never walked, which is why the form looked healthy; `a[0]`, `b[i]`
        // and any undeclared name all walked, and all died.
    }

	if (ctx->it_id) {
		ast::IConstraintStmtField *idx = m_factory->mkConstraintStmtField(
			mkId(ctx->it_id->identifier()),
			0 // TODO: 
		);
	  	c->setIt(idx);
        DEBUG("Set index of iteration variable (2): %d", symtab->getChildren().size());
        idx->setIndex(symtab->getChildren().size());
        symtab->getSymtab().insert({
            idx->getName()->getId(),
            symtab->getChildren().size()});
        symtab->getChildren().push_back(ast::IScopeChildUP(idx, false));
	}

	m_constraint_s.push_back(c);
	visitConstraintSetItems(ctx->constraint_set());
	m_constraint_s.pop_back();

	m_constraint = c;
	if (m_constraint_s.size() > 0) {
        c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);
	DEBUG_LEAVE("visitForeach_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitForall_constraint_item(PSSParser::Forall_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitForall_constraint_item");

	ast::IExprId *iterator_id = mkId(ctx->identifier());
	ast::IDataTypeUserDefined *type_id = mkDataTypeUserDefined(ctx->type_identifier());
	ast::IExprRefPath *ref_path = ctx->ref_path() ? mkExprRefPath(ctx->ref_path()) : 0;

	ast::IConstraintStmtForall *c = m_factory->mkConstraintStmtForall(
		iterator_id, type_id, ref_path);
	ast::IConstraintSymbolScope *symtab = m_factory->mkConstraintSymbolScope("<forall>");
	c->setSymtab(symtab);
	symtab->setConstraint(c);

	// Register the quantified iterator variable so the body can reference it
	// (incl. member access like `it.field`). The iterator carries its own
	// DataTypeUserDefined (a fresh node built from the same type_identifier) so
	// field-ref resolution can map it to the type's scope.
	//
	// The iterator is placed as the FIRST entry of the forall's constraint list
	// (index 0) and the symtab maps its name to that index. This is required for
	// ref-path resolution: a constraint scope is navigated via getConstraints()
	// (ScopeUtil), so the iterator must live there to be addressable as
	// forall.getChild(0); the real body constraints follow at index 1+. The
	// symtab.getChildren() also references it (non-owning) so the resolver's
	// scope walk can read the declaration when looking the name up.
	ast::IConstraintStmtField *it = m_factory->mkConstraintStmtField(
		m_factory->mkExprId(iterator_id->getId(), iterator_id->getIs_escaped()),
		mkDataTypeUserDefined(ctx->type_identifier())
	);
	it->setIndex(0);
	symtab->getSymtab().insert({it->getName()->getId(), 0});
	symtab->getChildren().push_back(ast::IScopeChildUP(it, false)); // non-owning ref
	c->getConstraints().push_back(ast::IConstraintStmtUP(it, true)); // owner, index 0

	m_constraint_s.push_back(c);
	visitConstraintSetItems(ctx->constraint_set());
	m_constraint_s.pop_back();

	m_constraint = c;
	if (m_constraint_s.size() > 0) {
		c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitForall_constraint_item");
	return 0;

}

antlrcpp::Any AstBuilderInt::visitIf_constraint_item(PSSParser::If_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitIf_constraint_item");
	ast::IExpr *cond = mkExpr(ctx->expression());
	ast::IConstraintScope *true_c = m_factory->mkConstraintScope();
	ast::IConstraintScope *false_c = 0;

	m_constraint_s.push_back(true_c);
	visitConstraintSetItems(ctx->constraint_set(0));
	m_constraint_s.pop_back();

	if (ctx->constraint_set(1)) {
		false_c = m_factory->mkConstraintScope();
		m_constraint_s.push_back(false_c);
		visitConstraintSetItems(ctx->constraint_set(1));
		m_constraint_s.pop_back();
	}

	IConstraintStmtIf *c = m_factory->mkConstraintStmtIf(
		cond,
		true_c,
		false_c);

	m_constraint = c;
	if (m_constraint_s.size() > 0) {
        c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(
			IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitIf_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitImplication_constraint_item(PSSParser::Implication_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitImplication_constraint_item");
	ast::IConstraintStmtImplication *c = m_factory->mkConstraintStmtImplication(mkExpr(ctx->expression()));

	m_constraint_s.push_back(c);
	visitConstraintSetItems(ctx->constraint_set());
	m_constraint_s.pop_back();

	m_constraint = c;
	if (m_constraint_s.size()) {
        c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitImplication_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitUnique_constraint_item");
	ast::IConstraintStmtUnique *c = m_factory->mkConstraintStmtUnique();
	setLoc(c, ctx->start);

	PSSParser::Unique_constraint_argumentContext *arg = ctx->unique_constraint_argument();

	if (arg->hierarchical_id_list()) {
		c->setIs_braced(true);

		std::vector<PSSParser::Hierarchical_idContext *> items =
			arg->hierarchical_id_list()->hierarchical_id();

		for (std::vector<PSSParser::Hierarchical_idContext *>::const_iterator
			it=items.begin();
			it!=items.end(); it++) {
			ast::IExprHierarchicalId *hid = mkHierarchicalId(*it);
			c->getList().push_back(ast::IExprHierarchicalIdUP(hid));
		}
	} else {
		// Single-argument form (3.1). A slice, if written, is already part of
		// the hierarchical_id -- see the grammar comment on
		// unique_constraint_argument.
		c->setIs_braced(false);
		c->getList().push_back(ast::IExprHierarchicalIdUP(
			mkHierarchicalId(arg->hierarchical_id())));
	}

	if (m_constraint_s.size() > 0) {
		c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitUnique_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitSoft_constraint_item(PSSParser::Soft_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitSoft_constraint_item");
	ast::IConstraintStmtSoft *c = m_factory->mkConstraintStmtSoft(
		mkExpr(ctx->expression()));
	setLoc(c, ctx->start);

	// `index` is what a downstream solver derives soft-constraint priority
	// from (13.1.12), so it must reflect source order exactly.
	if (m_constraint_s.size() > 0) {
		c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitSoft_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitDist_directive(PSSParser::Dist_directiveContext *ctx) {
	DEBUG_ENTER("visitDist_directive");
	ast::IExpr *lhs = mkExpr(ctx->expression());
	ast::IConstraintStmtDist *c = m_factory->mkConstraintStmtDist(lhs);

	for (auto *item : ctx->dist_list()->dist_item()) {
		PSSParser::Open_range_valueContext *rv = item->open_range_value();
		ast::IExpr *rlhs = rv->lhs ? mkExpr(rv->lhs) : nullptr;
		ast::IExpr *rrhs = rv->rhs ? mkExpr(rv->rhs) : nullptr;
		ast::IExprOpenRangeValue *range =
			m_factory->mkExprOpenRangeValue(rlhs, rrhs);

		// The weight is optional; absent means the default weight of 1.
		ast::IDistWeight *weight = nullptr;
		if (item->dist_weight()) {
			PSSParser::Dist_weightContext *w = item->dist_weight();
			weight = m_factory->mkDistWeight(
				w->TOK_COLON_DIV() != nullptr,
				mkExpr(w->expression()));
		}

		c->getItems().push_back(
			ast::IDistItemUP(m_factory->mkDistItem(range, weight)));
	}

	if (m_constraint_s.size() > 0) {
		c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}
	attachPendingAnnotations(c);

	DEBUG_LEAVE("visitDist_directive");
	return 0;
}

void AstBuilderInt::visitConstraintSetItems(PSSParser::Constraint_setContext *ctx) {
	DEBUG_ENTER("visitConstraintSetItems");

	if (ctx->constraint_body_item()) {
		ctx->constraint_body_item()->accept(this);
	} else {
		std::vector<PSSParser::Constraint_body_itemContext *> items =
			ctx->constraint_block()->constraint_body_item();
		for (std::vector<PSSParser::Constraint_body_itemContext *>::const_iterator
			it=items.begin();
			it!=items.end(); it++) {
			(*it)->accept(this);
		}
	}

	DEBUG_LEAVE("visitConstraintSetItems");
}

// B.17 Expressions

static std::map<std::string, ast::ExprUnaryOp> prv_str2unop = {
	{"+", ast::ExprUnaryOp::UnaryOp_Plus},
	{"-", ast::ExprUnaryOp::UnaryOp_Minus},
	{"!", ast::ExprUnaryOp::UnaryOp_LogNot},
	{"~", ast::ExprUnaryOp::UnaryOp_BitNeg},
	{"&", ast::ExprUnaryOp::UnaryOp_BitAnd},
	{"|", ast::ExprUnaryOp::UnaryOp_BitOr},
	{"^", ast::ExprUnaryOp::UnaryOp_BitXor}
};

static std::map<std::string, ast::ExprBinOp> prv_str2binop = {
	{"||", ast::ExprBinOp::BinOp_LogOr},
	{"&&", ast::ExprBinOp::BinOp_LogAnd},
	{"|", ast::ExprBinOp::BinOp_BitOr},
	{"^", ast::ExprBinOp::BinOp_BitXor},
	{"&", ast::ExprBinOp::BinOp_BitAnd},
	{"<", ast::ExprBinOp::BinOp_Lt},
	{"<=", ast::ExprBinOp::BinOp_Le},
	{">", ast::ExprBinOp::BinOp_Gt},
	{">=", ast::ExprBinOp::BinOp_Ge},
	{"**", ast::ExprBinOp::BinOp_Exp},
	{"*", ast::ExprBinOp::BinOp_Mul},
	{"/", ast::ExprBinOp::BinOp_Div},
	{"%", ast::ExprBinOp::BinOp_Mod},
	{"+", ast::ExprBinOp::BinOp_Add},
	{"-", ast::ExprBinOp::BinOp_Sub},
	{"<<", ast::ExprBinOp::BinOp_Shl},
	{">>", ast::ExprBinOp::BinOp_Shr},
	{"==", ast::ExprBinOp::BinOp_Eq},
	{"!=", ast::ExprBinOp::BinOp_Ne}
};

antlrcpp::Any AstBuilderInt::visitExpression(PSSParser::ExpressionContext *ctx) {
	DEBUG_ENTER("visitExpression");

	if (ctx->unary_op()) {
		ast::IExpr *lhs = mkExpr(ctx->lhs);

		m_expr = m_factory->mkExprUnary(
			prv_str2unop.find(ctx->unary_op()->getText())->second,
			lhs);
	} else if (ctx->lhs && ctx->rhs) {
		// It's some form of binary op
		ast::IExpr *lhs = mkExpr(ctx->lhs);

		ast::IExpr *rhs = mkExpr(ctx->rhs);

		ast::ExprBinOp op = ast::ExprBinOp::BinOp_LogOr;
		if (ctx->exp_op()) {
			op = ast::ExprBinOp::BinOp_Exp;
		} else if (ctx->mul_div_mod_op()) {
			op = prv_str2binop.find(ctx->mul_div_mod_op()->getText())->second;
		} else if (ctx->add_sub_op()) {
			op = prv_str2binop.find(ctx->add_sub_op()->getText())->second;
		} else if (ctx->shift_op()) {
			op = prv_str2binop.find(ctx->shift_op()->getText())->second;
		} else if (ctx->logical_inequality_op()) {
			op = prv_str2binop.find(ctx->logical_inequality_op()->getText())->second;
		} else if (ctx->eq_neq_op()) {
			op = prv_str2binop.find(ctx->eq_neq_op()->getText())->second;
		} else if (ctx->binary_and_op()) {
			op = ExprBinOp::BinOp_BitAnd;
		} else if (ctx->binary_xor_op()) {
			op = ExprBinOp::BinOp_BitXor;
		} else if (ctx->binary_or_op()) {
			op = ExprBinOp::BinOp_BitOr;
		} else if (ctx->logical_and_op()) {
			op = ExprBinOp::BinOp_LogAnd;
		} else if (ctx->logical_or_op()) {
			op = ExprBinOp::BinOp_LogOr;
		}

		m_expr = m_factory->mkExprBin(
			lhs,
			op,
			rhs);
	} else if (ctx->lhs) {
		// It's either an 'in' or a conditional 
		if (ctx->in_expression()) {
			// Build ExprIn: lhs in [open_range_list | collection_expression]
			ast::IExpr *lhs = mkExpr(ctx->lhs);
			PSSParser::In_expressionContext *in_ctx = ctx->in_expression();
			ast::IExprOpenRangeList *rhs = mkOpenRangeList(in_ctx->open_range_list());
			// Collection-expression form: x in comp.some_list
			ast::IExpr *coll = nullptr;
			if (in_ctx->collection_expression()) {
				coll = mkExpr(in_ctx->collection_expression()->expression());
			}
			m_expr = m_factory->mkExprIn(lhs, rhs, coll);
		} else {
			// Conditional
			ast::IExpr *cond = mkExpr(ctx->lhs);

			ast::IExpr *true_e = mkExpr(ctx->conditional_expr()->true_expr);

			ast::IExpr *false_e = mkExpr(ctx->conditional_expr()->false_expr);

			m_expr = m_factory->mkExprCond(
				cond,
				true_e,
				false_e);
		}
	} else {
		// It's a primary
		ctx->primary()->accept(this);
	}

	DEBUG_LEAVE("visitExpression");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitBool_literal(PSSParser::Bool_literalContext *ctx) {
	DEBUG_ENTER("visitBool_literal");
	m_expr = m_factory->mkExprBool(ctx->TOK_TRUE());
	DEBUG_LEAVE("visitBool_literal");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitString_literal(PSSParser::String_literalContext *ctx) {
	DEBUG_ENTER("visitString_literal");
	if (ctx->DOUBLE_QUOTED_STRING()) {
		std::string value = ctx->DOUBLE_QUOTED_STRING()->getText();
		value = value.substr(1, value.size()-2);
		m_expr = m_factory->mkExprString(value, false);
	} else { 
		std::string value = ctx->TRIPLE_DOUBLE_QUOTED_STRING()->getText();
		value = value.substr(3, value.size()-6);
		// §4.7.1: only a triple-quoted string is a template context, and only one
		// that actually holds special elements becomes an ExprTemplateString. The
		// subclass keeps every existing ExprString consumer working unchanged.
		ast::ITemplateString *tmpl = mkTemplateString(ctx);
		if (tmpl) {
			ast::IExprTemplateString *e = m_factory->mkExprTemplateString(value, true);
			e->setTemplate(tmpl);
			m_expr = e;
		} else {
			m_expr = m_factory->mkExprString(value, true);
		}
	}
	DEBUG_LEAVE("visitString_literal");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitNull_ref(PSSParser::Null_refContext *ctx) {
	DEBUG_ENTER("visitNull_ref");
	m_expr = m_factory->mkExprNull();
	DEBUG_LEAVE("visitNull_ref");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitRef_path(PSSParser::Ref_pathContext *ctx) {
	DEBUG_ENTER("visitRef_path");

    m_expr = mkExprRefPath(ctx);

	DEBUG_LEAVE("visitRef_path");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitCompile_has_expr(PSSParser::Compile_has_exprContext *ctx) {
    m_expr = m_factory->mkExprCompileHas(0);
    return 0;
}

antlrcpp::Any AstBuilderInt::visitCast_expression(PSSParser::Cast_expressionContext *ctx) {
	DEBUG_ENTER("visitCast_expression");
	ast::IExpr *expr = mkExpr(ctx->expression());

	ctx->casting_type()->accept(this);
	ast::IDataType *type = m_type;

	m_expr = m_factory->mkExprCast(type, expr);

	DEBUG_LEAVE("visitCast_expression");
	return 0;
}

// B.18 Identifiers

/**
 * Strip the leading backslash from an escaped identifier's token text.
 *
 * LRM 4.3: "Neither the leading backslash character nor the terminating white
 * space is considered to be part of the identifier.  Therefore, an escaped
 * identifier \cpu3 is treated the same as a non-escaped identifier cpu3."
 *
 * So the backslash is spelling, not name.  Keeping it made `\cpu3` and `cpu3`
 * two distinct names, which resolves only as long as every declaration and
 * every reference happen to be spelled the same way -- correct by consistency
 * rather than by rule, and silently wrong the moment they differ.
 *
 * The terminating whitespace never reaches here: the lexer rule stops before
 * it, so the token text has nothing to trim on the right.
 */
static std::string unescapeId(const std::string &text) {
	return (text.size() && text[0] == '\\') ? text.substr(1) : text;
}

antlrcpp::Any AstBuilderInt::visitIdentifier(PSSParser::IdentifierContext *ctx) {
	DEBUG_ENTER("visitIdentifier");
	IExprId *id;

	if (ctx->ESCAPED_ID()) {
		id = m_factory->mkExprId(
			unescapeId(ctx->ESCAPED_ID()->getText()), true);
	} else {
        DEBUG("visitIdentifier: %s", ctx->ID()->getText().c_str());
		id = m_factory->mkExprId(ctx->ID()->getText(), false);
	}

	Location loc;
	loc.lineno = ctx->start->getLine();
	loc.linepos = ctx->start->getCharPositionInLine()+1;
    // The extent spans the source text, which for an escaped identifier is one
    // character longer than the name now that the backslash has been stripped.
    loc.extent = id->getId().size() + (id->getIs_escaped()?1:0);
	id->setLocation(loc);
    DEBUG("Set Location: %d:%d:%d",
        id->getLocation().fileid,
        id->getLocation().lineno,
        id->getLocation().linepos);

	m_expr = id;

	DEBUG_LEAVE("visitIdentifier");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitType_identifier(PSSParser::Type_identifierContext *ctx) {
    DEBUG_ENTER("visitType_identifier");
    m_type = mkDataTypeUserDefined(ctx);
    DEBUG_LEAVE("visitType_identifier");
    return 0;
}

// B.19 Numbers

/**
 * A copy of `s` with the `_` digit separators removed.
 *
 * B.19 allows the separator anywhere after the first digit, in every base and
 * in the size prefix as well. None of the conversion routines understand it, so
 * it is stripped for them -- never from the image, which is the source
 * spelling.
 */
static std::string stripSeparators(const std::string &s, uint32_t off=0) {
	std::string ret;
	for (uint32_t i=off; i<s.size(); i++) {
		if (s.at(i) != '_') {
			ret.push_back(s.at(i));
		}
	}
	return ret;
}

/**
 * Read an integer literal -- every form B.19 spells -- from its source text.
 *
 * Text rather than tokens, because there are two callers and only one of them
 * has tokens to offer: `evalExpression` walks the parse tree. Nothing is lost
 * by meeting there. A number's `getText()` is its tokens concatenated, and the
 * only thing that can sit between them is whitespace (`16 'hFF`), which is not
 * part of any token either.
 *
 * There were two readers before this, and the second one silently disagreed
 * with the first: it read `8'hFF` as 8 and `0b1010` as 0, so a `compile if`
 * written with either quietly took the wrong branch (P1-G1c). The way to not
 * have that happen again is to have one reader.
 *
 * Returns false only for text no lexer rule can produce.
 */
static bool parseIntegerLiteral(
		const std::string   &text,
		int32_t             &width,
		uint64_t            &value,
		bool                &is_signed) {
	width = 32;
	value = 0;
	is_signed = false;

	std::string::size_type q = text.find('\'');

	if (q != std::string::npos) {
		// `[ size ] ' [s] base digits`. The size is a separate token (B.19
		// spells the halves separately, and `8` alone is an ordinary
		// DEC_LITERAL); absent, the literal keeps the default width.
		if (q > 0) {
			width = (int32_t)strtoul(
				stripSeparators(text.substr(0, q)).c_str(), 0, 10);
		}

		uint32_t i = (uint32_t)q+1;

		if (i < text.size() && (text[i] == 's' || text[i] == 'S')) {
			is_signed = true;
			i++;
		}

		if (i >= text.size()) {
			return false;
		}

		int32_t radix;
		switch (text[i]) {
			case 'h': case 'H': radix = 16; break;
			case 'd': case 'D': radix = 10; break;
			case 'o': case 'O': radix = 8; break;
			case 'b': case 'B': radix = 2; break;
			default: return false;
		}

		value = strtoull(stripSeparators(text, i+1).c_str(), 0, radix);
		return true;
	}

	// Unbased. The prefix picks the base, and a lone leading `0` is octal --
	// so the `0` of `0b1010` has to be tested for `b` before it is taken as
	// one, which is the half of this the second reader got wrong.
	uint32_t off = 0;
	int32_t radix = 10;

	if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
		radix = 16;
		off = 2;
	} else if (text.size() > 2 && text[0] == '0' && (text[1] == 'b' || text[1] == 'B')) {
		radix = 2;
		off = 2;
	} else if (text.size() > 1 && text[0] == '0') {
		radix = 8;
		off = 1;
	}

	value = strtoull(stripSeparators(text, off).c_str(), 0, radix);
	return true;
}

antlrcpp::Any AstBuilderInt::visitNumber(PSSParser::NumberContext *ctx_t) {
	DEBUG_ENTER("visitNumber %s", ctx_t->getText().c_str());
    if (ctx_t->integer_number()) {
        // The image is the source spelling, and the source spelling is the
        // tokens: which of the eight `integer_number` alternatives matched is
        // exactly what `parseIntegerLiteral` recovers from the text, so there
        // is nothing to gain by asking here as well.
        std::string img = ctx_t->integer_number()->getText();
        uint64_t value;
        bool is_signed;
        int32_t width;

        if (!parseIntegerLiteral(img, width, value, is_signed)) {
            DEBUG_FATAL("Unknown format");
        }

        if (is_signed) {
    	    m_expr = m_factory->mkExprSignedNumber(img, width, value);
        } else {
    	    m_expr = m_factory->mkExprUnsignedNumber(img, width, value);
        }

    } else { // floating-point number
        PSSParser::Floating_point_numberContext *ctx = ctx_t->floating_point_number();
        std::string img = ctx->getText();

        // strtod does not understand PSS digit separators, so strip them for
        // the conversion while keeping the original spelling in the image.
        std::string val_t;
        for (std::string::const_iterator it=img.begin(); it!=img.end(); it++) {
            if (*it != '_') {
                val_t += *it;
            }
        }

        m_expr = m_factory->mkExprFloatLiteral(
            strtod(val_t.c_str(), 0),
            img,
            ctx->floating_point_sci_number() != nullptr);
    }

	DEBUG_LEAVE("visitNumber");

	return 0;
}

antlrcpp::Any AstBuilderInt::visitAggregate_literal(PSSParser::Aggregate_literalContext *ctx) {
    DEBUG_ENTER("visitAggregate_literal");
    PSSParserBaseVisitor::visitAggregate_literal(ctx);
    DEBUG_LEAVE("visitAggregate_literal");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitEmpty_aggregate_literal(PSSParser::Empty_aggregate_literalContext *ctx) {
    DEBUG_ENTER("visitEmpty_aggregate_literal");
    ast::IExprAggrEmpty *lval = m_factory->mkExprAggrEmpty();
    m_expr = lval;
    DEBUG_LEAVE("visitEmpty_aggregate_literal");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitValue_list_literal(PSSParser::Value_list_literalContext *ctx) {
    DEBUG_ENTER("visitValue_list_literal");
    ast::IExprAggrList *lval = m_factory->mkExprAggrList();

    std::vector<PSSParser::ExpressionContext *> items = ctx->expression();
    for (std::vector<PSSParser::ExpressionContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        lval->getElems().push_back(ast::IExprUP(mkExpr(*it)));
    }

    m_expr = lval;
    DEBUG_LEAVE("visitValue_list_literal");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitMap_literal(PSSParser::Map_literalContext *ctx) {
    DEBUG_ENTER("visitMap_literal");
    ast::IExprAggrMap *lval = m_factory->mkExprAggrMap();

    std::vector<PSSParser::Map_literal_itemContext *> items = ctx->map_literal_item();
    for (std::vector<PSSParser::Map_literal_itemContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ast::IExpr *key = mkExpr((*it)->expression(0));
        ast::IExpr *val = mkExpr((*it)->expression(1));
        lval->getElems().push_back(ast::IExprAggrMapElemUP(
            m_factory->mkExprAggrMapElem(key, val)));
    }
    m_expr = lval;
    DEBUG_LEAVE("visitMap_literal");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitStruct_literal(PSSParser::Struct_literalContext *ctx) {
    DEBUG_ENTER("visitStruct_literal");
    ast::IExprAggrStruct *lval = m_factory->mkExprAggrStruct();

    std::vector<PSSParser::Struct_literal_itemContext *> items = ctx->struct_literal_item();
    for (std::vector<PSSParser::Struct_literal_itemContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ast::IExprId *id = mkId((*it)->identifier());
        ast::IExpr *val = mkExpr((*it)->expression());
        lval->getElems().push_back(ast::IExprAggrStructElemUP(
            m_factory->mkExprAggrStructElem(id, val)));
    }

    m_expr = lval;
    DEBUG_LEAVE("visitStruct_literal");
    return 0;
}

struct RewrittenSyntaxError {
    std::string msg;
    // PSS020-PSS028 sub-band ID, or empty for the PSS001 fallback (an
    // ANTLR message shape this classifier does not (yet) recognize).
    std::string id;
};

// D1: ANTLR reports a follow-set containing the bare token name ID (or its
// ESCAPED_ID sibling, `\`escaped\``) whenever an identifier is legal at this
// position -- regardless of what else is *also* legal there (a leading '::'
// for a qualified name, 'super' at a super-reference, a trailing '*' or '{'
// at an import spec, ...). Originally three exact strings, one added by hand
// each time a new grammar position turned up one; generalized to "does ID
// appear as a standalone element of the set" after E-7's mutation sweep hit
// a fourth position (import specs) the same day a third (super_ref) was
// added -- enumerating every position by hand does not scale, and the
// simplified "expected identifier" message is correct for all of them: an
// identifier is always among the legal continuations when ID is in the set.
//
// Capped at MAX_ELEMENTS: a *name* position's follow set is a short,
// specific list (qualifiers, ID, ESCAPED_ID -- 5 elements at most seen so
// far). An *expression* position's follow set also contains ID (any
// expression can start with an identifier) but alongside a dozen-plus other
// alternatives (literals, unary operators, '('...) -- e.g. after a bare
// `return` or a trailing comma in a call's argument list. Collapsing that
// large a set to "expected identifier" would be actively wrong (the L1
// corpus's punct/missing_semicolon_return.pss and
// punct/extra_trailing_comma_call.pss cases pin the correct PSS024 fallback
// for exactly this shape), so those fall through to the length-gated
// generic handling instead.
static bool setBodyHasBareIdentifierElement(const std::string &body) {
    static const size_t MAX_ELEMENTS = 5;
    bool foundId = false;
    size_t elementCount = 0;
    size_t pos = 0;
    while (pos <= body.size()) {
        size_t comma = body.find(", ", pos);
        std::string elem = (comma == std::string::npos)
            ? body.substr(pos) : body.substr(pos, comma - pos);
        elementCount++;
        // Exact match -- avoids false positives from a quoted literal
        // containing "ID" or from ESCAPED_ID as a *substring* of some other
        // token name.
        if (elem == "ID" || elem == "ESCAPED_ID") {
            foundId = true;
        }
        if (comma == std::string::npos) {
            break;
        }
        pos = comma + 2;
    }
    return foundId && elementCount <= MAX_ELEMENTS;
}

// A set whose every element is a string-literal token -- a template `exec`
// file body's `"""..."""` position accepts either quoting style, so ANTLR's
// set here is exactly {DOUBLE_QUOTED_STRING, TRIPLE_DOUBLE_QUOTED_STRING},
// two bare lexer token names with no quoted-literal spelling to fall back
// on (unlike punctuation, a string token's *text* is the file contents, not
// a fixed spelling ANTLR can quote). Same "one recognizable shape, humanize
// it" treatment as the identifier case above, found by the same E-7 sweep.
static bool setBodyIsStringLiteral(const std::string &body) {
    if (body.empty()) {
        return false;
    }
    size_t pos = 0;
    while (pos <= body.size()) {
        size_t comma = body.find(", ", pos);
        std::string elem = (comma == std::string::npos)
            ? body.substr(pos) : body.substr(pos, comma - pos);
        if (elem != "DOUBLE_QUOTED_STRING" && elem != "TRIPLE_DOUBLE_QUOTED_STRING") {
            return false;
        }
        if (comma == std::string::npos) {
            break;
        }
        pos = comma + 2;
    }
    return true;
}

// The "what ANTLR wants here" fragment of a message: either a braced set
// (`{'a', 'b'}`) or a single bare/quoted element with no braces at all
// (`'a'`, or the bare token name `ID`). Every classifier branch below that
// inspects or reformats this fragment goes through here once instead of
// re-deriving "does it start with '{'" and "where's the matching '}'"
// independently at each call site.
static std::string setBody(const std::string &text) {
    if (!text.empty() && text.front() == '{') {
        size_t close = text.find('}');
        if (close != std::string::npos) {
            return text.substr(1, close - 1);
        }
    }
    return text;
}

// Strip ANTLR's brace-set syntax from `text`, and prefix a multi-element set
// with "one of" so the result reads as plain English:
// "{'static', 'function'}" -> "one of 'static', 'function'"; a single
// element is returned with its braces (if any) simply removed. Does not
// touch a set containing a bare token name (ID, TOK_*, ...) -- that shape is
// jargon for a different reason (setBodyHasBareIdentifierElement above) and
// is left to G3 to catch, since a real fix needs the rule-context name table
// this classifier deliberately doesn't have (see E-6's Landed note).
static std::string humanizeSetText(const std::string &text) {
    std::string body = setBody(text);
    if (body == text || body.find(',') == std::string::npos) {
        return body;
    }
    return "one of " + body;
}

// G7: the offending token's own text is quoted into most of the messages
// below. It is usually a handful of punctuation characters, but ANTLR hands
// back the *full* text of whatever token it actually matched -- a triple-
// quoted template string, say -- and that can be arbitrarily long and
// contain embedded newlines. Every "'" + sym + "'" splice uses this
// sanitized form instead of raw `sym`; boolean checks on `sym` (size,
// first-character class, an exact keyword match) keep using the original,
// since sanitizing would not change their answer.
static std::string sanitizeSymForMessage(const std::string &sym) {
    static const size_t MAX_LEN = 40;
    std::string out;
    out.reserve(sym.size());
    for (char c : sym) {
        out += (c == '\n' || c == '\r' || c == '\t') ? ' ' : c;
    }
    if (out.size() > MAX_LEN) {
        out = out.substr(0, MAX_LEN) + "...";
    }
    return out;
}

static RewrittenSyntaxError rewriteSyntaxError(const std::string &msg, const std::string &symRaw) {
    const std::string sym = sanitizeSymForMessage(symRaw);
    if (msg.rfind("missing ", 0) == 0) {
        // ANTLR's single-token-insertion recovery: "missing 'X' at 'Y'" when
        // exactly one token would satisfy the position, or
        // "missing {A, B, ...} at 'Y'" when more than one would. Originally
        // two separate branches (an {ID, ESCAPED_ID}-only special case, and
        // a single-quoted-token catch-all); unified after E-7's mutation
        // sweep hit a third shape, "missing {DOUBLE_QUOTED_STRING,
        // TRIPLE_DOUBLE_QUOTED_STRING} at ...", a braced set that is neither.
        size_t at = msg.find(" at ");
        std::string what = msg.substr(std::string("missing ").size(),
            at == std::string::npos ? std::string::npos
                                     : at - std::string("missing ").size());
        if (setBodyHasBareIdentifierElement(setBody(what))) {
            return {"expected identifier before '" + sym + "'", "PSS022"};
        }
        if (setBodyIsStringLiteral(setBody(what))) {
            return {"expected a string literal before '" + sym + "'", "PSS020"};
        }
        return {"expected " + humanizeSetText(what) + " before '" + sym + "'", "PSS020"};
    }
    if (msg.find("mismatched input") != std::string::npos) {
        // Everything from "expecting" to the end of the message -- the
        // "what ANTLR wants here" clause every "mismatched input" message
        // carries. Computed once and reused by every sub-branch below
        // instead of each re-searching for "expecting" independently.
        size_t expectingAt = msg.find("expecting");
        std::string expecting = (expectingAt == std::string::npos)
            ? std::string() : msg.substr(expectingAt);
        std::string expectingWhat = expecting.empty()
            ? std::string() : expecting.substr(std::string("expecting ").size());

        if (setBodyHasBareIdentifierElement(setBody(expectingWhat))) {
            // D1: same "an identifier belongs here" situation as the
            // single-token-insertion branch above, just reached via ANTLR's
            // other recovery strategy (deletion+report instead of
            // insertion+report) -- give it the same PSS022 wording instead
            // of leaking the raw expecting-set as a generic PSS024.
            return {"expected identifier before '" + sym + "'", "PSS022"};
        }
        if (setBodyIsStringLiteral(setBody(expectingWhat))) {
            return {"expected a string literal before '" + sym + "'", "PSS020"};
        }
        if (msg.find("expecting {',', ';'}") != std::string::npos ||
            msg.find("expecting ';'") != std::string::npos) {
            return {"expected ';' before '" + sym + "'", "PSS020"};
        }
        if (msg.find("expecting {'{', ':', '<'}") != std::string::npos ||
            msg.find("expecting {'{', ':'}") != std::string::npos) {
            std::string hint;
            if (sym == "extends") {
                hint = "; use ':' for inheritance, not 'extends'";
            }
            return {"expected '{' or ':' before '" + sym + "'" + hint, "PSS020"};
        }
        if (expecting.size() > 60) {
            return {"unexpected '" + sym + "' in this context", "PSS024"};
        }
        return {"unexpected '" + sym + "' expecting "
            + humanizeSetText(expectingWhat), "PSS024"};
    }
    if (msg.find("extraneous input") != std::string::npos) {
        // D11: only call the offending token a "keyword" when it looks like
        // one (starts with a letter or '_'). A numeric literal or a
        // multi-char punctuation run is neither punctuation-single-char
        // (the PSS025 case) nor a keyword -- it still belongs to PSS025's
        // sibling PSS026 bucket (this classifier only has the two), but
        // should not be *called* a keyword.
        bool looksLikeKeyword = !sym.empty() &&
            (isalpha((unsigned char)sym[0]) || sym[0] == '_');
        if (sym.size() == 1 && !isalpha((unsigned char)sym[0])) {
            return {"unexpected '" + sym + "' in this context", "PSS025"};
        }
        if (looksLikeKeyword) {
            return {"unexpected keyword '" + sym + "' in this context", "PSS026"};
        }
        return {"unexpected '" + sym + "' in this context", "PSS026"};
    }
    if (msg.find("no viable alternative") != std::string::npos) {
        return {"syntax error at '" + sym + "'", "PSS028"};
    }
    return {msg, ""};
}

/**
 * D8: names of the two grammar rules that get "unclosed '{' for KIND 'NAME'"
 * treatment when input runs out while they're still open. Only checked
 * against the innermost active rule at the point of the EOF error -- a
 * truncation several rules deeper (mid-exec-body, say) is a less specific
 * diagnosis than pointing at a distant enclosing component's brace would be,
 * so it deliberately falls through to the generic EOF message instead.
 */
static bool findUnclosedOpener(
        ParserRuleContext *ctx, std::string &kind, std::string &name, Token *&open) {
    if (PSSParser::Component_declarationContext *cc =
            dynamic_cast<PSSParser::Component_declarationContext *>(ctx)) {
        if (cc->TOK_LCBRACE() && cc->component_identifier()) {
            kind = "component";
            name = cc->component_identifier()->getText();
            open = cc->TOK_LCBRACE()->getSymbol();
            return true;
        }
    } else if (PSSParser::Struct_declarationContext *sc =
            dynamic_cast<PSSParser::Struct_declarationContext *>(ctx)) {
        if (sc->TOK_LCBRACE() && sc->identifier()) {
            kind = "struct";
            name = sc->identifier()->getText();
            open = sc->TOK_LCBRACE()->getSymbol();
            return true;
        }
    }
    return false;
}

void AstBuilderInt::syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) {
	if (m_marker_l) {
		if (IMarkerCollector *coll = dynamic_cast<IMarkerCollector *>(m_marker_l)) {
			if (coll->maxErrorsExceeded()) {
				// PSS029 already announced; a hopelessly-broken file can
				// otherwise cascade into thousands of recovery errors.
				return;
			}
		}

		const std::string sym = offendingSymbol->getText();

		// D2: cascade suppression. A second syntax error within a couple of
		// tokens of the last one, and still inside the same rule, is almost
		// always ANTLR flailing through the same garbage region rather than
		// an independent defect -- report only the first.
		size_t rule_idx = static_cast<size_t>(-1);
		Parser *parser = dynamic_cast<Parser *>(recognizer);
		if (parser && parser->getContext()) {
			rule_idx = parser->getContext()->getRuleIndex();
		}
		ssize_t tok_idx = static_cast<ssize_t>(offendingSymbol->getTokenIndex());
		bool suppress =
			m_last_syntax_error_token_idx >= 0 &&
			rule_idx == m_last_syntax_error_rule_idx &&
			tok_idx >= m_last_syntax_error_token_idx &&
			(tok_idx - m_last_syntax_error_token_idx) <= 2;
		m_last_syntax_error_token_idx = tok_idx;
		m_last_syntax_error_rule_idx = rule_idx;
		if (suppress) {
			return;
		}

		ast::Location loc;
		loc.fileid = m_file_id;
		loc.lineno = line;
		loc.linepos = charPositionInLine;
        loc.extent = sym.size();

        if (sym == "<EOF>") {
            std::string kind, name;
            Token *open = nullptr;
            if (parser && parser->getContext() &&
                    findUnclosedOpener(parser->getContext(), kind, name, open)) {
                ast::Location open_loc;
                open_loc.fileid = m_file_id;
                open_loc.lineno = open->getLine();
                open_loc.linepos = open->getCharPositionInLine();
                open_loc.extent = 1;

                Marker m(
                    "unclosed '{' for " + kind + " '" + name + "'",
                    MarkerSeverityE::Error,
                    open_loc,
                    std::string("PSS021"));
                m.addRelated(loc, "input ends here");
                m_marker_l->marker(&m);
            } else {
                Marker m(
                    "unexpected end of input; missing closing '}'",
                    MarkerSeverityE::Error,
                    loc,
                    std::string("PSS021"));
                m_marker_l->marker(&m);
            }
            return;
        }

		RewrittenSyntaxError rewritten = rewriteSyntaxError(msg, sym);

		if (rewritten.id.empty()) {
			Marker m(
					rewritten.msg,
					MarkerSeverityE::Error,
					loc);
			m_marker_l->marker(&m);
		} else {
			Marker m(
					rewritten.msg,
					MarkerSeverityE::Error,
					loc,
					rewritten.id);
			m_marker_l->marker(&m);
		}
	}
}

void AstBuilderInt::addChild(ast::IScopeChild *c, Token *t, const ast::Location *loc, Token *ct, Token *stop, Token *trailing_stop) {
    DEBUG_ENTER("addChild (IScopeChild) %p %p", t, loc);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
	c->setParent(scope());
    attachPendingAnnotations(c);
    if (loc) {
        c->setLocation(*loc);
    } else if (t) {
        c->setLocation({
            m_file_id,
            (int32_t)t->getLine(),
            (int32_t)t->getCharPositionInLine()+1
        });
    }

    // Measured from `t`, which is where `location` points -- for a field that
    // is the identifier, not the type.  `ct` is the doc anchor and may sit
    // further left; using it would make `extent` inconsistent with `location`.
    setExtent(c, t, stop);

	if (m_collectDocStrings && (t || ct)) {
		addDocstring(c, docstringAnchor((ct)?ct:t), (trailing_stop)?trailing_stop:stop);
	}
    DEBUG_LEAVE("addChild (IScopeChild) %p %p", t, loc);
}

void AstBuilderInt::addChild(ast::ISymbolScope *c, Token *start, Token *end) {
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
	c->setParent(scope());
    attachPendingAnnotations(c);
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    setExtent(c, start, end);

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
}

void AstBuilderInt::addChild(ast::INamedScopeChild *c, Token *t) {
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
	c->setParent(scope());
    attachPendingAnnotations(c);
    c->setLocation({
        m_file_id,
        (int32_t)t->getLine(),
        (int32_t)t->getCharPositionInLine()+1
    });

	if (m_collectDocStrings && t) {
		addDocstring(c, docstringAnchor(t));
	}
}

void AstBuilderInt::addChild(ast::IConstraintScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    setExtent(c, start, end);
	c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
}

void AstBuilderInt::addChild(ast::IExecScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    setExtent(c, start, end);
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
	collectScopeTrailingComments(c, end);
}

void AstBuilderInt::addChild(ast::IFunctionDefinition *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    setExtent(c, start, end);
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
	collectScopeTrailingComments(c, end);
}

void AstBuilderInt::addChild(ast::INamedScope *c, Token *start, Token *end) {
    DEBUG_ENTER("addChild (INamedScope) %s %p %p", c->getName()->getId().c_str(), start, end);
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    setExtent(c, start, end);
    c->setParent(scope());
    attachPendingAnnotations(c);
    DEBUG("Parent: %p", c->getParent());
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
	collectScopeTrailingComments(c, end);
    DEBUG_LEAVE("addChild (INamedScope) %p %p", start, end);
}

void AstBuilderInt::addChild(ast::IScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()
    });
    setExtent(c, start, end);
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, docstringAnchor(start), end);
	}
	collectScopeTrailingComments(c, end);
}

int32_t AstBuilderInt::tokenEndLine(Token *t) {
	int32_t line = (int32_t)t->getLine();
	const std::string &txt = t->getText();

	// SL_COMMENT is lexed as `'//' .*? '\r'? ('\n'|EOF)`, so a `//` comment
	// carries its own line terminator. Counting that newline would put the
	// comment on the following line and make a blank-line-detached note look
	// adjacent to whatever follows it.
	size_t n = txt.size();
	if (n > 0 && txt[n-1] == '\n') {
		n--;
	}

	for (size_t i=0; i<n; i++) {
		if (txt[i] == '\n') {
			line++;
		}
	}

	return line;
}

std::string AstBuilderInt::normalizeComment(const std::string &raw, bool is_block) {
	if (!is_block) {
		// `// text` -- drop the marker and at most one space, so that the
		// relative indent of a run of `//` lines survives.
		std::string body = (raw.size() >= 2)?raw.substr(2):std::string();
		if (body.size() > 0 && body[0] == ' ') {
			body = body.substr(1);
		}
		while (body.size() > 0 && isspace((unsigned char)body[body.size()-1])) {
			body.erase(body.size()-1);
		}
		return body;
	}

	bool has_doc_marker = (raw.compare(0, 3, "/**") == 0);
	std::string body = raw;
	if (body.size() >= 2 && body.compare(0, 2, "/*") == 0) {
		body = body.substr(2);
	}
	if (body.size() >= 2 && body.compare(body.size()-2, 2, "*/") == 0) {
		body = body.substr(0, body.size()-2);
	}

	std::vector<std::string> lines;
	size_t pos = 0;
	while (true) {
		size_t nl = body.find('\n', pos);
		if (nl == std::string::npos) {
			lines.push_back(body.substr(pos));
			break;
		}
		std::string l = body.substr(pos, nl-pos);
		if (l.size() > 0 && l[l.size()-1] == '\r') {
			l.erase(l.size()-1);
		}
		lines.push_back(l);
		pos = nl+1;
	}

	// Strip the `*` gutter. Continuation lines always; the first line only
	// when the comment opened `/**`, so that `/* *emph* */` keeps its text.
	for (size_t i=0; i<lines.size(); i++) {
		if (i == 0 && !has_doc_marker) {
			continue;
		}
		std::string &l = lines[i];
		size_t j = 0;
		while (j < l.size() && (l[j] == ' ' || l[j] == '\t')) {
			j++;
		}
		if (j < l.size() && l[j] == '*') {
			j++;
			if (j < l.size() && l[j] == ' ') {
				j++;
			}
			l = l.substr(j);
		}
	}

	for (size_t i=0; i<lines.size(); i++) {
		std::string &l = lines[i];
		while (l.size() > 0 && isspace((unsigned char)l[l.size()-1])) {
			l.erase(l.size()-1);
		}
	}

	while (lines.size() > 0 && lines.front().empty()) {
		lines.erase(lines.begin());
	}
	while (lines.size() > 0 && lines.back().empty()) {
		lines.pop_back();
	}

	// Re-flush the block against the left margin, keeping relative indent.
	size_t indent = std::string::npos;
	for (size_t i=0; i<lines.size(); i++) {
		if (lines[i].empty()) {
			continue;
		}
		size_t j = 0;
		while (j < lines[i].size() && lines[i][j] == ' ') {
			j++;
		}
		if (indent == std::string::npos || j < indent) {
			indent = j;
		}
	}
	if (indent == std::string::npos) {
		indent = 0;
	}

	std::string result;
	for (size_t i=0; i<lines.size(); i++) {
		if (i > 0) {
			result += "\n";
		}
		result += (lines[i].size() >= indent)?lines[i].substr(indent):lines[i];
	}

	return result;
}

ast::IComment *AstBuilderInt::mkCommentFor(Token *t, ast::CommentPlacement placement) {
	bool is_block = (t->getChannel() == 12);
	std::string raw = t->getText();
	ast::IComment *cm = m_factory->mkComment(
			normalizeComment(raw, is_block),
			placement);
	cm->setRaw(raw);
	cm->setIs_block(is_block);
	cm->setLocation({
		m_file_id,
		(int32_t)t->getLine(),
		(int32_t)t->getCharPositionInLine()+1,
		(int32_t)raw.size()
	});
	return cm;
}

void AstBuilderInt::addDocstring(ast::IScopeChild *c, Token *t, Token *stop) {
	DEBUG_ENTER("addDocstring");
	// The anchor is the start of the outermost declaration context as written
	// in source.  A wrapper rule -- `attr_field`'s `rand` / `static const`, for
	// instance -- puts tokens between the comment and the token the
	// constructing visitor happens to hold, so the visitor's token is only a
	// fallback (see DocAnchorScope).
	Token *anchor = docAnchor(t);

	DocComment dc;
	if (m_doc_extractor && m_doc_extractor->extractLeading(anchor, dc)) {
		DEBUG("docstring=%s", dc.text.c_str());
		applyDocComment(c, dc);
	} else if (m_doc_extractor && stop &&
			m_doc_extractor->extractTrailing(stop, dc)) {
		// A leading comment always wins; a trailing one is consulted only when
		// there is none (§3.5).
		DEBUG("trailing docstring=%s", dc.text.c_str());
		applyDocComment(c, dc);
	}

	// The docstring is one comment; `comments` is all of them. The two are
	// extracted independently -- the extractor decides what documents `c`,
	// this records what was written around it.
	attachComments(c, anchor);

	DEBUG_LEAVE("addDocstring");
}

/**
 * Record the extracted comment on *c*: the normalized text, plus the verbatim
 * source, its lexical form and its own location (E4).  Keeping the raw text
 * lets a consumer apply a different dialect without re-lexing, and the
 * location lets a malformed doc comment be reported where it was written.
 */
void AstBuilderInt::applyDocComment(ast::IScopeChild *c, const DocComment &dc) {
	if (!dc.text.empty()) {
		c->setDocstring(dc.text);
	}
	c->setDocRaw(dc.raw);
	c->setDocForm(toAstDocForm(dc.form));
	c->setDocLocation(dc.location);
}

// Both namespaces spell this type `DocCommentForm`, and this file has
// `using namespace ast`, so every mention here is qualified.
ast::DocCommentForm AstBuilderInt::toAstDocForm(pssp::DocCommentForm form) {
	switch (form) {
		case pssp::DocCommentForm::Line:     return ast::DocCommentForm::DocForm_Line;
		case pssp::DocCommentForm::DocLine:  return ast::DocCommentForm::DocForm_DocLine;
		case pssp::DocCommentForm::Block:    return ast::DocCommentForm::DocForm_Block;
		case pssp::DocCommentForm::DocBlock: return ast::DocCommentForm::DocForm_DocBlock;
		default:                             return ast::DocCommentForm::DocForm_None;
	}
}

void AstBuilderInt::setExtent(ast::IScopeChild *c, Token *start, Token *stop) {
	if (!c || !start || !stop) {
		return;
	}
	// One past the last character of the stop token, so the range covers the
	// closing brace or semicolon rather than stopping just before it.
	c->setEndLocation({
		m_file_id,
		(int32_t)stop->getLine(),
		(int32_t)stop->getCharPositionInLine() + 1 + (int32_t)stop->getText().size()
	});
	// getStopIndex() is inclusive.
	int32_t extent = (int32_t)stop->getStopIndex() - (int32_t)start->getStartIndex() + 1;
	if (extent > 0) {
		ast::Location loc = c->getLocation();
		loc.extent = extent;
		c->setLocation(loc);
	}
}

void AstBuilderInt::attachDocstring(ast::IScopeChild *c, Token *t) {
	if (!m_collectDocStrings || !c || !t || !m_doc_extractor) {
		return;
	}
	DocComment dc;
	if (m_doc_extractor->extractLeading(t, dc)) {
		applyDocComment(c, dc);
	}
	attachComments(c, t);
}

void AstBuilderInt::attachComments(ast::IScopeChild *c, Token *t) {
	DEBUG_ENTER("attachComments");

	if (!m_collectComments || !t || !c) {
		DEBUG_LEAVE("attachComments -- not collecting");
		return;
	}

	attachTrailingComment(c, t);

	size_t idx = t->getTokenIndex();
	if (idx == 0) {
		DEBUG_LEAVE("attachComments -- first token");
		return;
	}

	std::vector<Token *> cmts = m_tokens->getHiddenTokensToLeft(idx, 11);
	std::vector<Token *> mlc = m_tokens->getHiddenTokensToLeft(idx, 12);
	cmts.insert(cmts.end(), mlc.begin(), mlc.end());

	if (cmts.empty()) {
		DEBUG_LEAVE("attachComments -- no comments");
		return;
	}

	// `//` and `/* */` arrive on separate channels, so a file that interleaves
	// them comes back in two runs. Restore source order.
	std::sort(cmts.begin(), cmts.end(), [](Token *a, Token *b) {
		return a->getTokenIndex() < b->getTokenIndex();
	});

	// A comment sharing a line with the previous on-channel token documents
	// *that* construct -- `x = 1; // note` -- and its owner has already
	// claimed it via attachTrailingComment. Skip it here.
	int32_t prev_line = -1;
	for (int32_t i=(int32_t)cmts.front()->getTokenIndex()-1; i>=0; i--) {
		Token *p = m_tokens->get(i);
		if (p->getChannel() == Token::DEFAULT_CHANNEL) {
			prev_line = tokenEndLine(p);
			break;
		}
	}

	size_t first = 0;
	while (first < cmts.size() && (int32_t)cmts[first]->getLine() == prev_line) {
		first++;
	}

	// Walk back from the construct over the contiguous run of comment lines.
	// A blank line cuts it -- that is how a note is deliberately detached.
	int32_t anchor = (int32_t)t->getLine();
	size_t lead = cmts.size();
	while (lead > first && tokenEndLine(cmts[lead-1]) >= anchor-1) {
		lead--;
		anchor = (int32_t)cmts[lead]->getLine();
	}

	for (size_t i=first; i<cmts.size(); i++) {
		c->getComments().push_back(ast::ICommentUP(mkCommentFor(
				cmts[i],
				(i >= lead)
					?ast::CommentPlacement::CommentPlacement_Leading
					:ast::CommentPlacement::CommentPlacement_Orphan)));
	}

	DEBUG_LEAVE("attachComments");
}

std::string AstBuilderInt::attachTrailingComment(ast::IScopeChild *c, Token *t) {
	std::string text;

	if (!t || !c) {
		return text;
	}

	int32_t line = tokenEndLine(t);
	size_t n = m_tokens->size();
	bool past_terminator = false;

	// Callers hand us the construct's *start* token, so walk forward to find
	// the comment that trails its end. The construct runs to its `;`; once
	// that is behind us, the next on-channel token opens the following
	// construct and any comment past it is that one's business, not ours.
	for (size_t i=t->getTokenIndex()+1; i<n; i++) {
		Token *nt = m_tokens->get(i);

		if ((int32_t)nt->getLine() != line) {
			break;
		}

		size_t ch = nt->getChannel();
		if (ch == 11 || ch == 12) {
			text = normalizeComment(nt->getText(), ch == 12);
			if (m_collectComments) {
				c->getComments().push_back(ast::ICommentUP(mkCommentFor(
						nt,
						ast::CommentPlacement::CommentPlacement_Trailing)));
			}
			break;
		} else if (ch == Token::DEFAULT_CHANNEL) {
			if (past_terminator) {
				break;
			} else if (nt->getText() == ";") {
				past_terminator = true;
			} else if (nt->getText() == "}") {
				// The construct is the last in its block; whatever follows the
				// brace documents the block, not this construct.
				break;
			}
		}
	}

	return text;
}

void AstBuilderInt::collectScopeTrailingComments(ast::IScopeChild *s, Token *end) {
	if (!m_collectComments || !s || !end) {
		return;
	}

	size_t idx = end->getTokenIndex();
	if (idx == 0) {
		return;
	}

	std::vector<Token *> cmts = m_tokens->getHiddenTokensToLeft(idx, 11);
	std::vector<Token *> mlc = m_tokens->getHiddenTokensToLeft(idx, 12);
	cmts.insert(cmts.end(), mlc.begin(), mlc.end());

	if (cmts.empty()) {
		return;
	}

	std::sort(cmts.begin(), cmts.end(), [](Token *a, Token *b) {
		return a->getTokenIndex() < b->getTokenIndex();
	});

	// Same partition as attachComments: whatever trails the scope's last
	// statement already belongs to that statement.
	int32_t prev_line = -1;
	for (int32_t i=(int32_t)cmts.front()->getTokenIndex()-1; i>=0; i--) {
		Token *p = m_tokens->get(i);
		if (p->getChannel() == Token::DEFAULT_CHANNEL) {
			prev_line = tokenEndLine(p);
			break;
		}
	}

	for (size_t i=0; i<cmts.size(); i++) {
		if ((int32_t)cmts[i]->getLine() == prev_line) {
			continue;
		}
		s->getTrailing_comments().push_back(ast::ICommentUP(mkCommentFor(
				cmts[i],
				ast::CommentPlacement::CommentPlacement_Orphan)));
	}
}

void AstBuilderInt::reportUnattachedAnnotation(ast::IAnnotation *a) {
	if (!m_marker_l || !a) {
		return;
	}
	std::string name;
	if (a->getType()) {
		for (uint32_t i=0; i<a->getType()->getElems().size(); i++) {
			if (i) {
				name += "::";
			}
			name += a->getType()->getElems().at(i)->getId()->getId();
		}
	}
	char msg[512];
	snprintf(msg, sizeof(msg),
		"annotation '%s' has no subsequent element in this scope to attach to. "
		"An element annotation attaches to the next declaration; terminate it "
		"with ';' if a standalone annotation was intended (PSS 3.1 7.13)",
		name.c_str());
	Marker m(msg, MarkerSeverityE::Error, a->getLocation());
	m_marker_l->marker(&m);
}

bool AstBuilderInt::isStandaloneAnnotation(PSSParser::AnnotationContext *ctx) {
	if (!ctx || !ctx->stop || !m_tokens) {
		return false;
	}
	size_t next = ctx->stop->getTokenIndex() + 1;
	while (next < m_tokens->size()) {
		Token *t = m_tokens->get(next);
		if (t->getChannel() != Token::DEFAULT_CHANNEL) {
			next++;
			continue;
		}
		return t->getText() == ";";
	}
	return false;
}

void AstBuilderInt::discardPendingAnnotations(size_t mark) {
    while (m_pending_annotations.size() > mark) {
        delete m_pending_annotations.back();
        m_pending_annotations.pop_back();
    }
}

void AstBuilderInt::attachPendingAnnotations(ast::IScopeChild *c) {
    if (!m_pending_annotations.empty()) {
        m_attached_annotation_tok = m_pending_annotation_tok;
        m_pending_annotation_tok = 0;
        for (std::vector<ast::IAnnotation *>::const_iterator
            it=m_pending_annotations.begin();
            it!=m_pending_annotations.end(); it++) {
            c->getAnnotations().push_back(ast::IAnnotationUP(*it));
        }
        m_pending_annotations.clear();
    }
}

Token *AstBuilderInt::docstringAnchor(Token *t) {
    Token *anchor = m_attached_annotation_tok;
    m_attached_annotation_tok = 0;
    return anchor ? anchor : t;
}

void AstBuilderInt::push_scope(ast::IScope *s) {
	DEBUG("-- push_scope");
	// Entering a scope suspends any active doc anchor: the anchor describes one
	// declaration, and the declarations nested inside it must find their own
	// comments.  A null entry reads as "no anchor in force".
	m_doc_anchors.push_back(0);
	m_scopes.push_back(s);
}

void AstBuilderInt::pop_scope() { 
	DEBUG("-- pop_scope");
    if (!m_pending_annotations.empty()) {
        // LRM 7.13: an element annotation "is attached to the next PSS model
        // element declared in the scope.  It is an error if no subsequent
        // element is present in the scope."  These were dropped silently, so
        // Example32's third case -- an annotation at the end of a scope -- was
        // accepted.  Standalone annotations never reach here: visitAnnotation
        // recognizes them by their terminating `;` and does not queue them.
        DEBUG("Reporting %d unattached annotations at scope pop",
            (int)m_pending_annotations.size());
        for (std::vector<ast::IAnnotation *>::const_iterator
            it=m_pending_annotations.begin();
            it!=m_pending_annotations.end(); it++) {
            reportUnattachedAnnotation(*it);
            delete *it;
        }
        m_pending_annotations.clear();
        m_pending_annotation_tok = 0;
    }
	popDocAnchor();
	m_scopes.pop_back();
}

void AstBuilderInt::addErrorMarker(Token *t, const char *fmt, ...) {
    if (!m_marker_l) {
        return;
    }

    char tmp[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(tmp, sizeof(tmp), fmt, ap);
    va_end(ap);

    ast::Location loc;
    loc.fileid = m_file_id;
    loc.lineno = t ? t->getLine() : 0;
    loc.linepos = t ? t->getCharPositionInLine()+1 : 0;
    loc.extent = t ? t->getText().size() : 0;

    Marker m(tmp, MarkerSeverityE::Error, loc);
    m_marker_l->marker(&m);
}

bool AstBuilderInt::evalCompileTimeCond(
        PSSParser::Constant_expressionContext   *ctx,
        int64_t                                 &val,
        const char                              *construct) {
    if (!ctx) {
        return false;
    }
    if (evalConstantExpression(ctx, val)) {
        return true;
    }

    // "The value of any compile if expressions must be determinable at compile
    // time" (19.1.3).  Reading an indeterminable condition as false is what
    // made a cross-file `static const` reference drop its branch and still
    // report a clean parse.
    addErrorMarker(
        ctx->start,
        "%s condition cannot be evaluated at compile time: '%s'. "
        "Compile-time expressions may reference only types and constants declared "
        "in this source unit or in a previously-processed one (PSS 3.1 19.1.2)",
        construct,
        ctx->getText().c_str());

    return false;
}

bool AstBuilderInt::evalConstantExpression(PSSParser::Constant_expressionContext *ctx, int64_t &val) {
    return evalExpression(ctx->expression(), val);
}

bool AstBuilderInt::evalExpression(PSSParser::ExpressionContext *ctx, int64_t &val) {
    if (ctx->unary_op()) {
        int64_t rhs = 0;
        if (!evalExpression(ctx->lhs, rhs)) {
            return false;
        }
        std::string op = ctx->unary_op()->getText();
        if (op == "+") {
            val = rhs;
        } else if (op == "-") {
            val = -rhs;
        } else if (op == "!") {
            val = !rhs;
        } else if (op == "~") {
            val = ~rhs;
        } else {
            return false;
        }
        return true;
    } else if (ctx->lhs && ctx->rhs) {
        int64_t lhs = 0, rhs = 0;
        if (!evalExpression(ctx->lhs, lhs) || !evalExpression(ctx->rhs, rhs)) {
            return false;
        }
        if (ctx->exp_op()) {
            int64_t r = 1;
            for (int64_t i=0; i<rhs; i++) {
                r *= lhs;
            }
            val = r;
        } else if (ctx->mul_div_mod_op()) {
            std::string op = ctx->mul_div_mod_op()->getText();
            if (op == "*") val = lhs * rhs;
            else if (op == "/") val = rhs ? (lhs / rhs) : 0;
            else val = rhs ? (lhs % rhs) : 0;
        } else if (ctx->add_sub_op()) {
            val = (ctx->add_sub_op()->getText() == "+") ? lhs + rhs : lhs - rhs;
        } else if (ctx->shift_op()) {
            val = (ctx->shift_op()->getText().find("<<") != std::string::npos) ? (lhs << rhs) : (lhs >> rhs);
        } else if (ctx->logical_inequality_op()) {
            std::string op = ctx->logical_inequality_op()->getText();
            if (op == "<") val = lhs < rhs;
            else if (op == "<=") val = lhs <= rhs;
            else if (op == ">") val = lhs > rhs;
            else val = lhs >= rhs;
        } else if (ctx->eq_neq_op()) {
            val = (ctx->eq_neq_op()->getText() == "==") ? (lhs == rhs) : (lhs != rhs);
        } else if (ctx->binary_and_op()) {
            val = lhs & rhs;
        } else if (ctx->binary_xor_op()) {
            val = lhs ^ rhs;
        } else if (ctx->binary_or_op()) {
            val = lhs | rhs;
        } else if (ctx->logical_and_op()) {
            val = (lhs && rhs);
        } else if (ctx->logical_or_op()) {
            val = (lhs || rhs);
        } else {
            return false;
        }
        return true;
    } else if (ctx->lhs) {
        if (ctx->conditional_expr()) {
            int64_t cond = 0;
            if (!evalExpression(ctx->lhs, cond)) {
                return false;
            }
            return evalExpression(cond ? ctx->conditional_expr()->true_expr : ctx->conditional_expr()->false_expr, val);
        } else {
            return false;
        }
    } else if (ctx->primary()) {
        if (ctx->primary()->bool_literal()) {
            val = ctx->primary()->bool_literal()->TOK_TRUE() ? 1 : 0;
            return true;
        } else if (ctx->primary()->number()) {
            std::string txt = ctx->primary()->number()->getText();

            if (ctx->primary()->number()->integer_number()) {
                int32_t width;
                uint64_t value;
                bool is_signed;
                if (!parseIntegerLiteral(txt, width, value, is_signed)) {
                    return false;
                }
                val = (int64_t)value;
                return true;
            }

            // A float where an integer is required. Truncating it is what this
            // has always done; reporting it belongs with the rest of
            // compile-time type checking, which does not exist yet.
            val = (int64_t)strtod(stripSeparators(txt).c_str(), 0);
            return true;
        } else if (ctx->primary()->paren_expr()) {
            return evalExpression(ctx->primary()->paren_expr()->expression(), val);
        } else if (ctx->primary()->compile_has_expr()) {
            val = evalCompileHas(ctx->primary()->compile_has_expr()->ref_path()) ? 1 : 0;
            return true;
        } else if (ctx->primary()->ref_path()) {
            ast::IScopeChild *target = resolveRefPathTarget(ctx->primary()->ref_path());
            return target ? evalScopeChildValue(target, val) : false;
        } else if (ctx->primary()->cast_expression()) {
            return evalExpression(ctx->primary()->cast_expression()->expression(), val);
        }
    }
    return false;
}

bool AstBuilderInt::evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, int64_t &val) {
    if (!expr) {
        return false;
    }

    if (ast::IExprBool *b = dynamic_cast<ast::IExprBool *>(expr)) {
        val = b->getValue();
        return true;
    } else if (ast::IExprSignedNumber *n = dynamic_cast<ast::IExprSignedNumber *>(expr)) {
        val = n->getValue();
        return true;
    } else if (ast::IExprUnsignedNumber *n = dynamic_cast<ast::IExprUnsignedNumber *>(expr)) {
        val = n->getValue();
        return true;
    } else if (ast::IExprCast *c = dynamic_cast<ast::IExprCast *>(expr)) {
        return evalAstExpression(eval_scope, c->getExpr(), val);
    } else if (ast::IExprCond *c = dynamic_cast<ast::IExprCond *>(expr)) {
        int64_t cond = 0;
        if (!evalAstExpression(eval_scope, c->getCond_e(), cond)) {
            return false;
        }
        return evalAstExpression(eval_scope, cond ? c->getTrue_e() : c->getFalse_e(), val);
    } else if (ast::IExprCompileHas *h = dynamic_cast<ast::IExprCompileHas *>(expr)) {
        if (!h->getRef()) {
            return false;
        }
        val = resolveRefPathTarget(eval_scope, h->getRef()) ? 1 : 0;
        return true;
    } else if (ast::IExprRefPath *rp = dynamic_cast<ast::IExprRefPath *>(expr)) {
        ast::IScopeChild *target = resolveRefPathTarget(eval_scope, rp);
        return target ? evalScopeChildValue(target, val) : false;
    } else if (ast::IExprBin *b = dynamic_cast<ast::IExprBin *>(expr)) {
        int64_t lhs = 0, rhs = 0;
        if (b->getOp() == ast::ExprBinOp::BinOp_Eq || b->getOp() == ast::ExprBinOp::BinOp_Ne) {
            if (evalAstExpression(eval_scope, b->getLhs(), lhs) && evalAstExpression(eval_scope, b->getRhs(), rhs)) {
                val = (b->getOp() == ast::ExprBinOp::BinOp_Eq) ? (lhs == rhs) : (lhs != rhs);
                return true;
            }

            std::string lhs_s, rhs_s;
            if (evalAstExpression(eval_scope, b->getLhs(), lhs_s) && evalAstExpression(eval_scope, b->getRhs(), rhs_s)) {
                val = (b->getOp() == ast::ExprBinOp::BinOp_Eq) ? (lhs_s == rhs_s) : (lhs_s != rhs_s);
                return true;
            }
            return false;
        }

        if (!evalAstExpression(eval_scope, b->getLhs(), lhs) || !evalAstExpression(eval_scope, b->getRhs(), rhs)) {
            return false;
        }

        switch (b->getOp()) {
            case ast::ExprBinOp::BinOp_Exp: {
                int64_t r = 1;
                for (int64_t i=0; i<rhs; i++) {
                    r *= lhs;
                }
                val = r;
            } break;
            case ast::ExprBinOp::BinOp_Mul:
                val = lhs * rhs;
                break;
            case ast::ExprBinOp::BinOp_Div:
                val = rhs ? (lhs / rhs) : 0;
                break;
            case ast::ExprBinOp::BinOp_Mod:
                val = rhs ? (lhs % rhs) : 0;
                break;
            case ast::ExprBinOp::BinOp_Add:
                val = lhs + rhs;
                break;
            case ast::ExprBinOp::BinOp_Sub:
                val = lhs - rhs;
                break;
            case ast::ExprBinOp::BinOp_Shl:
                val = lhs << rhs;
                break;
            case ast::ExprBinOp::BinOp_Shr:
                val = lhs >> rhs;
                break;
            case ast::ExprBinOp::BinOp_Lt:
                val = lhs < rhs;
                break;
            case ast::ExprBinOp::BinOp_Le:
                val = lhs <= rhs;
                break;
            case ast::ExprBinOp::BinOp_Gt:
                val = lhs > rhs;
                break;
            case ast::ExprBinOp::BinOp_Ge:
                val = lhs >= rhs;
                break;
            case ast::ExprBinOp::BinOp_BitAnd:
                val = lhs & rhs;
                break;
            case ast::ExprBinOp::BinOp_BitXor:
                val = lhs ^ rhs;
                break;
            case ast::ExprBinOp::BinOp_BitOr:
                val = lhs | rhs;
                break;
            case ast::ExprBinOp::BinOp_LogAnd:
                val = lhs && rhs;
                break;
            case ast::ExprBinOp::BinOp_LogOr:
                val = lhs || rhs;
                break;
            default:
                return false;
        }
        return true;
    }

    return false;
}

bool AstBuilderInt::evalAstExpression(ast::IScope *eval_scope, ast::IExpr *expr, std::string &val) {
    if (!expr) {
        return false;
    }

    if (ast::IExprString *s = dynamic_cast<ast::IExprString *>(expr)) {
        val = s->getValue();
        return true;
    } else if (ast::IExprCast *c = dynamic_cast<ast::IExprCast *>(expr)) {
        return evalAstExpression(eval_scope, c->getExpr(), val);
    } else if (ast::IExprCond *c = dynamic_cast<ast::IExprCond *>(expr)) {
        int64_t cond = 0;
        if (!evalAstExpression(eval_scope, c->getCond_e(), cond)) {
            return false;
        }
        return evalAstExpression(eval_scope, cond ? c->getTrue_e() : c->getFalse_e(), val);
    } else if (ast::IExprRefPath *rp = dynamic_cast<ast::IExprRefPath *>(expr)) {
        ast::IScopeChild *target = resolveRefPathTarget(eval_scope, rp);
        return target ? evalScopeChildValue(target, val) : false;
    }

    return false;
}

bool AstBuilderInt::evalCompileHas(PSSParser::Ref_pathContext *ctx) {
    return resolveRefPathTarget(ctx) != 0;
}

void AstBuilderInt::visitCompileIfItem(antlr4::ParserRuleContext *ctx) {
    for (auto *c : ctx->children) {
        c->accept(this);
    }
}

void AstBuilderInt::checkCompileIfBranches(
        antlr4::ParserRuleContext *true_body,
        antlr4::ParserRuleContext *false_body) {
    checkCompileIfBraces(true_body);
    checkCompileIfBraces(false_body);
}

void AstBuilderInt::checkCompileIfBraces(antlr4::ParserRuleContext *ctx) {
    // D2: a `compile if` branch consisting of a single unbraced item remains
    // legal, but is deprecated. Report it wherever it appears rather than only
    // on the branch the condition selects -- the spelling is deprecated
    // regardless of which way the condition happens to evaluate, and warning
    // only on the taken branch would make the diagnostic come and go as
    // unrelated configuration changed.
    if (!ctx || !m_marker_l || ctx->children.empty()) {
        return;
    }

    antlr4::tree::TerminalNode *first =
        dynamic_cast<antlr4::tree::TerminalNode *>(ctx->children.front());
    if (first && first->getSymbol()->getType() == PSSParser::TOK_LCBRACE) {
        return;
    }

    ast::Location loc;
    loc.fileid = m_file_id;
    loc.lineno = ctx->start->getLine();
    loc.linepos = ctx->start->getCharPositionInLine()+1;
    loc.extent = ctx->getText().size();

    Marker m(
        "'compile if' branch without enclosing braces is deprecated",
        MarkerSeverityE::Warn,
        loc);
    m_marker_l->marker(&m);
}

ast::IScope *AstBuilderInt::getGlobalScope(ast::IScope *s) {
    while (s && s->getParent()) {
        s = s->getParent();
    }
    return s;
}

ast::IScopeChild *AstBuilderInt::findNamedChild(ast::IScope *scope, const std::string &name) {
    if (!scope) {
        return 0;
    }
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        ast::IPackageScope *pkg = dynamic_cast<ast::IPackageScope *>(it->get());
        if (pkg && pkg->getId().size() && pkg->getId().back()->getId() == name) {
            return it->get();
        }
        ast::INamedScope *ns = dynamic_cast<ast::INamedScope *>(it->get());
        if (ns && ns->getName() && ns->getName()->getId() == name) {
            return it->get();
        }
        ast::INamedScopeChild *nsc = dynamic_cast<ast::INamedScopeChild *>(it->get());
        if (nsc && nsc->getName() && nsc->getName()->getId() == name) {
            return it->get();
        }
    }
    return 0;
}

ast::IScopeChild *AstBuilderInt::findNamedChildUp(ast::IScope *scope, const std::string &name) {
    while (scope) {
        ast::IScopeChild *ret = findNamedChild(scope, name);
        if (ret) {
            return ret;
        }
        scope = scope->getParent();
    }
    return 0;
}

ast::IScopeChild *AstBuilderInt::findPackagePath(
        ast::IScope *scope,
        const std::vector<std::string> &path,
        uint32_t &consumed) {
    consumed = 0;
    if (!scope || path.empty()) {
        return 0;
    }

    ast::IScopeChild *ret = 0;
    for (std::vector<ast::IScopeChildUP>::const_iterator
        it=scope->getChildren().begin();
        it!=scope->getChildren().end(); it++) {
        ast::IPackageScope *pkg = dynamic_cast<ast::IPackageScope *>(it->get());
        if (!pkg || pkg->getId().size() == 0 || pkg->getId().size() > path.size()) {
            continue;
        }

        bool match = true;
        for (uint32_t i=0; i<pkg->getId().size(); i++) {
            if (pkg->getId().at(i)->getId() != path.at(i)) {
                match = false;
                break;
            }
        }

        if (match && pkg->getId().size() > consumed) {
            consumed = pkg->getId().size();
            ret = it->get();
        }
    }

    return ret;
}

static bool appendTypeIdentifierPath(
        std::vector<std::string> &path,
        ast::ITypeIdentifier *type_id) {
    if (!type_id || !type_id->getElems().size()) {
        return false;
    }

    for (uint32_t i=0; i<type_id->getElems().size(); i++) {
        ast::ITypeIdentifierElem *elem = type_id->getElems().at(i).get();
        if (!elem || !elem->getId() || elem->getParams()) {
            return false;
        }
        path.push_back(elem->getId()->getId());
    }

    return !path.empty();
}

ast::IScope *AstBuilderInt::resolveDataTypeScope(ast::IDataType *type) {
    ast::IDataTypeUserDefined *ud = dynamic_cast<ast::IDataTypeUserDefined *>(type);
    if (!ud || !ud->getType_id() || !ud->getType_id()->getElems().size()) {
        return 0;
    }
    ast::IScope *start = scope();
    ast::IScopeChild *target = 0;
    for (uint32_t i=0; i<ud->getType_id()->getElems().size(); i++) {
        std::string elem = ud->getType_id()->getElems().at(i).get()->getId()->getId();
        if (i == 0) {
            target = ud->getIs_global() ? findNamedChild(getGlobalScope(start), elem) : findNamedChildUp(start, elem);
        } else {
            ast::IScope *scope_t = dynamic_cast<ast::IScope *>(target);
            target = findNamedChild(scope_t, elem);
        }
        if (!target) {
            return 0;
        }
    }
    return dynamic_cast<ast::IScope *>(target);
}

ast::IScopeChild *AstBuilderInt::findImportedPathTarget(
        ast::IScope *start,
        const std::vector<std::string> &path) {
    if (!start || path.empty()) {
        return 0;
    }

    ast::IScopeChild *ret = 0;
    for (ast::IScope *scope_it = start; scope_it; scope_it = scope_it->getParent()) {
        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=scope_it->getChildren().begin();
            it!=scope_it->getChildren().end(); it++) {
            ast::IPackageImportStmt *imp = dynamic_cast<ast::IPackageImportStmt *>(it->get());
            if (!imp || !imp->getPath()) {
                continue;
            }

            std::vector<std::string> candidate_path;
            if (!appendTypeIdentifierPath(candidate_path, imp->getPath())) {
                continue;
            }

            if (imp->getAlias()) {
                if (path.at(0) != imp->getAlias()->getId()) {
                    continue;
                }
                candidate_path.insert(candidate_path.end(), path.begin()+1, path.end());
            } else if (imp->getWildcard()) {
                candidate_path.insert(candidate_path.end(), path.begin(), path.end());
            } else {
                if (candidate_path.back() != path.at(0)) {
                    continue;
                }
                candidate_path.insert(candidate_path.end(), path.begin()+1, path.end());
            }

            ast::IScopeChild *target = resolvePathTarget(
                scope_it,
                candidate_path,
                false,
                false);
            if (!target) {
                continue;
            }

            if (ret && ret != target) {
                return 0;
            }
            ret = target;
        }
    }

    return ret;
}

ast::IScopeChild *AstBuilderInt::resolvePathTarget(
        ast::IScope *start,
        const std::vector<std::string> &path,
        bool is_global,
        bool search_imports) {
    if (path.empty()) {
        return 0;
    }

    ast::IScope *start_scope = start ? start : scope();
    ast::IScope *global_scope = getGlobalScope(start_scope);
    ast::IScopeChild *target = 0;
    uint32_t path_i = 1;


    if (is_global) {
        target = findPackagePath(global_scope, path, path_i);
        if (!target) {
            target = findNamedChild(global_scope, path.at(0));
            path_i = 1;
        }
    } else {
        target = findNamedChildUp(start_scope, path.at(0));
        if (!target) {
            if (search_imports) {
                target = findImportedPathTarget(start_scope, path);
                if (target) {
                    // findImportedPathTarget fully resolves the path
                    return target;
                }
            }
        }
        if (!target) {
            target = findPackagePath(global_scope, path, path_i);
        } else {
            path_i = 1;
        }
    }

    target = walkPathMembers(target, path, path_i);

    if (!target) {
        // Nothing in this source unit answers the path.  Compile-time
        // expressions may also reference declarations from a
        // previously-processed source unit (PSS 3.1 19.1.2), so try those
        // before giving up -- otherwise a `compile if` reading a constant from
        // another file resolves to null and silently reads as false.
        target = resolvePathTargetInPriorUnits(global_scope, path);
    }

    return target;
}

ast::IScopeChild *AstBuilderInt::walkPathMembers(
        ast::IScopeChild *target,
        const std::vector<std::string> &path,
        uint32_t path_i) {
    if (!target) {
        return 0;
    }

    for (; path_i<path.size(); path_i++) {
        // Handle enum item lookup: IEnumDecl is not a scope
        if (ast::IEnumDecl *edecl = dynamic_cast<ast::IEnumDecl *>(target)) {
            target = 0;
            for (auto &item : edecl->getItems()) {
                if (item->getName() && item->getName()->getId() == path.at(path_i)) {
                    target = item.get();
                    break;
                }
            }
            if (!target) return 0;
            continue;
        }
        ast::IScope *scope_t = dynamic_cast<ast::IScope *>(target);
        if (!scope_t) {
            if (ast::IField *f = dynamic_cast<ast::IField *>(target)) {
                scope_t = resolveDataTypeScope(f->getType());
            } else if (ast::IActionHandleField *f = dynamic_cast<ast::IActionHandleField *>(target)) {
                scope_t = resolveDataTypeScope(f->getType());
            } else if (ast::IFieldCompRef *f = dynamic_cast<ast::IFieldCompRef *>(target)) {
                scope_t = resolveDataTypeScope(f->getType());
            } else if (ast::IFieldRef *f = dynamic_cast<ast::IFieldRef *>(target)) {
                scope_t = resolveDataTypeScope(f->getType());
            } else if (ast::IFieldClaim *f = dynamic_cast<ast::IFieldClaim *>(target)) {
                scope_t = resolveDataTypeScope(f->getType());
            }
        }
        if (!scope_t) {
            return 0;
        }
        target = findNamedChild(scope_t, path.at(path_i));
        if (!target) {
            return 0;
        }
    }

    return target;
}

ast::IScopeChild *AstBuilderInt::resolvePathTargetInPriorUnits(
        ast::IScope *cur_global,
        const std::vector<std::string> &path) {
    if (path.empty()) {
        return 0;
    }

    for (std::vector<ast::IGlobalScope *>::const_reverse_iterator
        it=m_prior_units.rbegin();
        it!=m_prior_units.rend(); it++) {
        ast::IScope *unit = *it;
        if (unit == cur_global) {
            continue;
        }

        // Each unit is resolved end-to-end: a package may be split across
        // several units, so the fragment that matches the leading path
        // elements is not necessarily the one holding the member.
        uint32_t path_i = 1;
        ast::IScopeChild *target = findPackagePath(unit, path, path_i);
        if (target) {
            if (ast::IScopeChild *ret=walkPathMembers(target, path, path_i)) {
                return ret;
            }
        }

        target = findNamedChild(unit, path.at(0));
        if (target) {
            if (ast::IScopeChild *ret=walkPathMembers(target, path, 1)) {
                return ret;
            }
        }
    }

    return 0;
}

ast::IScopeChild *AstBuilderInt::resolveRefPathTarget(PSSParser::Ref_pathContext *ctx) {
    std::vector<std::string> path;
    bool is_global = false;

    if (ctx->static_ref_path()) {
        is_global = ctx->static_ref_path()->static_ref_path_prefix()->is_global;
        // Include the prefix element (first path segment before ::)
        if (!is_global && ctx->static_ref_path()->static_ref_path_prefix()->type_identifier_elem()) {
            path.push_back(ctx->static_ref_path()->static_ref_path_prefix()->type_identifier_elem()->identifier()->getText());
        }
        std::vector<PSSParser::Type_identifier_elemContext *> elems = ctx->static_ref_path()->type_identifier_elem();
        for (auto *e : elems) {
            path.push_back(e->identifier()->getText());
        }
        path.push_back(ctx->static_ref_path()->member_path_elem()->identifier()->getText());
        if (ctx->hierarchical_id()) {
            for (auto *e : ctx->hierarchical_id()->member_path_elem()) {
                path.push_back(e->identifier()->getText());
            }
        }
    } else {
        for (auto *e : ctx->hierarchical_id()->member_path_elem()) {
            path.push_back(e->identifier()->getText());
        }
    }

    if (path.empty()) {
        return 0;
    }

    return resolvePathTarget(scope(), path, is_global);
}

static bool appendHierarchicalIdPath(
        std::vector<std::string> &path,
        ast::IExprHierarchicalId *hier_id) {
    if (!hier_id) {
        return false;
    }

    for (std::vector<ast::IExprMemberPathElemUP>::const_iterator
        it=hier_id->getElems().begin();
        it!=hier_id->getElems().end(); it++) {
        if (!(*it)->getId() || (*it)->getParams() || (*it)->getSubscript().size()) {
            return false;
        }
        path.push_back((*it)->getId()->getId());
    }

    return !path.empty();
}

static bool appendStaticRefPath(
        std::vector<std::string> &path,
        ast::IExprRefPathStatic *ref) {
    if (!ref) {
        return false;
    }

    for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
        it=ref->getBase().begin();
        it!=ref->getBase().end(); it++) {
        if (!(*it)->getId() || (*it)->getParams()) {
            return false;
        }
        path.push_back((*it)->getId()->getId());
    }

    return !path.empty();
}

ast::IScopeChild *AstBuilderInt::resolveRefPathTarget(
        ast::IScope *eval_scope,
        ast::IExprRefPath *expr) {
    if (!expr) {
        return 0;
    }

    std::vector<std::string> path;
    bool is_global = false;
    ast::IScope *start_scope = eval_scope ? eval_scope : scope();

    if (ast::IExprRefPathStaticRooted *rooted = dynamic_cast<ast::IExprRefPathStaticRooted *>(expr)) {
        is_global = rooted->getRoot()->getIs_global();
        if (!appendStaticRefPath(path, rooted->getRoot()) || !appendHierarchicalIdPath(path, rooted->getLeaf())) {
            return 0;
        }
    } else if (ast::IExprRefPathStatic *static_ref = dynamic_cast<ast::IExprRefPathStatic *>(expr)) {
        is_global = static_ref->getIs_global();
        if (!appendStaticRefPath(path, static_ref)) {
            return 0;
        }
    } else if (ast::IExprRefPathContext *context_ref = dynamic_cast<ast::IExprRefPathContext *>(expr)) {
        if (context_ref->getIs_super() && start_scope) {
            start_scope = start_scope->getParent();
        }
        if (!appendHierarchicalIdPath(path, context_ref->getHier_id())) {
            return 0;
        }
    } else {
        return 0;
    }

    for (size_t pi=0; pi<path.size(); pi++) {
    }
    return resolvePathTarget(start_scope, path, is_global);
}

bool AstBuilderInt::evalEnumItemExpression(
        ast::IEnumDecl *decl,
        ast::IExpr *expr,
        int64_t &val) {
    if (!expr) return false;

    // Try standard eval first with the enclosing scope
    if (evalAstExpression(scope(), expr, val)) {
        return true;
    }

    // Handle binary expressions with enum item references
    if (ast::IExprBin *b = dynamic_cast<ast::IExprBin *>(expr)) {
        int64_t lhs = 0, rhs = 0;
        if (!evalEnumItemExpression(decl, b->getLhs(), lhs) ||
            !evalEnumItemExpression(decl, b->getRhs(), rhs)) {
            return false;
        }
        switch (b->getOp()) {
            case ast::ExprBinOp::BinOp_Add: val = lhs + rhs; return true;
            case ast::ExprBinOp::BinOp_Sub: val = lhs - rhs; return true;
            case ast::ExprBinOp::BinOp_Mul: val = lhs * rhs; return true;
            case ast::ExprBinOp::BinOp_Div: val = rhs ? (lhs / rhs) : 0; return true;
            case ast::ExprBinOp::BinOp_Mod: val = rhs ? (lhs % rhs) : 0; return true;
            case ast::ExprBinOp::BinOp_Shl: val = lhs << rhs; return true;
            case ast::ExprBinOp::BinOp_Shr: val = lhs >> rhs; return true;
            case ast::ExprBinOp::BinOp_BitAnd: val = lhs & rhs; return true;
            case ast::ExprBinOp::BinOp_BitOr: val = lhs | rhs; return true;
            case ast::ExprBinOp::BinOp_BitXor: val = lhs ^ rhs; return true;
            default: return false;
        }
    }

    // Check if the expression is a reference to another enum item
    if (ast::IExprRefPathContext *rp = dynamic_cast<ast::IExprRefPathContext *>(expr)) {
        if (rp->getHier_id() && rp->getHier_id()->getElems().size() == 1) {
            std::string name = rp->getHier_id()->getElems().at(0)->getId()->getId();
            for (auto &item : decl->getItems()) {
                if (item->getName() && item->getName()->getId() == name) {
                    if (item->getIndex() >= 0) {
                        val = item->getIndex();
                        return true;
                    }
                }
            }
        }
    }

    return false;
}

bool AstBuilderInt::evalScopeChildValue(ast::IScopeChild *target, int64_t &val) {
    if (ast::IField *f = dynamic_cast<ast::IField *>(target)) {
        if (f->getInit()) {
            return evalAstExpression(f->getParent(), f->getInit(), val);
        }
    } else if (ast::IEnumItem *e = dynamic_cast<ast::IEnumItem *>(target)) {
        // Prefer pre-computed index (set during enum declaration)
        if (e->getIndex() >= 0) {
            val = e->getIndex();
            return true;
        } else if (e->getValue()) {
            return evalAstExpression(e->getParent(), e->getValue(), val);
        }
    }
    return false;
}

bool AstBuilderInt::evalScopeChildValue(ast::IScopeChild *target, std::string &val) {
    if (ast::IField *f = dynamic_cast<ast::IField *>(target)) {
        if (f->getInit()) {
            return evalAstExpression(f->getParent(), f->getInit(), val);
        }
    }
    return false;
}

ast::IActivityJoinSpec *AstBuilderInt::mkActivityJoinSpec(PSSParser::Activity_join_specContext *ctx) {
	DEBUG_ENTER("mkActivityoinSpec");
	ast::IActivityJoinSpec *spec = 0;
	DEBUG("TODO: mkActivityJoinSpec");

	DEBUG_LEAVE("mkActivityoinSpec");
	return spec;
}

ast::IScopeChild *AstBuilderInt::mkActivityStmt(PSSParser::Activity_stmt_annContext *ctx) {
	DEBUG_ENTER("mkActivityStmt");
	m_activity_stmt = 0;
	ctx->accept(this);
	DEBUG_LEAVE("mkActivityStmt");
	return m_activity_stmt;
}

// Add a synthetic integer field to a scope's symtab and children vector.
// Used to register loop variables (repeat, foreach) so the name resolver can
// find them when resolving `with` constraint expressions inside loop bodies.
void AstBuilderInt::addSyntheticIntField(ast::ISymbolScope *scope, const std::string &name) {
    if (!scope || name.empty()) return;
    if (scope->getSymtab().find(name) != scope->getSymtab().end()) return; // already registered

    ast::IExprId *id = m_factory->mkExprId(name, false);
    ast::IField *field = m_factory->mkField(
        id,
        m_factory->mkDataTypeInt(
            false,
            m_factory->mkExprUnsignedNumber("32", 32, 32),
            nullptr),
        ast::FieldAttr::NoFlags,
        nullptr);
    int32_t idx = scope->getChildren().size();
    field->setIndex(idx);
    scope->getSymtab()[name] = idx;
    scope->getChildren().push_back(ast::IScopeChildUP(field, true));
}

// Inject the LRM built-in field for a state/resource struct (`initial`:bool /
// `instance_id`:int) so the name resolver can resolve references to it (e.g.
// `constraint initial -> ...`). Skips injection when the user already declares
// a field of that name. Field resolution for type members walks getChildren()
// (cf. the synthetic `comp` field added to actions), so no symtab entry is
// needed.
void AstBuilderInt::addStructBuiltinField(ast::IStruct *s, ast::StructKind kind) {
    const char *name;
    bool is_bool;
    if (kind == ast::StructKind::State) {
        name = "initial"; is_bool = true;
    } else if (kind == ast::StructKind::Resource) {
        name = "instance_id"; is_bool = false;
    } else {
        return;
    }

    for (auto &ch : s->getChildren()) {
        ast::IField *f = dynamic_cast<ast::IField *>(ch.get());
        if (f && f->getName() && f->getName()->getId() == name) {
            return; // user-declared; leave it alone
        }
    }

    ast::IDataType *type = is_bool
        ? (ast::IDataType *)m_factory->mkDataTypeBool()
        : (ast::IDataType *)m_factory->mkDataTypeInt(
            false, m_factory->mkExprUnsignedNumber("32", 32, 32), nullptr);
    ast::IField *field = m_factory->mkField(
        m_factory->mkExprId(name, false),
        type,
        ast::FieldAttr::NoFlags,
        nullptr);
    field->setIndex(s->getChildren().size());
    s->getChildren().push_back(ast::IScopeChildUP(field));
}

void AstBuilderInt::addActivityStmt(
        ast::ISymbolScope                   *scope,
        PSSParser::Activity_stmt_annContext *ctx) {
    ast::IScopeChild *a_stmt = mkActivityStmt(ctx);
    if (a_stmt) {
        int32_t idx = scope->getChildren().size();
        a_stmt->setIndex(idx);
        scope->getChildren().push_back(ast::IScopeChildUP(a_stmt));
        // NOTE: Labels (e.g. T1: do tx_data_a) are registered in the action's
        // synthetic type scope by TaskBuildSymbolTree::registerActivityLabels,
        // not here. Adding them to the immediate activity scope (parallel, etc.)
        // would build a corrupt symbol-path since activity scopes have getId()=-1.
    }
}

ast::IConstraintStmt *AstBuilderInt::mkConstraintSet(PSSParser::Constraint_setContext *ctx) {
	m_constraint = 0;
	ctx->accept(this);
	return m_constraint;
}

std::vector<ast::IGenericConstraintParam *> AstBuilderInt::mkGenericConstraintParams(
        PSSParser::Generic_constraint_paramsContext *ctx) {
    std::vector<ast::IGenericConstraintParam *> ret;

    if (!ctx) {
        return ret;
    }

    std::vector<PSSParser::Generic_constraint_paramContext *> params = ctx->generic_constraint_param();
    for (std::vector<PSSParser::Generic_constraint_paramContext *>::const_iterator
        it=params.begin();
        it!=params.end(); it++) {
        bool is_numeric = (*it)->generic_constraint_data_type()->is_numeric;
        ast::IDataType *type = 0;
        if (!is_numeric) {
            type = mkDataType((*it)->generic_constraint_data_type()->data_type());
        }
        ret.push_back(m_factory->mkGenericConstraintParam(
            mkId((*it)->identifier()),
            (*it)->is_const,
            is_numeric,
            type));
    }

    return ret;
}

ast::IDataType *AstBuilderInt::mkDataType(PSSParser::Data_typeContext *ctx) {
	m_type = 0;
	ctx->accept(this);
    if (!m_type) {
        DEBUG_ERROR("Internal Error: mkDataType returning null");
    }
	return m_type;
}

ast::IDataTypeUserDefined *AstBuilderInt::mkDataTypeUserDefined(PSSParser::Type_identifierContext *ctx) {
	DEBUG_ENTER("mkDataTypeUserDefined");
	// std::vector<PSSParser::Type_identifier_elemContext *> items = ctx->type_identifier_elem();

	// for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
	// 	it=items.begin();
	// 	it!=items.end(); it++) {
	// 	ret->getElems().push_back(ast::ITypeIdentifierElemUP(
	// 		m_factory->mkTypeIdentifierElem(mkId((*it)->identifier()))));
	// }

	ast::IDataTypeUserDefined *ret = m_factory->mkDataTypeUserDefined(
		ctx->is_global,
		mkTypeId(ctx));

    // Type-identifier location is the same as the first identifier element
    ret->setLocation(ret->getType_id()->getElems().front()->getId()->getLocation());

	DEBUG_LEAVE("mkDataTypeUserDefined");

	return ret;
}

/**
 * Wrap `elem_t` in one `array<>` per declared dimension.
 *
 * Dimensions are applied **right to left**: `A a[3][2]` denotes an array of 3
 * arrays of 2, so the rightmost dimension is the innermost wrap. §11.3.2
 * Example87 makes this observable -- given `A a_arr[3][2]`, `a_arr[1]` is a
 * sub-array of two handles, not an element.
 *
 * Applying them left to right builds the transposed type, which is wrong for
 * every non-square declaration and silently right for square ones.
 */
ast::IDataTypeUserDefined *AstBuilderInt::mkDataTypeArray(
        ast::IDataType          *elem_t,
        ast::IExpr              *size) {
    DEBUG_ENTER("mkDataTypeArray");
    ast::ITemplateParamValueList *params = m_factory->mkTemplateParamValueList();
    params->getValues().push_back(ast::ITemplateParamValueUP(
        m_factory->mkTemplateParamTypeValue(elem_t)
    ));
    params->getValues().push_back(ast::ITemplateParamValueUP(
        m_factory->mkTemplateParamExprValue(size)
    ));
    ast::ITypeIdentifierElem *array_e = m_factory->mkTypeIdentifierElem(
        m_factory->mkExprId("array", false),
        params);
    ast::ITypeIdentifier *array_t = m_factory->mkTypeIdentifier();
    array_t->getElems().push_back(ast::ITypeIdentifierElemUP(array_e));
    
	ast::IDataTypeUserDefined *ret = m_factory->mkDataTypeUserDefined(
		false,
        array_t);

    DEBUG_LEAVE("mkDataTypeArray");
    return ret;
}

ast::IExprDomainOpenRangeList *AstBuilderInt::mkDomainOpenRangeList(PSSParser::Domain_open_range_listContext *ctx) {
	DEBUG_ENTER("mkDomainOpenRangeList");
	ast::IExprDomainOpenRangeList *ret = m_factory->mkExprDomainOpenRangeList();
	std::vector<PSSParser::Domain_open_range_valueContext *> items =
		ctx->domain_open_range_value();
	
	for (std::vector<PSSParser::Domain_open_range_valueContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {

		ast::IExpr *lhs = 0;
		if ((*it)->lhs) {
			lhs = mkExpr((*it)->lhs);
		}

		ast::IExpr *rhs = 0;
		if ((*it)->rhs) {
			rhs = mkExpr((*it)->rhs);
		}

		ast::IExprDomainOpenRangeValue *value = m_factory->mkExprDomainOpenRangeValue(
			!((*it)->limit_high || (*it)->limit_mid || (*it)->limit_low),
			lhs,
			rhs
		);
		ret->getValues().push_back(ast::IExprDomainOpenRangeValueUP(value));
	}
	DEBUG_LEAVE("mkDomainOpenRangeList");
	return ret;
}

ast::IExprOpenRangeList *AstBuilderInt::mkOpenRangeList(PSSParser::Open_range_listContext *ctx) {
	DEBUG_ENTER("mkOpenRangeList");
	ast::IExprOpenRangeList *ret = m_factory->mkExprOpenRangeList();

	if (ctx) {
		std::vector<PSSParser::Open_range_valueContext *> items = ctx->open_range_value();
		for (auto *it : items) {
			ast::IExpr *lhs = it->lhs ? mkExpr(it->lhs) : nullptr;
			ast::IExpr *rhs = it->rhs ? mkExpr(it->rhs) : nullptr;
			ast::IExprOpenRangeValue *value = m_factory->mkExprOpenRangeValue(lhs, rhs);
			ret->getValues().push_back(ast::IExprOpenRangeValueUP(value));
		}
	}

	DEBUG_LEAVE("mkOpenRangeList");
	return ret;
}

ast::IScopeChild *AstBuilderInt::mkExecStmt(PSSParser::Procedural_stmtContext *ctx) {
    DEBUG_ENTER("mkExecStmt");
    m_exec_stmt = 0;
    m_exec_stmt_cnt = 0;

    if (!ctx) {
        // An `exec_stmt` that is not a `procedural_stmt` -- `super;` is the
        // only one the grammar admits. Callers used to hand the null straight
        // to ctx->TOK_SEMICOLON() below, which segfaulted the parser (plan
        // phase 1.2). Callers that can produce one handle it themselves; this
        // guard is for the rest, and for whatever the grammar grows next.
        DEBUG("Note: null procedural_stmt");
        DEBUG_LEAVE("mkExecStmt -- null ctx");
        return 0;
    }

    if (ctx->annotation()) {
        // An annotation applied to a statement (LRM 21.6.1, Example323).  It is
        // metadata, not a statement: visiting it makes it pending so it
        // attaches to the next element built in this scope, and it contributes
        // nothing to the exec body itself.
        ctx->accept(this);
        DEBUG_LEAVE("mkExecStmt -- annotation");
        return 0;
    }

    if (!ctx->TOK_SEMICOLON()) {
        ctx->accept(this);

        if (!m_exec_stmt_cnt) {
            DEBUG_ERROR("No exec stmt produced");
        }
    } else {
        // Null statement
        m_exec_stmt_cnt++;
    }

    // Every procedural statement is built through here, nested bodies
    // included, so this is the one place a statement's provenance can be
    // recorded. Neither the location nor the comments were carried before.
    if (m_exec_stmt) {
        Token *start = ctx->getStart();
        if (start && m_exec_stmt->getLocation().lineno < 0) {
            m_exec_stmt->setLocation({
                m_file_id,
                (int32_t)start->getLine(),
                (int32_t)start->getCharPositionInLine()+1
            });
        }
        if (m_collectDocStrings) {
            attachDocstring(m_exec_stmt, start);
        }
    }

    DEBUG_LEAVE("mkExecStmt %p", m_exec_stmt);
    return m_exec_stmt;
}

void AstBuilderInt::addExecStmt(PSSParser::Procedural_stmtContext *ctx) {
    DEBUG_ENTER("addExecStmt");
    ast::IScopeChild *stmt = mkExecStmt(ctx);

    if (stmt) {
        stmt->setIndex(m_exec_scope_s.back()->getChildren().size());
        m_exec_scope_s.back()->getChildren().push_back(ast::IScopeChildUP(stmt));
    }

    DEBUG_LEAVE("addExecStmt");
}

static std::map<std::string, ParamDir> param_dir_m = {
    { "input", ParamDir::ParamDir_In},
    { "output", ParamDir::ParamDir_Out},
    { "inout", ParamDir::ParamDir_InOut}
};
// B.13 `ref_type_category ::= action | monitor | component | object_kind`.
// `struct` is deliberately absent: it is a *plain* category, so `ref struct`
// is not legal 3.1 -- see plain_param_kind_m.
static std::map<std::string, FunctionParamDeclKind> ref_param_kind_m = {
    { "action", FunctionParamDeclKind::ParamKind_RefAction },
    { "monitor", FunctionParamDeclKind::ParamKind_RefMonitor },
    { "component", FunctionParamDeclKind::ParamKind_RefComponent },
    { "buffer", FunctionParamDeclKind::ParamKind_RefBuffer },
    { "stream", FunctionParamDeclKind::ParamKind_RefStream },
    { "state", FunctionParamDeclKind::ParamKind_RefState },
    { "resource", FunctionParamDeclKind::ParamKind_RefResource }
};

// B.13 `plain_type_category ::= struct | numeric`
static std::map<std::string, FunctionParamDeclKind> plain_param_kind_m = {
    { "struct", FunctionParamDeclKind::ParamKind_Struct },
    { "numeric", FunctionParamDeclKind::ParamKind_Numeric }
};

/**
 * Look `text` up in `m`, or return `dflt`.
 *
 * These maps were previously indexed with `m.find(k)->second`, which
 * dereferences `end()` when the key is absent. Adding a category to the
 * grammar without adding it here would then be undefined behaviour rather
 * than a wrong-but-visible value.
 */
static FunctionParamDeclKind lookupParamKind(
        const std::map<std::string, FunctionParamDeclKind> &m,
        const std::string                                  &text,
        FunctionParamDeclKind                               dflt) {
    std::map<std::string, FunctionParamDeclKind>::const_iterator it = m.find(text);
    return (it != m.end())?it->second:dflt;
}

ast::IFunctionPrototype *AstBuilderInt::mkFunctionPrototype(
    PSSParser::Function_prototypeContext *ctx,
    PSSParser::Platform_qualifierContext *plat,
    bool                                 is_pure) {
    DEBUG_ENTER("mkFunctionPrototype %s", toString(ctx->function_identifier()->identifier()).c_str());
    ast::IDataType *rtype = 0;

    if (ctx->function_return_type()->data_type()) {
        rtype = mkDataType(ctx->function_return_type()->data_type());
    }

    // `platform_qualifier ::= target [solve] | solve`, so the two are not
    // mutually exclusive -- `target solve function` sets both.
    bool is_target = plat && plat->TOK_TARGET();
    bool is_solve = plat && plat->TOK_SOLVE();

    ast::IFunctionPrototype *proto = m_factory->mkFunctionPrototype(
        mkId(ctx->function_identifier()->identifier()),
        rtype,
        is_target,
        is_solve);
    proto->setIs_pure(is_pure);

    // A prototype reached through FunctionDefinition::getProto() or
    // FunctionImportProto::getProto() is never handed to addChild -- the
    // wrapper is the scope child -- so without this it keeps the default
    // lineno of -1, which is the documented marker for a compiler-injected
    // node.  The prototypes built directly from m_factory (the injected
    // set_executor/set_default_executor pair) deliberately do not come
    // through here and so remain marked.
    setLoc(proto, ctx->start);

    std::vector<PSSParser::Function_parameterContext *> items =
        ctx->function_parameter_list_prototype()->function_parameter();
    for (std::vector<PSSParser::Function_parameterContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ast::IFunctionParamDecl *param = mkFunctionParamDecl(*it);

        proto->getParameters().push_back(ast::IFunctionParamDeclUP(param));
    }

    if (ctx->function_parameter_list_prototype()->is_varargs) {
        // Pick up the final parameter
        PSSParser::Varargs_parameterContext *va_p = ctx->function_parameter_list_prototype()->varargs_parameter();

        ParamDir dir = ParamDir::ParamDir_Default;
        FunctionParamDeclKind kind = FunctionParamDeclKind::ParamKind_DataType;
        ast::IDataType *type = 0;
        ast::IExpr *dflt = 0;

        // The four alternatives of `varargs_parameter` are siblings in the
        // grammar. They were nested: `is_type`, `is_ref` and `is_struct` were
        // all tested only *inside* an `is_ref` branch, so `type... args` and
        // `struct... args` fell through with no kind set at all and kept the
        // ParamKind_DataType default with a null type. This mirrors the flat
        // shape mkFunctionParamDecl() uses for a non-varargs parameter.
        if (va_p->data_type()) {
            type = mkDataType(va_p->data_type());
        } else if (va_p->is_type) {
            kind = FunctionParamDeclKind::ParamKind_Type;
        } else if (va_p->is_ref) {
            kind = lookupParamKind(
                ref_param_kind_m,
                va_p->ref_type_category()->getText(),
                FunctionParamDeclKind::ParamKind_RefStruct);
        } else if (va_p->plain_type_category()) {
            kind = lookupParamKind(
                plain_param_kind_m,
                va_p->plain_type_category()->getText(),
                FunctionParamDeclKind::ParamKind_Struct);
        }

        ast::IFunctionParamDecl *param = m_factory->mkFunctionParamDecl(
            kind,
            mkId(va_p->identifier()),
            type,
            dir,
            dflt);

        param->setIs_varargs(true);
        proto->getParameters().push_back(ast::IFunctionParamDeclUP(param));
    }

    DEBUG_LEAVE("mkFunctionPrototype");
    return proto;
}



ast::IFunctionParamDecl *AstBuilderInt::mkFunctionParamDecl(PSSParser::Function_parameterContext *ctx) {
    ast::IFunctionParamDecl *ret = 0;
    DEBUG_ENTER("mkFunctionParamDecl");
    ParamDir dir = ParamDir::ParamDir_Default;
    FunctionParamDeclKind kind = FunctionParamDeclKind::ParamKind_DataType;
    ast::IDataType *type = 0;
    ast::IExpr *dflt = 0;

    if (ctx->data_type()) {
        // Regular parameter with direction, type, etc
        if (ctx->function_parameter_dir()) {
            dir = param_dir_m.find(ctx->function_parameter_dir()->getText())->second;
        }
        type = mkDataType(ctx->data_type());

        if (ctx->constant_expression()) {
            dflt = mkExpr(ctx->constant_expression()->expression());
        }
    } else {
        // type, ref-category, parameter
        if (ctx->is_type) {
            kind = FunctionParamDeclKind::ParamKind_Type;
        } else if (ctx->is_ref) {
            kind = lookupParamKind(
                ref_param_kind_m,
                ctx->ref_type_category()->getText(),
                FunctionParamDeclKind::ParamKind_RefStruct);
        } else if (ctx->plain_type_category()) {
            kind = lookupParamKind(
                plain_param_kind_m,
                ctx->plain_type_category()->getText(),
                FunctionParamDeclKind::ParamKind_Struct);
        }
    }

    ret = m_factory->mkFunctionParamDecl(
        kind,
        mkId(ctx->identifier()),
        type,
        dir,
        dflt);
    attachDocstring(ret, ctx->start);

    DEBUG_LEAVE("mkFunctionParamDecl");
    return ret;
}

std::vector<ast::IActionFieldInitializer *> AstBuilderInt::mkActionFieldInitializers(
        PSSParser::Action_initializer_listContext *ctx) {
    std::vector<ast::IActionFieldInitializer *> ret;

    if (!ctx) {
        return ret;
    }

    std::vector<PSSParser::Action_initializerContext *> inits = ctx->action_initializer();
    for (std::vector<PSSParser::Action_initializerContext *>::const_iterator
        it=inits.begin();
        it!=inits.end(); it++) {
        ret.push_back(m_factory->mkActionFieldInitializer(
            mkHierarchicalId((*it)->hierarchical_id()),
            mkExpr((*it)->expression())));
    }

    return ret;
}

IExprId *AstBuilderInt::mkId(PSSParser::IdentifierContext *ctx) {
	IExprId *id;

	
	if (ctx->ESCAPED_ID()) {
		id = m_factory->mkExprId(
			unescapeId(ctx->ESCAPED_ID()->getText()), true);
	} else {
        DEBUG("mkId: %s", ctx->ID()->getText().c_str());
		id = m_factory->mkExprId(ctx->ID()->getText(), false);
	}

    Location loc;
    loc.fileid = m_file_id;
	loc.lineno = ctx->start->getLine();
	loc.linepos = ctx->start->getCharPositionInLine()+1;
    loc.extent = id->getId().size() + (id->getIs_escaped()?1:0);
	id->setLocation(loc);

    DEBUG("ID Loc: %d:%d:%d",
        id->getLocation().fileid,
        id->getLocation().lineno,
        id->getLocation().linepos);

	return id;
}

std::string AstBuilderInt::toString(PSSParser::IdentifierContext *ctx) {
    if (ctx) {
        if (ctx->ESCAPED_ID()) {
            return unescapeId(ctx->ESCAPED_ID()->getText());
        } else {
            return ctx->ID()->getText();
        }
    } else {
        return "<null>";
    }
}

ast::IExprHierarchicalId *AstBuilderInt::mkHierarchicalId(PSSParser::Hierarchical_idContext *ctx) {
	DEBUG_ENTER("mkHierarchicalId");
	ast::IExprHierarchicalId *ret = m_factory->mkExprHierarchicalId();
	std::vector<PSSParser::Member_path_elemContext *> items = ctx->member_path_elem();

	for (std::vector<PSSParser::Member_path_elemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        ret->getElems().push_back(ast::IExprMemberPathElemUP(mkMemberPathElem(*it)));
	}

	DEBUG_LEAVE("mkHierarchicalId");
	return ret;
}

ast::IExprHierarchicalId *AstBuilderInt::mkHierarchicalId(PSSParser::Member_path_elemContext *ctx) {
	DEBUG_ENTER("mkHierarchicalId(member_path_elem)");
	ast::IExprHierarchicalId *ret = m_factory->mkExprHierarchicalId();
    ret->getElems().push_back(ast::IExprMemberPathElemUP(mkMemberPathElem(ctx)));

	DEBUG_LEAVE("mkHierarchicalId(member_path_elem)");
	return ret;
}

ast::IExprHierarchicalId *AstBuilderInt::mkHierarchicalId(
        PSSParser::Static_ref_pathContext *root_ctx,
        PSSParser::Hierarchical_idContext *leaf_ctx) {
    DEBUG_ENTER("mkHierarchicalId(base_ctx, leaf_ctx)");
	ast::IExprHierarchicalId *ret = m_factory->mkExprHierarchicalId();
    ret->getElems().push_back(ast::IExprMemberPathElemUP(mkMemberPathElem(
        root_ctx->member_path_elem())));

	std::vector<PSSParser::Member_path_elemContext *> items = leaf_ctx->member_path_elem();

	for (std::vector<PSSParser::Member_path_elemContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
        ret->getElems().push_back(ast::IExprMemberPathElemUP(mkMemberPathElem(*it)));
	}

    DEBUG_LEAVE("mkHierarchicalId(base_ctx, leaf_ctx)");
    return ret;
}


ast::IExprMemberPathElem *AstBuilderInt::mkMemberPathElem(
    PSSParser::Member_path_elemContext *ctx) {
    ast::IExprId *id = 0;
    ast::IMethodParameterList *params = 0;
    ast::IExpr *subscript = 0;

    id = mkId(ctx->identifier());

    if (ctx->function_parameter_list()) {
        params = m_factory->mkMethodParameterList();
        std::vector<PSSParser::ExpressionContext *> plist =
            ctx->function_parameter_list()->expression();
        for (std::vector<PSSParser::ExpressionContext *>::const_iterator
            it=plist.begin();
            it!=plist.end(); it++) {
            params->getParameters().push_back(ast::IExprUP(mkExpr(*it)));
        }
    }

    ast::IExprMemberPathElem *elem = m_factory->mkExprMemberPathElem(
        id,
        params);

    if (ctx->member_path_elem_index().size()) {
        for (uint32_t i=0; i<ctx->member_path_elem_index().size(); i++) {
            auto idx_ctx = ctx->member_path_elem_index(i);

            if (idx_ctx->TOK_ELIPSIS()) {
                /*
                 * A slice, not an index. Which endpoint is present depends on
                 * the spelling:
                 *
                 *   [ a .. b ]   expression(0)=a  expression(1)=b
                 *   [ a .. ]     expression(0)=a  (no second expression)
                 *   [ .. b ]     expression(0)=b  -- the *upper* bound
                 *
                 * The third case is why the token position, not the expression
                 * index, decides: with a leading '..' the sole expression is
                 * the right-hand endpoint.
                 */
                // No setLoc: ast::Expr is a root class with no Location member
                // (only ScopeChild and ExprId carry one).
                ast::IExprSliceRange *slice = m_factory->mkExprSliceRange();

                bool leading_elipsis =
                    idx_ctx->TOK_ELIPSIS()->getSymbol()->getTokenIndex()
                        < idx_ctx->expression(0)->start->getTokenIndex();

                if (leading_elipsis) {
                    slice->setUpper(mkExpr(idx_ctx->expression(0)));
                } else {
                    slice->setLower(mkExpr(idx_ctx->expression(0)));
                    if (idx_ctx->expression().size() > 1) {
                        slice->setUpper(mkExpr(idx_ctx->expression(1)));
                    }
                }
                elem->getSubscript().push_back(ast::IExprUP(slice));
            } else {
                subscript = mkExpr(idx_ctx->expression(0));
                elem->getSubscript().push_back(ast::IExprUP(subscript));
            }
        }
    }

    return elem;
}

void AstBuilderInt::mkTypeId(
		std::vector<IExprIdUP>					&type_id,
		PSSParser::Type_identifierContext		*ctx) {
    DEBUG("FIXME: mkTypeId<type_id, ctxt>");
	for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
		it=ctx->type_identifier_elem().begin();
		it!=ctx->type_identifier_elem().end(); it++) {
//		type_id.push_back(IExprIdUP(mkId((*it)->identifier())));
	}
}

ast::ITypeIdentifier *AstBuilderInt::mkTypeId(
		PSSParser::Type_identifierContext		*ctx) {
    DEBUG_ENTER("mkTypeId");
	ast::ITypeIdentifier *ret = m_factory->mkTypeIdentifier();
	std::vector<PSSParser::Type_identifier_elemContext *> elems = ctx->type_identifier_elem();

	if (elems.size() == 0) {
		DEBUG_ERROR("Error: elems.size==0");
	}

	for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
		it=elems.begin();
		it!=elems.end(); it++) {
        ast::ITemplateParamValueList *params = 0;

        if ((*it)->template_param_value_list()) {
            DEBUG("Parameterized element");
            params = mkTemplateParamValueList((*it)->template_param_value_list());
        }

		ast::ITypeIdentifierElem *elem = m_factory->mkTypeIdentifierElem(
			mkId((*it)->identifier()),
            params);

        DEBUG("elem \"%s\"", elem->getId()->getId().c_str());

		// TODO: handle parameterized types
		
		ret->getElems().push_back(ast::ITypeIdentifierElemUP(elem));
	}

    DEBUG_LEAVE("mkTypeId");
	return ret;
}

ast::ITypeIdentifierElem *AstBuilderInt::mkTypeIdElem(
		PSSParser::Type_identifier_elemContext		*ctx) {
	ast::ITypeIdentifierElem *elem = m_factory->mkTypeIdentifierElem(
			mkId(ctx->identifier()),
            (ctx->template_param_value_list())?mkTemplateParamValueList(
                ctx->template_param_value_list()):0
            );
    return elem;
}

ast::ITypeIdentifierElem *AstBuilderInt::mkTypeIdElem(
		PSSParser::IdentifierContext		*ctx) {
	ast::ITypeIdentifierElem *elem = m_factory->mkTypeIdentifierElem(
			mkId(ctx),
            0);
    return elem;
}

ast::IExpr *AstBuilderInt::mkExpr(
		PSSParser::ExpressionContext 			*ctx) {
	m_expr = 0;
	ctx->accept(this);
	return m_expr;
}

ast::IExprBitSlice *AstBuilderInt::mkExprBitSlice(
        PSSParser::Bit_sliceContext             *ctx) {
    ast::IExprBitSlice *ret = m_factory->mkExprBitSlice(
        mkExpr(ctx->constant_expression(0)->expression()),
        mkExpr(ctx->constant_expression(0)->expression())
    );

    return ret;
}

ast::IExprRefPath *AstBuilderInt::mkExprRefPath(
        PSSParser::Ref_pathContext              *ctx) {
    DEBUG_ENTER("mkExprRefPath");
    ast::IExprRefPath *ret = 0;
    if (ctx->static_ref_path()) {
        DEBUG("static_ref_path: ");

        if (ctx->hierarchical_id()) {
            DEBUG("hierarchical_id: ");
            // Has a context portion
            ast::IExprRefPathStatic *static_ref = mkExprRefPathStatic(ctx->static_ref_path());
            ast::IExprHierarchicalId *context_ref = mkHierarchicalId(
                ctx->static_ref_path(),
                ctx->hierarchical_id());

            DEBUG("mkExprRefPath: static_ref=%p context_ref=%p\n", static_ref, context_ref);
            ast::IExprRefPathStaticRooted *ref = m_factory->mkExprRefPathStaticRooted(
                static_ref,
                context_ref);

            if (ctx->bit_slice()) {
                ref->setSlice(mkExprBitSlice(ctx->bit_slice()));
            }

            ret = ref;
        } else { // Does not have a hierarchical_id component
            /*
             * ref_path:
             *   static_ref_path ( TOK_DOT hierarchical_id )? bit_slice?     // <-- We're here
             *   | (is_super=TOK_SUPER TOK_DOT)? hierarchical_id bit_slice?
             * 
             * static_ref_path:
             *   static_ref_path_prefix (type_identifier_elem TOK_DOUBLE_COLON )* member_path_elem
             * 
             * static_ref_path_prefix:
             *   (type_identifier_elem TOK_DOUBLE_COLON)
             *   | is_global=TOK_DOUBLE_COLON
             * 
             * member_path_elem:
             * 	identifier function_parameter_list? ( TOK_LSBRACE expression TOK_RSBRACE )?
             */

            DEBUG("!hierarchical_id: ");
            std::vector<PSSParser::Type_identifier_elemContext *> items =
                ctx->static_ref_path()->type_identifier_elem();
            if (!ctx->static_ref_path()->static_ref_path_prefix()->is_global && items.size() == 0 && 
                !ctx->static_ref_path()->member_path_elem()->function_parameter_list()) {
                DEBUG("case1");
                // static_ref_path_prefix member_path_elem
                DEBUG("Non-function static reference");
                ast::IExprRefPathStatic *ref = m_factory->mkExprRefPathStatic(false);
                ref->getBase().push_back(ast::ITypeIdentifierElemUP(
                    mkTypeIdElem(ctx->static_ref_path()->static_ref_path_prefix()->type_identifier_elem())
                ));
                ref->getBase().push_back(ast::ITypeIdentifierElemUP(
                    mkTypeIdElem(ctx->static_ref_path()->member_path_elem()->identifier())
                ));

                if (ctx->bit_slice()) {
                    ref->setSlice(mkExprBitSlice(ctx->bit_slice()));
                }

                ret = ref;
            } else {
                DEBUG("case2 (multi-element path) size=%d", items.size());
                // static_ref_path_prefix type_identifier_elem+ member_path_elem

                ast::IExprRefPathStatic *ref = m_factory->mkExprRefPathStatic(
                    ctx->static_ref_path()->static_ref_path_prefix()->is_global
                );

                if (!ctx->static_ref_path()->static_ref_path_prefix()->is_global) {
                    DEBUG("Add root elem");
                    ref->getBase().push_back(ast::ITypeIdentifierElemUP(
                        mkTypeIdElem(ctx->static_ref_path()->static_ref_path_prefix()->type_identifier_elem())));
                }

                for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
                    it=items.begin();
                    it!=items.end(); it++) {
                    ref->getBase().push_back(ast::ITypeIdentifierElemUP(mkTypeIdElem(*it)));
                }

                if (ctx->static_ref_path()->member_path_elem()->function_parameter_list()) {
                    // Last element is a function call. Use ExprStaticRooted to express
                    ast::IExprRefPathStaticRooted *expr = m_factory->mkExprRefPathStaticRooted(
                        ref,
                        mkHierarchicalId(ctx->static_ref_path()->member_path_elem())
                    );
                    ret = expr;
                } else {
                    // Last element is a field/constant reference
                    ref->getBase().push_back(ast::ITypeIdentifierElemUP(
                        mkTypeIdElem(ctx->static_ref_path()->member_path_elem()->identifier())));
                    ret = ref;
                }

                if (ctx->bit_slice()) {
                    DEBUG_ERROR("Revisit handling of bit_slice");
                    ref->setSlice(mkExprBitSlice(ctx->bit_slice()));
                }
            }
        }

    } else { // Does not have a static_ref_path prefix
        // Context ref
        DEBUG("!static_ref_path: ExprRefPathContext");
        ast::IExprRefPathContext *cref = m_factory->mkExprRefPathContext(
            mkHierarchicalId(ctx->hierarchical_id())
        );

        if (ctx->bit_slice()) {
            cref->setSlice(mkExprBitSlice(ctx->bit_slice()));
        }

        ret = cref;
    }

    DEBUG_LEAVE("mkExprRefPath");
    return ret;
}

ast::IExprRefPathStatic *AstBuilderInt::mkExprRefPathStatic(
        PSSParser::Static_ref_pathContext       *ctx) {
    IExprRefPathStatic *ret = 0;

    ret = m_factory->mkExprRefPathStatic(ctx->static_ref_path_prefix()->is_global);

    // The prefix element is part of the path, and was being dropped:
    //
    //   static_ref_path: static_ref_path_prefix
    //                    (type_identifier_elem TOK_DOUBLE_COLON)*
    //                    member_path_elem
    //   static_ref_path_prefix: (type_identifier_elem TOK_DOUBLE_COLON)
    //                         | is_global=TOK_DOUBLE_COLON
    //
    // For `p::f.x` the prefix holds `p` and `type_identifier_elem()` is
    // *empty*, so building the base from the latter alone produced a static
    // root with no elements at all. visitExprRefPathStatic then walked a base
    // of size zero, left the target null, and visitExprRefPathStaticRooted
    // returned at its "failed root resolution" branch -- silently. Every
    // qualified path with a member suffix (`p::f().x`, `p::S.field`) linked
    // clean no matter what it named, including a call with the wrong number
    // of arguments.
    //
    // The other builder of this shape -- the "case2" branch of mkExprRefPath
    // -- has always pushed the prefix explicitly, which is why `p::f(1,2)`
    // *was* checked and `p::f(1,2).x` was not.
    if (!ctx->static_ref_path_prefix()->is_global) {
        ret->getBase().push_back(ast::ITypeIdentifierElemUP(
            mkTypeIdElem(ctx->static_ref_path_prefix()->type_identifier_elem())));
    }

    std::vector<PSSParser::Type_identifier_elemContext *> items =
        ctx->type_identifier_elem();
    for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ret->getBase().push_back(ast::ITypeIdentifierElemUP(mkTypeIdElem(*it)));
    }

    return ret;
}

/**
 * Give a template parameter declaration the location of its own name.
 *
 * The declarations were built without one, so every diagnostic that pointed at
 * a parameter -- "duplicate parameter name 'T'" among them -- was reported at
 * <unknown>:-1:0. The name carries a usable location already; the declaration
 * simply never took it.
 */
static void setDeclLocation(ast::ITemplateParamDecl *p) {
    if (p && p->getName()) {
        p->setLocation(p->getName()->getLocation());
    }
}

// Every alternative of the `type_category` grammar rule must appear here.
// `buffer` did not: the lookup below dereferenced end() and read whatever the
// map's header node happened to contain, so `struct S<buffer T>` bound the
// parameter to a garbage category. It went unnoticed only because nothing
// read the category back -- see TaskBuildParamValList::checkCategoryArg,
// which now does.
static std::map<std::string, ast::TypeCategory> type_category_m = {
    {"action", ast::TypeCategory::Action },
    {"monitor", ast::TypeCategory::Monitor },
    {"component", ast::TypeCategory::Component },
    {"buffer", ast::TypeCategory::Buffer },
    {"resource", ast::TypeCategory::Resource },
    {"state", ast::TypeCategory::State },
    {"stream", ast::TypeCategory::Stream },
    {"struct", ast::TypeCategory::Struct },
    {"numeric", ast::TypeCategory::Numeric }
};

ast::ITemplateParamDeclList *AstBuilderInt::mkTypeParamDecl(
        PSSParser::Template_param_decl_listContext *ctx) {
    DEBUG_ENTER("mkTypeParamDecl");
    ast::ITemplateParamDeclList *plist = m_factory->mkTemplateParamDeclList();
    std::vector<PSSParser::Template_param_declContext *> items = ctx->template_param_decl();
    for (std::vector<PSSParser::Template_param_declContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        if ((*it)->type_param_decl()) {
            // Type parameter
            if ((*it)->type_param_decl()->generic_type_param_decl()) {
                ast::ITemplateGenericTypeParamDecl *gen_p = m_factory->mkTemplateGenericTypeParamDecl(
                    mkId((*it)->type_param_decl()->generic_type_param_decl()->identifier()),
                    ((*it)->type_param_decl()->generic_type_param_decl()->data_type())?
                        mkDataType((*it)->type_param_decl()->generic_type_param_decl()->data_type()):0
                );
                setDeclLocation(gen_p);
                attachDocstring(gen_p, (*it)->start);
                plist->getParams().push_back(ast::ITemplateParamDeclUP(gen_p));
            } else { // Type-category parameter
                PSSParser::Category_type_param_declContext *cat_ctx = (*it)->type_param_decl()->category_type_param_decl();
                std::map<std::string, ast::TypeCategory>::const_iterator cat_it =
                    type_category_m.find(cat_ctx->type_category()->getText());
                // A category the map does not know is a gap between the
                // grammar and this table, not a user error; default to the
                // most permissive reading rather than dereferencing end().
                ast::TypeCategory category = (cat_it != type_category_m.end())
                    ?cat_it->second:ast::TypeCategory::Struct;
                ast::IDataType *dflt = 0;

                if ((*it)->type_param_decl()->category_type_param_decl()->type_identifier()) {
                    dflt = m_factory->mkDataTypeUserDefined(
                        false, 
                        mkTypeId((*it)->type_param_decl()->category_type_param_decl()->type_identifier())
                    );
                }

                ast::ITemplateCategoryTypeParamDecl *cat_p = m_factory->mkTemplateCategoryTypeParamDecl(
                    mkId((*it)->type_param_decl()->category_type_param_decl()->identifier()),
                    category,
                    ((*it)->type_param_decl()->category_type_param_decl()->type_restriction())?
                        mkTypeId((*it)->type_param_decl()->category_type_param_decl()->type_restriction()->type_identifier()):0,
                    dflt
                );
                setDeclLocation(cat_p);
                attachDocstring(cat_p, (*it)->start);
                plist->getParams().push_back(ast::ITemplateParamDeclUP(cat_p));
            }
        } else {
            // Value parameter
            ast::ITemplateValueParamDecl *val_p = m_factory->mkTemplateValueParamDecl(
                mkId((*it)->value_param_decl()->identifier()),
                mkDataType((*it)->value_param_decl()->data_type()),
                ((*it)->value_param_decl()->constant_expression())?
                    mkExpr((*it)->value_param_decl()->constant_expression()->expression()):0
            );
            setDeclLocation(val_p);
            attachDocstring(val_p, (*it)->start);
            plist->getParams().push_back(ast::ITemplateParamDeclUP(val_p));
        }
    }

    DEBUG_LEAVE("mkTypeParamDecl");
    return plist;
}

ast::ITemplateParamValueList *AstBuilderInt::mkTemplateParamValueList(
        PSSParser::Template_param_value_listContext *ctx) {
    ast::ITemplateParamValueList *plist = m_factory->mkTemplateParamValueList();

    std::vector<PSSParser::Template_param_valueContext *> items;
    items = ctx->template_param_value();
    for (std::vector<PSSParser::Template_param_valueContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        if ((*it)->constant_expression()) {
            plist->getValues().push_back(ast::ITemplateParamValueUP(
                m_factory->mkTemplateParamExprValue(
                    mkExpr((*it)->constant_expression()->expression())
                )));
        } else {
            // Data type
            plist->getValues().push_back(ast::ITemplateParamValueUP(
                m_factory->mkTemplateParamTypeValue(
                    mkDataType((*it)->data_type())
                )));
        }
    }

    return plist;

}

void AstBuilderInt::setLoc(ast::IScopeChild *c, Token *start) {
    Location loc;
    loc.fileid = m_file_id;
    loc.lineno = (int32_t)start->getLine();
    loc.linepos = (int32_t)start->getCharPositionInLine()+1;
    // A no-op outside a template fragment sub-parse (§4.7.1).
    rebaseLoc(loc.lineno, loc.linepos);
	c->setLocation(loc);
}

void AstBuilderInt::setLoc(ast::IExprId *c, Token *start) {
    Location loc;
    loc.fileid = m_file_id;
    loc.lineno = (int32_t)start->getLine();
    loc.linepos = (int32_t)start->getCharPositionInLine()+1;
    rebaseLoc(loc.lineno, loc.linepos);
	c->setLocation(loc);
}

dmgr::IDebug *AstBuilderInt::m_dbg = 0;

}
