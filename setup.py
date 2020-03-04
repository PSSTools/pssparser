
import os
from setuptools import setup

setup(
  name = "pssparser",
  packages=['pssparser','pssparser-gen'],
  package_dir = {'' : 'src', '' : 'src-gen'},
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

