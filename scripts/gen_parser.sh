#!/bin/sh

antlr_jar_name=antlr-4.8-complete.jar
antlr_jar_url=https://www.antlr.org/download/${antlr_jar_name}

scripts_dir=`dirname $0`
project_dir=`dirname $scripts_dir`

mkdir -p ${project_dir}/packages
mkdir -p ${project_dir}/gen-src/pssparser-gen

antlr_jar=${project_dir}/packages/${antlr_jar_name}

if test ! -f ${antlr_jar}; then
  wget -O ${antlr_jar} ${antlr_jar_url}
fi

java -jar ${antlr_jar} -Dlanguage=Python3 -visitor \
  ${project_dir}/grammar/PSS.g4 -o ${project_dir}/gen-src

touch ${project_dir}/gen-src/pssparser-gen/__init__.py
cp ${project_dir}/gen-src/grammar/* ${project_dir}/gen-src/pssparser-gen
rm -rf ${project_dir}/gen-src/grammar
