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
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IScope.h"

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
			ast::IGlobalScope	*global,
			std::istream 		*in);

    virtual void syntaxError(
    		Recognizer *recognizer,
			Token * offendingSymbol,
			size_t line,
			size_t charPositionInLine,
			const std::string &msg,
			std::exception_ptr e) override;

private:
    void addChild(ast::IScopeChild *c, Token *t);

    void addChild(ast::INamedScopeChild *c, Token *t);

    void addChild(ast::INamedScope *c, Token *t);

    void addDocstring(ast::IScopeChild *c, Token *t);

    std::string processDocStringMultiLineComment(
    		const std::vector<Token *>		&mlc_tokens,
			const std::vector<Token *>		&ws_tokens);

    std::string processDocStringSingleLineComment(
    		const std::vector<Token *>		&slc_tokens,
			const std::vector<Token *>		&ws_tokens);

    ast::IScope *scope() const { return m_scopes.back(); }

    void push_scope(ast::IScope *s) { m_scopes.push_back(s); }

    void pop_scope() { m_scopes.pop_back(); }

private:
    IMarkerListener						*m_marker_l;
    std::vector<ast::IScope *>			m_scopes;
    std::unique_ptr<CommonTokenStream>	m_tokens;

};

}

