/*
 * TestParseSpecExamples.h
 *
 *  Created on: Oct 17, 2020
 *      Author: ballance
 */
#pragma once
#include "gtest/gtest.h"

class TestParseSpecExamples : public ::testing::Test {
public:
	TestParseSpecExamples();

	virtual ~TestParseSpecExamples();

	void runTest(
		const std::string &content,
		const std::string &name);

};

