
import os
from setuptools import setup, find_namespace_packages

version="0.0.1"

if "BUILD_NUM" in os.environ.keys():
    version += "." + os.environ["BUILD_NUM"]

setup(
  name = "pssparser",
  version = version,
  packages=find_namespace_packages(),
  package_dir = {'' : 'src'},
  author = "Matthew Ballance",
  author_email = "matt.ballance@gmail.com",
  description = ("pssparser provides an Accellera PSS parser implemented with ANTLR and Python"),
  license = "Apache 2.0",
  keywords = ["PSS", "Portable Stimulus", "Accellera"],
  url = "https://github.com/psstools/pssparser",
  entry_points={
    'console_scripts': [
      'pssparser = pssparser.__main__:main'
    ]
  },
  setup_requires=[
    'setuptools_scm',
    'setuptools-antlr'
  ],
  install_requires=[
    'antlr4-python3-runtime'
  ],
)

