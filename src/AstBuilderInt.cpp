/*
 * AstBuilderInt.cpp
 *
 *  Created on: Sep 13, 2020
 *      Author: ballance
 */

#include "AstBuilderInt.h"
#include "PSSLexer.h"
#include "pssp/ast/IFactory.h"
#include "Action.h"
#include "Component.h"
#include "NamedScopeChild.h"
#include "ScopeUtil.h"

namespace pssp {

AstBuilderInt::AstBuilderInt(IMarkerListener *marker_l) : m_marker_l(marker_l) {
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
	if (!m_marker_l->hasSeverity(Severity_Error)) {
		push_scope(global);
		ctx->accept(this);
		pop_scope();
	}
}

void AstBuilderInt::syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) {
	if (m_marker_l) {
		m_marker_l->marker(Marker(
				msg,
				Severity_Error,
				Location(
						0,
						line,
						charPositionInLine)));
	}
}

void AstBuilderInt::addChild(ast::IScopeChild *c, Token *t) {
	ScopeUtil::addChild(scope(), c);
}

void AstBuilderInt::addChild(ast::INamedScopeChild *c, Token *t) {
	ScopeUtil::addChild(scope(), c);
}

void AstBuilderInt::addChild(ast::INamedScope *c, Token *t) {
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

}
