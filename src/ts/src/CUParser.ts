
import {ANTLRInputStream, CommonTokenStream } from 'antlr4ts';
import {PSSParser} from './antlr_gen/PSSParser';
import {PSSLexer} from './antlr_gen/PSSLexer';

let inputStream = new ANTLRInputStream("");
let lexer = new PSSLexer(inputStream);
let tokenStream = new CommonTokenStream(lexer);
let parser = new PSSParser(tokenStream);

let root = parser.compilation_unit();

console.log("Parse complete")

export declare class CUParser {

}