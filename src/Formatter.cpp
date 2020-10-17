/*
 * Formatter.cpp
 *
 *  Created on: Sep 26, 2020
 *      Author: ballance
 */

#include <stdio.h>
#include "Formatter.h"
#include "PSSLexer.h"
#include "PSSParser.h"

using namespace antlr4;

namespace pss {

Formatter::Formatter() {
	// TODO Auto-generated constructor stub

}

Formatter::~Formatter() {
	// TODO Auto-generated destructor stub
}

void Formatter::format(
			std::istream	*in,
			std::ostream	*out) {
    std::ifstream stream;
    stream.open("input.scene");

    ANTLRInputStream input(*in);
    PSSLexer lexer(&input);
    CommonTokenStream tokens(&lexer);
    PSSParser parser(&tokens);
    parser.addParseListener(this);
    parser.compilation_unit();
}

void Formatter::enterAction_declaration(PSSParser::Action_declarationContext *ctx) {
	fprintf(stdout, "enterAction_declaration %p %s\n",
			ctx->start,
			ctx->start->getText().c_str());
}

void Formatter::exitAction_declaration(PSSParser::Action_declarationContext *ctx) {
	fprintf(stdout, "exitAction_declaration %s\n", ctx->start->getText().c_str());
}

void Formatter::enterComponent_declaration(PSSParser::Component_declarationContext *ctx) {
	fprintf(stdout, "enterComponent_declaration %p %s\n",
			ctx->start,
			ctx->start->getText().c_str());
}

void Formatter::exitComponent_declaration(PSSParser::Component_declarationContext *ctx) {
	fprintf(stdout, "exitComponent_declaration %s\n", ctx->start->getText().c_str());
}

void Formatter::visitTerminal(antlr4::tree::TerminalNode *node) {
	fprintf(stdout, "visitTerminal: %p %s\n",
			node->getSymbol(),
			node->getText().c_str());

}

void Formatter::visitErrorNode(antlr4::tree::ErrorNode *node) {
	fprintf(stdout, "visitErrorNode: %s\n", node->getText().c_str());
}

}
