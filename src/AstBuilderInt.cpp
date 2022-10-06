/*
 * AstBuilderInt.cpp
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#include "AstBuilderInt.h"
#include "PSSLexer.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IAction.h"
#include "pssp/ast/IComponent.h"
#include "pssp/ast/IExprId.h"
#include "pssp/ast/INamedScope.h"
#include "pssp/ast/IPackageImportStmt.h"
#include "pssp/ast/Location.h"
#include "ScopeUtil.h"
#include "Marker.h"

namespace pssp {

using namespace ast;

AstBuilderInt::AstBuilderInt(
	ast::IFactory		*factory,
	IMarkerListener 	*marker_l) : m_factory(factory), m_marker_l(marker_l) {
	// TODO Auto-generated constructor stub

}

AstBuilderInt::~AstBuilderInt() {
	// TODO Auto-generated destructor stub
}

void AstBuilderInt::build(
			ast::IGlobalScope		*global,
			std::istream 			*in) {
	ANTLRInputStream input(*in);
	PSSLexer lexer(&input);
	m_tokens = std::unique_ptr<CommonTokenStream>(new CommonTokenStream(&lexer));
	PSSParser parser(m_tokens.get());

	parser.removeErrorListeners();
	parser.addErrorListener(this);

	PSSParser::Compilation_unitContext *ctx = parser.compilation_unit();

	// Only proceed to build out the AST if there are no syntax errors
	if (!m_marker_l->hasSeverity(MarkerSeverityE::Error)) {
		push_scope(global);
		ctx->accept(this);
		pop_scope();
	}
}

antlrcpp::Any AstBuilderInt::visitPackage_declaration(
	PSSParser::Package_declarationContext *ctx) {
	IPackageScope *pkg = m_factory->mkPackageScope();

	// TODO: populate Id list
	for (std::vector<PSSParser::Package_identifierContext *>::const_iterator
		it=ctx->package_id_path()->package_identifier().begin();
		it!=ctx->package_id_path()->package_identifier().end(); it++) {
		pkg->getId().push_back(IExprIdUP(mkId((*it)->identifier())));
	}

	addChild(pkg);
	push_scope(pkg);
	for (std::vector<PSSParser::Package_body_itemContext *>::const_iterator
		it=ctx->package_body_item().begin();
		it!=ctx->package_body_item().end(); it++) {
		(*it)->accept(this);
	}
	pop_scope();

	return 0;
}

antlrcpp::Any AstBuilderInt::visitImport_stmt(PSSParser::Import_stmtContext *ctx) {
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

	for (std::vector<PSSParser::Type_identifier_elemContext *>::const_iterator
		it=ctx->package_import_pattern()->type_identifier()->type_identifier_elem().begin();
		it!=ctx->package_import_pattern()->type_identifier()->type_identifier_elem().end(); it++) {
		imp->getPath().push_back(IExprIdUP(mkId((*it)->identifier())));
	}
	addChild(imp);


	return 0;
}

void AstBuilderInt::syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) {
	if (m_marker_l) {
		ast::Location loc;
		loc.fileid = 0;
		loc.lineno = line;
		loc.linepos = charPositionInLine;

		Marker m(
				msg,
				MarkerSeverityE::Error,
				loc);
		m_marker_l->marker(&m);
	}
}

void AstBuilderInt::addChild(ast::IScopeChild *c) {
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
//	ScopeUtil::addChild(scope(), c);
}

void AstBuilderInt::addChild(ast::INamedScopeChild *c) {
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
//	ScopeUtil::addChild(scope(), c);
}

void AstBuilderInt::addChild(ast::INamedScope *c) {
	scope()->getChildren().push_back(ast::IScopeChildUP(c));
}

void AstBuilderInt::addDocstring(ast::IScopeChild *c, Token *t) {
	std::vector<Token *> ws_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 10);
	std::vector<Token *> slc_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 11);
	std::vector<Token *> mlc_tokens = m_tokens->getHiddenTokensToLeft(
			t->getTokenIndex(), 12);

	fprintf(stdout, "ws_tokens=%d slc_tokens=%d mlc_tokens=%d\n",
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
}

std::string AstBuilderInt::processDocStringMultiLineComment(
    		const std::vector<Token *>		&mlc_tokens,
			const std::vector<Token *>		&ws_tokens) {
	int32_t last_ws_line = -1;
	if (ws_tokens.size() > 0) {
		last_ws_line = ws_tokens.back()->getLine();
	}

	fprintf(stdout, "last_ws_line=%d comment_line=%d\n",
			last_ws_line,
			mlc_tokens.back()->getLine());
	std::string comment;
	if (last_ws_line < 0 || last_ws_line < mlc_tokens.back()->getLine()) {
		fprintf(stdout, "OK: no whitespace between element and comment\n");
	} else if (last_ws_line >= 0) {
		fprintf(stdout, "TODO: check if whitespace exceeds a limit\n");

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

		fprintf(stdout, "Comment last line: %d\n", comment_last_line);
		fprintf(stdout, "Whitespace last line: %d\n", last_ws_line);

		if (last_ws_line <= (comment_last_line+2)) {
			fprintf(stdout, "Note: Have a doc comment\n");

			// TODO: now we need to clean up the comment
			//

			// Trim off the beginning and end of the comment
			comment = comment.substr(2,comment.size()-4);

			fprintf(stdout, "Comment: %s\n", comment.c_str());
			// Step through the lines looking for a '*' prefix
			i=0;
			while (i<comment.size()) {
				if (comment.at(i) == '*') {
					comment.erase(i, 1);
					fprintf(stdout, "Post-remove(1): %s\n", comment.c_str());
				} else if ((i+1<comment.size()) &&
						(isspace(comment.at(i)) && comment.at(i+1) == '*')) {
					comment.erase(i, 2);
					fprintf(stdout, "Post-remove(2): %s\n", comment.c_str());
				}
				if ((i=comment.find('\n',i)) != std::string::npos) {
					i++;
				} else {
					break;
				}
			}
		} else {
			fprintf(stdout, "Note: False alarm\n");
			comment.clear();
		}
	}

	return comment;
}

std::string AstBuilderInt::processDocStringSingleLineComment(
    		const std::vector<Token *>		&slc_tokens,
			const std::vector<Token *>		&ws_tokens) {
	return "";
}

IExprId *AstBuilderInt::mkId(PSSParser::IdentifierContext *ctx) {
	IExprId *id;
	
	if (ctx->ESCAPED_ID()) {
		id = m_factory->mkExprId(ctx->ESCAPED_ID()->toString(), true);
	} else {
		id = m_factory->mkExprId(ctx->ID()->toString(), false);
	}

	Location loc = id->getLocation();
	loc.lineno = ctx->start->getLine();
	loc.linepos = ctx->start->getCharPositionInLine();
	id->setLocation(loc);


	// TODO: Fill in location info

	return id;
}

}
