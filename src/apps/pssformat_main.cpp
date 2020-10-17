/*
 * pssformat_main.cpp
 *
 *  Created on: Sep 26, 2020
 *      Author: ballance
 */
#include <stdio.h>
#include <iostream>
#include <fstream>
#include "Formatter.h"

int main(int argc, char **argv) {
	fprintf(stdout, "Hello World\n");

	std::fstream in;

	in.open(argv[1], std::fstream::in|std::fstream::binary);

	if (!in.is_open()) {
		exit(1);
	}

	pss::Formatter f;



	f.format(
			&in,
			&std::cout);

	in.close();
}


