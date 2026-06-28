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
#include "Marker.h"

namespace pssp {



using namespace ast;

AstBuilderInt::AstBuilderInt(
    dmgr::IDebugMgr     *dmgr,
	ast::IFactory		*factory,
	IMarkerListener 	*marker_l) : m_factory(factory), m_marker_l(marker_l) {
    DEBUG_INIT("pssp::AstBuilderInt", dmgr);
	m_collectDocStrings = false;
    m_enableProfile = false;
	m_field_depth = 0;
	m_labeled_activity_id = 0;
	m_constraint = 0;

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
    m_profile_decisions.clear();

    uint64_t parse_s = time_ms();
	ANTLRInputStream input(*in);
	PSSLexer lexer(&input);
	m_tokens = std::unique_ptr<CommonTokenStream>(new CommonTokenStream(&lexer));
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
	}

    if (m_enableProfile) {
        // Extract and store the profiling data immediately while parser is still alive
        atn::ParseInfo info = parser.getParseInfo();
        m_profile_decisions = info.getDecisionInfo();
        
        // Log summary for debugging
        for (std::vector<atn::DecisionInfo>::const_iterator
            it=m_profile_decisions.begin();
            it!=m_profile_decisions.end(); it++) {
            if (it->ambiguities.size()) {
                DEBUG("Info: %s", it->toString().c_str());
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
    if (evalConstantExpression(ctx->cond, cond) && cond) {
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
    if (evalConstantExpression(ctx->cond, cond) && cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitAnnotation_attr_field(PSSParser::Annotation_attr_fieldContext *ctx) {
	DEBUG_ENTER("visitAnnotation_attr_field");

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

    if (ctx->annotation_parameter_list()) {
        if (ctx->annotation_parameter_list()->annotation_positional_parameter_list()) {
            std::vector<PSSParser::ExpressionContext *> exprs =
                ctx->annotation_parameter_list()->annotation_positional_parameter_list()->expression();
            for (std::vector<PSSParser::ExpressionContext *>::const_iterator
                it=exprs.begin();
                it!=exprs.end(); it++) {
                { ast::IAnnotationParam *param = m_factory->mkAnnotationParam(mkExpr(*it));
                annotation->getParameters().push_back(ast::IAnnotationParamUP(param)); }
            }
        } else if (ctx->annotation_parameter_list()->annotation_namemapped_parameter_list()) {
            std::vector<PSSParser::Annotation_namemapped_parameter_elemContext *> elems =
                ctx->annotation_parameter_list()->annotation_namemapped_parameter_list()->annotation_namemapped_parameter_elem();
            for (std::vector<PSSParser::Annotation_namemapped_parameter_elemContext *>::const_iterator
                it=elems.begin();
                it!=elems.end(); it++) {
                { ast::IAnnotationParam *param = m_factory->mkAnnotationParam(
                        mkExpr((*it)->expression()));
                    param->setName(mkId((*it)->identifier()));
                    annotation->getParameters().push_back(ast::IAnnotationParamUP(param)); }
            }
        } else if (ctx->annotation_parameter_list()->annotation_mixed_parameter_list()) {
            // Positional params first
            std::vector<PSSParser::ExpressionContext *> exprs =
                ctx->annotation_parameter_list()->annotation_mixed_parameter_list()->expression();
            for (auto *expr : exprs) {
                ast::IAnnotationParam *param = m_factory->mkAnnotationParam(mkExpr(expr));
                annotation->getParameters().push_back(ast::IAnnotationParamUP(param));
            }
            // Named params after
            std::vector<PSSParser::Annotation_namemapped_parameter_elemContext *> elems =
                ctx->annotation_parameter_list()->annotation_mixed_parameter_list()->annotation_namemapped_parameter_elem();
            for (auto *elem : elems) {
                ast::IAnnotationParam *param = m_factory->mkAnnotationParam(
                    mkExpr(elem->expression()));
                param->setName(mkId(elem->identifier()));
                annotation->getParameters().push_back(ast::IAnnotationParamUP(param));
            }
        }
    }

    m_pending_annotations.push_back(annotation);

    DEBUG_LEAVE("visitAnnotation");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitConst_field_declaration(PSSParser::Const_field_declarationContext *ctx) {
	DEBUG_ENTER("visitConst_field_declaration");

	m_field_depth++;
	ctx->data_declaration()->accept(this);
	m_field_depth--;

	if (!m_field_depth) {
		m_fields.clear();
	}

	for (std::vector<ast::IField *>::const_iterator
		it=m_fields.begin();
		it!=m_fields.end(); it++) {
		(*it)->setAttr((*it)->getAttr() | FieldAttr::Const);
	}

	DEBUG_LEAVE("visitConst_field_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitCompile_assert_stmt(PSSParser::Compile_assert_stmtContext *ctx) {
    int64_t cond = 0;
    if (!evalConstantExpression(ctx->cond, cond) || !cond) {
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
	ctx->action_declaration()->accept(this);
	ast::IAction *action = dynamic_cast<ast::IAction *>(scope()->getChildren().back().get());
	action->setIs_abstract(true);
    setLoc(action, ctx->start);
	DEBUG_LEAVE("visitAbstract_action_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitOverride_action_declaration(PSSParser::Override_action_declarationContext *ctx) {
    DEBUG_ENTER("visitOverride_action_declaration");

    // Map override action to IExtendType with Action kind.
    ast::ITypeIdentifier *target_id = m_factory->mkTypeIdentifier();
    target_id->getElems().push_back(ast::ITypeIdentifierElemUP(
        m_factory->mkTypeIdentifierElem(
            mkId(ctx->action_identifier()->identifier()), 0)));

    ast::IExtendType *ext = m_factory->mkExtendType(
        ast::ExtendTargetE::Action,
        target_id);
    setLoc(ext, ctx->start);

    addChild(ext, ctx->start, ctx->TOK_RCBRACE()->getSymbol());
    push_scope(ext);

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
    if (evalConstantExpression(ctx->cond, cond) && cond) {
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

		if ((*it)->array_dim()) {
		    ast::IExpr *array_dim = 0;
			array_dim = mkExpr((*it)->array_dim()->constant_expression()->expression());
            type = mkDataTypeArray(type, array_dim);
		}

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

		if ((*it)->array_dim()) {
		    ast::IExpr *array_dim = 0;
			array_dim = mkExpr((*it)->array_dim()->constant_expression()->expression());
            type = mkDataTypeArray(type, array_dim);
		}

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
            std::vector<PSSParser::Array_dimContext *> dims = (*it)->action_handle_array_instance()->array_dim();
            for (std::vector<PSSParser::Array_dimContext *>::reverse_iterator
                dim_it=dims.rbegin();
                dim_it!=dims.rend(); dim_it++) {
                type = mkDataTypeArray(
                    type,
                    mkExpr((*dim_it)->constant_expression()->expression()));
            }
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
    if (evalConstantExpression(ctx->cond, cond) && cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitMonitor_body_compile_if(PSSParser::Monitor_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    if (evalConstantExpression(ctx->constant_expression(), cond) && cond) {
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
    { "post_solve", ast::ExecKind::ExecKind_PostSolve }
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
            msg += "(body, header, declaration, run_start, run_end, init, init_down, init_up, pre_solve, post_solve)";

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
        addExecStmt((*it)->procedural_stmt());
    }
    m_exec_scope_s.pop_back();

    addChild(exec, ctx->start, ctx->TOK_RCBRACE()->getSymbol());

    DEBUG_LEAVE("visitExec_block");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitTarget_code_exec_block(PSSParser::Target_code_exec_blockContext *ctx) {
    DEBUG_ENTER("visitTarget_code_exec_block");
    DEBUG("TODO: visitTarget_code_exec_block");
    DEBUG_LEAVE("visitTarget_code_exec_block");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitTarget_file_exec_block(PSSParser::Target_file_exec_blockContext *ctx) {
    DEBUG_ENTER("visitTarget_file_exec_block");
    DEBUG("TODO: visitTarget_file_exec_block");
    DEBUG_LEAVE("visitTarget_file_exec_block");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitExec_super_stmt(PSSParser::Exec_super_stmtContext *ctx) {
    DEBUG_ENTER("visitExec_super_stmt");
    DEBUG("TODO: visitExec_super_stmt");
    DEBUG_LEAVE("visitExec_super_stmt");
    return 0;
}

// B.5 Functions
antlrcpp::Any AstBuilderInt::visitProcedural_function(PSSParser::Procedural_functionContext *ctx) {
    DEBUG_ENTER("visitProcedural_function");

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
        mkFunctionPrototype(ctx->function_prototype()),
        body,
        platqual
    );

    if (ctx->platform_qualifier()) {
        if (ctx->platform_qualifier()->TOK_TARGET()) {
            func->getProto()->setIs_target(true);
        } else {
            func->getProto()->setIs_solve(true);
        }
    }

    addChild(func, ctx->start);
    DEBUG_LEAVE("visitProcedural_function");
    return 0;
}

antlrcpp::Any AstBuilderInt::visitFunction_decl(PSSParser::Function_declContext *ctx) {
    DEBUG_ENTER("visitFunction_decl");
    ast::IFunctionPrototype *proto = mkFunctionPrototype(ctx->function_prototype());
    addChild(proto, ctx->start);
    DEBUG_LEAVE("visitFunction_decl");
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
            mkFunctionPrototype(ctx->function_prototype())
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

        body->setIndex(stmt->getChildren().size());

        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    } else if (ctx->is_repeat_while) {
        ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());
        body->setIndex(0);
        ast::IProceduralStmtRepeatWhile *stmt = m_factory->mkProceduralStmtRepeatWhile(
            body,
            mkExpr(ctx->expression()));
        m_exec_stmt = stmt;
        m_exec_stmt_cnt++;
    } else { // 'while'
        ast::IScopeChild *body = mkExecStmt(ctx->procedural_stmt());
        body->setIndex(0);
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

        if ((*it)->array_dim()) {
            ast::IExpr *array_dim = 0;
            array_dim = mkExpr((*it)->array_dim()->constant_expression()->expression());
            type = mkDataTypeArray(type, array_dim);
        }
        ast::IProceduralStmtDataDeclaration *decl = m_factory->mkProceduralStmtDataDeclaration(
            name,
            type,
            init);
        decl->setIndex(m_exec_scope_s.back()->getChildren().size());
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
    if (evalConstantExpression(ctx->cond, cond) && cond) {
        visitCompileIfItem(ctx->true_body);
    } else if (ctx->false_body) {
        visitCompileIfItem(ctx->false_body);
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitComponent_data_declaration(PSSParser::Component_data_declarationContext *ctx) {
    DEBUG_ENTER("visitComponent_data_declaration");

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
	ast::IExprRefPathContext *target = nullptr;

	// The foreach target is a simple field identifier (e.g. `count`). Use the
	// labeled `target=identifier` grammar token (not a general expression) so
	// the optional [idx_id] subscript is NOT consumed by expression parsing.
	{
		ast::IExprHierarchicalId *hid = m_factory->mkExprHierarchicalId();
		ast::IExprMemberPathElem *elem = m_factory->mkExprMemberPathElem(
			mkId(ctx->target), 0);
		hid->getElems().push_back(ast::IExprMemberPathElemUP(elem));
		target = m_factory->mkExprRefPathContext(hid);
	}

	ast::IScopeChild *body = mkActivityStmt(ctx->activity_stmt_ann());
	if (!body) {
		body = m_factory->mkActivitySequence("");
	}

	// Register iterator and index variables as synthetic fields in the body scope
	// so `with` constraints inside the loop body can reference them by name.
	if (auto *body_scope = dynamic_cast<ast::ISymbolScope*>(body)) {
		if (ctx->it_id)  addSyntheticIntField(body_scope, ctx->it_id->identifier()->getText());
		if (ctx->idx_id) addSyntheticIntField(body_scope, ctx->idx_id->identifier()->getText());
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

		if (!(*it)->array_dim().empty()) {
		    // Convert the type to array<type,expr> for each dimension
		    for (auto *dim : (*it)->array_dim()) {
		        ast::IExpr *array_dim = mkExpr(dim->constant_expression()->expression());
		        type = mkDataTypeArray(type, array_dim);
		    }
		}

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
            ctx->data_type()->start);

		if (m_field_depth > 0) {
			m_fields.push_back(field);
		}
	}
	DEBUG_LEAVE("visitData_declaration");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitAttr_field(PSSParser::Attr_fieldContext *ctx) {
	DEBUG_ENTER("visitAttr_field");

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

antlrcpp::Any AstBuilderInt::visitInteger_type(PSSParser::Integer_typeContext *ctx) {
	DEBUG_ENTER("visitInteger_type");

	ast::IExpr *width = 0;
	ast::IExprDomainOpenRangeList *in = 0;

	if (ctx->lhs) {
		width = mkExpr(ctx->lhs);
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

	ast::IExprId *name = 0;
	if (ctx->type_identifier() &&
		!ctx->type_identifier()->type_identifier_elem().empty()) {
		name = mkId(
			ctx->type_identifier()->type_identifier_elem(0)->identifier());
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

	DEBUG_LEAVE("visitConstraint_block (%d)", m_constraint_s.size());
	return 0;
}

antlrcpp::Any AstBuilderInt::visitConstraint_body_compile_if(PSSParser::Constraint_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    if (evalConstantExpression(ctx->constant_expression(), cond) && cond) {
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
	DEBUG_LEAVE("visitExpression_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitProcedural_compile_if(PSSParser::Procedural_compile_ifContext *ctx) {
    int64_t cond = 0;
    if (evalConstantExpression(ctx->constant_expression(), cond) && cond) {
        visitCompileIfItem(ctx->procedural_compile_if_stmt(0));
    } else if (ctx->procedural_compile_if_stmt().size() > 1) {
        visitCompileIfItem(ctx->procedural_compile_if_stmt(1));
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitCovergroup_body_compile_if(PSSParser::Covergroup_body_compile_ifContext *ctx) {
    int64_t cond = 0;
    if (evalConstantExpression(ctx->constant_expression(), cond) && cond) {
        visitCompileIfItem(ctx->covergroup_body_compile_if_item(0));
    } else if (ctx->covergroup_body_compile_if_item().size() > 1) {
        visitCompileIfItem(ctx->covergroup_body_compile_if_item(1));
    }
    return 0;
}

antlrcpp::Any AstBuilderInt::visitOverride_compile_if(PSSParser::Override_compile_ifContext *ctx) {
    int64_t cond = 0;
    if (evalConstantExpression(ctx->constant_expression(), cond) && cond) {
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
        } else {
            // No index is a bit odd, but put a placeholder in anyway
            symtab->getChildren().push_back(ast::IScopeChildUP(0));
        }
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

	DEBUG_LEAVE("visitImplication_constraint_item");
	return 0;
}

antlrcpp::Any AstBuilderInt::visitUnique_constraint_item(PSSParser::Unique_constraint_itemContext *ctx) {
	DEBUG_ENTER("visitUnique_constraint_item");
	ast::IConstraintStmtUnique *c = m_factory->mkConstraintStmtUnique();

	std::vector<PSSParser::Hierarchical_idContext *> items = 
		ctx->hierarchical_id_list()->hierarchical_id();
	
	for (std::vector<PSSParser::Hierarchical_idContext *>::const_iterator
		it=items.begin();
		it!=items.end(); it++) {
		ast::IExprHierarchicalId *hid = mkHierarchicalId(*it);
		c->getList().push_back(ast::IExprHierarchicalIdUP(hid));
	}

	if (m_constraint_s.size() > 0) {
		c->setIndex(m_constraint_s.back()->getConstraints().size());
		m_constraint_s.back()->getConstraints().push_back(ast::IConstraintStmtUP(c));
	}

	DEBUG_LEAVE("visitUnique_constraint_item");
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
		m_expr = m_factory->mkExprString(value, true);
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

antlrcpp::Any AstBuilderInt::visitIdentifier(PSSParser::IdentifierContext *ctx) {
	DEBUG_ENTER("visitIdentifier");
	IExprId *id;
	
	if (ctx->ESCAPED_ID()) {
		id = m_factory->mkExprId(ctx->ESCAPED_ID()->getText(), true);
	} else {
        DEBUG("visitIdentifier: %s", ctx->ID()->getText().c_str());
		id = m_factory->mkExprId(ctx->ID()->getText(), false);
	}

	Location loc;
	loc.lineno = ctx->start->getLine();
	loc.linepos = ctx->start->getCharPositionInLine()+1;
    loc.extent = id->getId().size();
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

antlrcpp::Any AstBuilderInt::visitNumber(PSSParser::NumberContext *ctx_t) {
	DEBUG_ENTER("visitNumber %s", ctx_t->getText().c_str());
    if (ctx_t->integer_number()) {
        PSSParser::Integer_numberContext *ctx = ctx_t->integer_number();
        uint64_t value;
        bool is_signed = false;
        int32_t width = 32;
        std::string img;
        if (ctx->based_hex_number()) {
            DEBUG("Based hex number");
            if (ctx->based_hex_number()->DEC_LITERAL()) {
                // Explicit width
                width = strtoul(
                    ctx->based_hex_number()->DEC_LITERAL()->getSymbol()->getText().c_str(), 0, 10);
            }
            img = ctx->based_hex_number()->BASED_HEX_LITERAL()->getSymbol()->getText();
            std::string val_t;
            is_signed = (img[1] == 's' || img[1] == 'S');

            for (uint32_t i=2+is_signed; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 16);
        } else if (ctx->based_oct_number()) {
            DEBUG("Based oct number");
            if (ctx->based_oct_number()->DEC_LITERAL()) {
                // Explicit width
                width = strtoul(
                    ctx->based_oct_number()->DEC_LITERAL()->getSymbol()->getText().c_str(), 0, 10);
            }
            img = ctx->based_oct_number()->BASED_OCT_LITERAL()->getSymbol()->getText();
            std::string val_t;
            is_signed = (img[1] == 's' || img[1] == 'S');

            for (uint32_t i=2+is_signed; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 8);
        } else if (ctx->based_dec_number()) {
            DEBUG("Based dec number");
            if (ctx->based_dec_number()->DEC_LITERAL()) {
                // Explicit width
                width = strtoul(
                    ctx->based_dec_number()->DEC_LITERAL()->getSymbol()->getText().c_str(), 0, 10);
            }
            img = ctx->based_dec_number()->BASED_DEC_LITERAL()->getSymbol()->getText();
            std::string val_t;
            is_signed = (img[1] == 's' || img[1] == 'S');

            for (uint32_t i=2+is_signed; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 10);
        } else if (ctx->based_bin_number()) {
            DEBUG("Based bin number");
            if (ctx->based_bin_number()->DEC_LITERAL()) {
                // Explicit width
                width = strtoul(
                    ctx->based_bin_number()->DEC_LITERAL()->getSymbol()->getText().c_str(), 0, 10);
            }
            img = ctx->based_bin_number()->BASED_BIN_LITERAL()->getSymbol()->getText();
            std::string val_t;
            is_signed = (img[1] == 's' || img[1] == 'S');

            for (uint32_t i=2+is_signed; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 2);
        } else if (ctx->hex_number()) {
            DEBUG("Unbased hex number");
            img = ctx->hex_number()->HEX_LITERAL()->getSymbol()->getText();
            std::string val_t;

            for (uint32_t i=2; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 16);
        } else if (ctx->dec_number()) {
            DEBUG("Unbased dec number");
            img = ctx->dec_number()->DEC_LITERAL()->getSymbol()->getText();
            std::string val_t;

            for (uint32_t i=0; i<img.size(); i++) {
                if (img.at(i) != '_') {
                    val_t.push_back(img.at(i));
                }
            }

            value = strtoull(val_t.c_str(), 0, 10);
        } else if (ctx->oct_number()) {
            DEBUG("Unbased oct number");
            img = ctx->oct_number()->OCT_LITERAL()->getSymbol()->getText();
            std::string val_t;

            if (img.size() > 1) {
                for (uint32_t i=1; i<img.size(); i++) {
                    if (img.at(i) != '_') {
                        val_t.push_back(img.at(i));
                    }
                }

                value = strtoull(val_t.c_str(), 0, 8);
            } else {
                value = 0;
            }
        } else {
            DEBUG_FATAL("Unknown format");
        }

        if (is_signed) {
    	    m_expr = m_factory->mkExprSignedNumber(img, width, value);
        } else {
    	    m_expr = m_factory->mkExprUnsignedNumber(img, width, value);
        }

    } else { // floating-point number
        PSSParser::Floating_point_numberContext *ctx = ctx_t->floating_point_number();
        DEBUG_ERROR("handle floating-point number");
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

static std::string rewriteSyntaxError(const std::string &msg, const std::string &sym) {
    if (sym == "<EOF>") {
        return "unexpected end of input; possible missing closing '}'";
    }
    if (msg.find("missing {ID, ESCAPED_ID}") != std::string::npos) {
        return "expected identifier before '" + sym + "'";
    }
    if (msg.find("mismatched input") != std::string::npos) {
        if (msg.find("expecting {',', ';'}") != std::string::npos ||
            msg.find("expecting ';'") != std::string::npos) {
            return "expected ';' before '" + sym + "'";
        }
        if (msg.find("expecting {'{', ':', '<'}") != std::string::npos ||
            msg.find("expecting {'{', ':'}") != std::string::npos) {
            std::string hint;
            if (sym == "extends") {
                hint = "; use ':' for inheritance, not 'extends'";
            }
            return "expected '{' or ':' before '" + sym + "'" + hint;
        }
        std::string expecting = msg.substr(msg.find("expecting"));
        if (expecting.size() > 60) {
            return "unexpected '" + sym + "' in this context";
        }
        return "unexpected '" + sym + "' " + expecting;
    }
    if (msg.find("extraneous input") != std::string::npos) {
        if (sym.size() == 1 && !isalpha(sym[0])) {
            return "unexpected '" + sym + "' in this context";
        } else {
            return "unexpected keyword '" + sym + "' in this context";
        }
    }
    if (msg.find("no viable alternative") != std::string::npos) {
        return "syntax error at '" + sym + "'";
    }
    return msg;
}

void AstBuilderInt::syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) {
	DEBUG_ERROR("Error: Syntax error: line=%d pos=%d sym=%s",
        (int)line, (int)charPositionInLine, offendingSymbol->getText().c_str());
	if (m_marker_l) {
		ast::Location loc;
		loc.fileid = m_file_id;
		loc.lineno = line;
		loc.linepos = charPositionInLine;
        loc.extent = offendingSymbol->getText().size();

		std::string rewritten = rewriteSyntaxError(msg, offendingSymbol->getText());

		Marker m(
				rewritten,
				MarkerSeverityE::Error,
				loc);
		m_marker_l->marker(&m);
	}
}

void AstBuilderInt::addChild(ast::IScopeChild *c, Token *t, const ast::Location *loc, Token *ct) {
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

	if (m_collectDocStrings && (t || ct)) {
		addDocstring(c, (ct)?ct:t);
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
    // c->setEndLocation({
    //     m_file_id,
    //     (int32_t)end->getLine(),
    //     (int32_t)end->getCharPositionInLine()+1
    // });

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
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
		addDocstring(c, t);
	}
}

void AstBuilderInt::addChild(ast::IConstraintScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    c->setEndLocation({
        m_file_id,
        (int32_t)end->getLine(),
        (int32_t)end->getCharPositionInLine()+1
    });
	c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
	}
}

void AstBuilderInt::addChild(ast::IExecScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    c->setEndLocation({
        m_file_id,
        (int32_t)end->getLine(),
        (int32_t)end->getCharPositionInLine()+1
    });
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
	}
}

void AstBuilderInt::addChild(ast::IFunctionDefinition *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    c->setEndLocation({
        m_file_id,
        (int32_t)end->getLine(),
        (int32_t)end->getCharPositionInLine()+1
    });
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
	}
}

void AstBuilderInt::addChild(ast::INamedScope *c, Token *start, Token *end) {
    DEBUG_ENTER("addChild (INamedScope) %s %p %p", c->getName()->getId().c_str(), start, end);
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()+1
    });
    c->setEndLocation({
        m_file_id,
        (int32_t)end->getLine(),
        (int32_t)end->getCharPositionInLine()+1
    });
    c->setParent(scope());
    attachPendingAnnotations(c);
    DEBUG("Parent: %p", c->getParent());
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
	}
    DEBUG_LEAVE("addChild (INamedScope) %p %p", start, end);
}

void AstBuilderInt::addChild(ast::IScope *c, Token *start, Token *end) {
    c->setLocation({
        m_file_id,
        (int32_t)start->getLine(),
        (int32_t)start->getCharPositionInLine()
    });
    c->setEndLocation({
        m_file_id,
        (int32_t)end->getLine(),
        (int32_t)end->getCharPositionInLine()
    });
    c->setParent(scope());
    attachPendingAnnotations(c);
    c->setIndex(scope()->getChildren().size());
	scope()->getChildren().push_back(ast::IScopeChildUP(c));

	if (m_collectDocStrings && start) {
		addDocstring(c, start);
	}
}

void AstBuilderInt::addDocstring(ast::IScopeChild *c, Token *t) {
	DEBUG_ENTER("addDocstring");
	std::vector<Token *> ws_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 10);
	std::vector<Token *> slc_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 11);
	std::vector<Token *> mlc_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 12);

	DEBUG("ws_tokens=%d slc_tokens=%d mlc_tokens=%d",
			ws_tokens.size(), slc_tokens.size(), mlc_tokens.size());

	if (slc_tokens.size() == 0 && mlc_tokens.size() == 0) {
		return;
	}

	int32_t last_ws_line = -1;
	if (ws_tokens.size() > 0) {
		last_ws_line = ws_tokens.back()->getLine();
	}

	std::string docstring;
	if (slc_tokens.size() > 0 && mlc_tokens.size() > 0) {
		if (slc_tokens.back()->getLine() > mlc_tokens.back()->getLine()) {
			// Single-line comment is last
			docstring = processDocStringSingleLineComment(
					slc_tokens,
					ws_tokens);
		} else {
			// Multi-line comment is last
			docstring = processDocStringMultiLineComment(
					mlc_tokens,
					ws_tokens);
		}
	} else if (slc_tokens.size() > 0) {
		// Single-line comment
		docstring = processDocStringSingleLineComment(
				slc_tokens,
				ws_tokens);
	} else {
		// Multi-line comment
		docstring = processDocStringMultiLineComment(
				mlc_tokens,
				ws_tokens);
	}

	DEBUG("docstring=%s", docstring.c_str());
	if (docstring != "") {
		c->setDocstring(docstring);
	}

	/*
	fprintf(stdout, "Token pos: %d\n", comp->getLine());
	for (std::vector<Token*>::const_iterator
			it=tokens.begin();
			it!=tokens.end(); it++) {
		fprintf(stdout, "Token %d: %s\n",
				(*it)->getLine(),
				(*it)->getText().c_str());
	}
	 */
	DEBUG_LEAVE("addDocstring");
}

void AstBuilderInt::attachPendingAnnotations(ast::IScopeChild *c) {
    if (!m_pending_annotations.empty()) {
        for (std::vector<ast::IAnnotation *>::const_iterator
            it=m_pending_annotations.begin();
            it!=m_pending_annotations.end(); it++) {
            c->getAnnotations().push_back(ast::IAnnotationUP(*it));
        }
        m_pending_annotations.clear();
    }
}

std::string AstBuilderInt::processDocStringMultiLineComment(
    		const std::vector<Token *>		&mlc_tokens,
			const std::vector<Token *>		&ws_tokens) {
	int32_t last_ws_line = -1;
	if (ws_tokens.size() > 0) {
		last_ws_line = ws_tokens.back()->getLine();
	}

	std::string comment;
	if (last_ws_line < 0 || last_ws_line < mlc_tokens.back()->getLine()) {
//		fprintf(stdout, "OK: no whitespace between element and comment\n");
	} else if (last_ws_line >= 0) {
//		fprintf(stdout, "TODO: check if whitespace exceeds a limit\n");

		// Find the extent of the comment
		uint32_t comment_last_line = mlc_tokens.back()->getLine();
		comment = mlc_tokens.back()->getText();
		std::string ws = ws_tokens.back()->getText();
		int32_t i=0;
		while (i < comment.size() &&
				(i=comment.find('\n', i)) != std::string::npos) {
			comment_last_line++;
			i++;
		}

		i=0;
		while (i < comment.size() &&
				(i=ws.find('\n', i)) != std::string::npos) {
			last_ws_line++;
			i++;
		}
/*
		fprintf(stdout, "Comment last line: %d\n", comment_last_line);
		fprintf(stdout, "Whitespace last line: %d\n", last_ws_line);
 */

		if (last_ws_line <= (comment_last_line+2)) {
//			fprintf(stdout, "Note: Have a doc comment\n");

			// TODO: now we need to clean up the comment
			//

			// Trim off the beginning and end of the comment
			comment = comment.substr(2,comment.size()-4);

//			fprintf(stdout, "Comment: %s\n", comment.c_str());
			// Step through the lines looking for a '*' prefix
			i=0;
			while (i<comment.size()) {
				if (comment.at(i) == '*') {
					comment.erase(i, 1);
//					fprintf(stdout, "Post-remove(1): %s\n", comment.c_str());
				} else if ((i+1<comment.size()) &&
						(isspace(comment.at(i)) && comment.at(i+1) == '*')) {
					comment.erase(i, 2);
//					fprintf(stdout, "Post-remove(2): %s\n", comment.c_str());
				}
				if ((i=comment.find('\n',i)) != std::string::npos) {
					i++;
				} else {
					break;
				}
			}
		} else {
//			fprintf(stdout, "Note: False alarm\n");
			comment.clear();
		}
	}

	return comment;
}

std::string AstBuilderInt::processDocStringSingleLineComment(
    		const std::vector<Token *>		&slc_tokens,
			const std::vector<Token *>		&ws_tokens) {
    std::string comment;

    for (std::vector<Token *>::const_iterator
        it=slc_tokens.begin();
        it!=slc_tokens.end(); it++) {
        comment += (*it)->getText().substr(2);
    }

	return comment;
}

void AstBuilderInt::push_scope(ast::IScope *s) { 
	DEBUG("-- push_scope");
	m_scopes.push_back(s); 
}

void AstBuilderInt::pop_scope() { 
	DEBUG("-- pop_scope");
    if (!m_pending_annotations.empty()) {
        DEBUG("Discarding %d pending annotations at scope pop",
            (int)m_pending_annotations.size());
        for (std::vector<ast::IAnnotation *>::const_iterator
            it=m_pending_annotations.begin();
            it!=m_pending_annotations.end(); it++) {
            delete *it;
        }
        m_pending_annotations.clear();
    }
	m_scopes.pop_back(); 
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
            std::string norm;
            for (char c : txt) {
                if (c != '_') norm.push_back(c);
            }
            if (norm.rfind("0x", 0) == 0 || norm.rfind("0X", 0) == 0) {
                val = strtoll(norm.c_str()+2, 0, 16);
            } else if (norm.size() > 1 && norm[0] == '0') {
                val = strtoll(norm.c_str()+1, 0, 8);
            } else {
                val = strtoll(norm.c_str(), 0, 10);
            }
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

    if (!ctx->TOK_SEMICOLON()) {
        ctx->accept(this);

        if (!m_exec_stmt_cnt) {
            DEBUG_ERROR("No exec stmt produced");
        }
    } else {
        // Null statement
        m_exec_stmt_cnt++;
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
static std::map<std::string, FunctionParamDeclKind> ref_param_kind_m = {
    { "action", FunctionParamDeclKind::ParamKind_RefAction },
    { "component", FunctionParamDeclKind::ParamKind_RefComponent },
    { "struct", FunctionParamDeclKind::ParamKind_RefStruct },
    { "buffer", FunctionParamDeclKind::ParamKind_RefBuffer },
    { "stream", FunctionParamDeclKind::ParamKind_RefStream },
    { "state", FunctionParamDeclKind::ParamKind_RefState },
    { "resource", FunctionParamDeclKind::ParamKind_RefResource }
};

ast::IFunctionPrototype *AstBuilderInt::mkFunctionPrototype(
    PSSParser::Function_prototypeContext *ctx) {
    DEBUG_ENTER("mkFunctionPrototype %s", toString(ctx->function_identifier()->identifier()).c_str());
    ast::IDataType *rtype = 0;

    if (ctx->function_return_type()->data_type()) {
        rtype = mkDataType(ctx->function_return_type()->data_type());
    }

    bool is_target = false;
    bool is_solve = false;

    ast::IFunctionPrototype *proto = m_factory->mkFunctionPrototype(
        mkId(ctx->function_identifier()->identifier()),
        rtype,
        is_target,
        is_solve);

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

        if (va_p->data_type()) {
            type = mkDataType(va_p->data_type());
        } else if (va_p->is_ref) {
            if (va_p->is_type) {
                kind = FunctionParamDeclKind::ParamKind_Type;
            } else if (va_p->is_ref) {
                kind = ref_param_kind_m.find(va_p->type_category()->getText())->second;
            } else if (va_p->is_struct) {
                kind = FunctionParamDeclKind::ParamKind_Struct;
            } else {
                // TODO: should not occur
            }
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
            kind = ref_param_kind_m.find(ctx->type_category()->getText())->second;
        } else if (ctx->is_struct) {
            kind = FunctionParamDeclKind::ParamKind_Struct;
        } else {
            // TODO: should not occur
        }
    }

    ret = m_factory->mkFunctionParamDecl(
        kind,
        mkId(ctx->identifier()),
        type,
        dir,
        dflt);

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
		id = m_factory->mkExprId(ctx->ESCAPED_ID()->getText(), true);
	} else {
        DEBUG("mkId: %s", ctx->ID()->getText().c_str());
		id = m_factory->mkExprId(ctx->ID()->getText(), false);
	}

    Location loc;
    loc.fileid = m_file_id;
	loc.lineno = ctx->start->getLine();
	loc.linepos = ctx->start->getCharPositionInLine()+1;
    loc.extent = id->getId().size();
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
            return ctx->ESCAPED_ID()->getText();
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
            // For now, just handle the first expression (index or start of range)
            // TODO: Handle substring range with ELIPSIS
            subscript = mkExpr(idx_ctx->expression(0));
            elem->getSubscript().push_back(ast::IExprUP(subscript));
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

    std::vector<PSSParser::Type_identifier_elemContext *> items =
        ctx->type_identifier_elem();
    for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
        it=items.begin();
        it!=items.end(); it++) {
        ret->getBase().push_back(ast::ITypeIdentifierElemUP(mkTypeIdElem(*it)));
    }

    return ret;
}

static std::map<std::string, ast::TypeCategory> type_category_m = {
    {"action", ast::TypeCategory::Action },
    {"component", ast::TypeCategory::Component },
    {"resource", ast::TypeCategory::Resource },
    {"state", ast::TypeCategory::State },
    {"stream", ast::TypeCategory::Stream },
    {"struct", ast::TypeCategory::Struct }
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
                plist->getParams().push_back(ast::ITemplateParamDeclUP(gen_p));
            } else { // Type-category parameter
                PSSParser::Category_type_param_declContext *cat_ctx = (*it)->type_param_decl()->category_type_param_decl();
                ast::TypeCategory category = type_category_m.find(cat_ctx->type_category()->getText())->second;
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
	c->setLocation(loc);
}

void AstBuilderInt::setLoc(ast::IExprId *c, Token *start) {
    Location loc;
    loc.fileid = m_file_id;
    loc.lineno = (int32_t)start->getLine();
    loc.linepos = (int32_t)start->getCharPositionInLine()+1;
	c->setLocation(loc);
}

dmgr::IDebug *AstBuilderInt::m_dbg = 0;

}
