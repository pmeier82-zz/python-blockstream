##!/usr/bin/env python
## -*- coding: utf-8 -*-
################################################################################
#
# setup.py
#
# Philipp Meier - <pmeier82 at googlemail dot com>
# 2011-05-10
#


##---IMPORTS

import ez_setup

ez_setup.use_setuptools()
from setuptools import setup, find_packages

##---STINGS

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: Education',
    'Intended Audience :: Science/Research',
    'License :: Free for non-commercial use',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2.6',
    'Topic :: Scientific/Engineering :: Bio-Informatics'
]
DESCRIPTION = 'python bindings for the blockstream shared library'
LONG_DESCRIPTION = """%s

Python bindings to interface with the blockstream network package protocol.
The blockstream protocol implements a container type package, called a block,
that is used as a transport proxy for other more specific protocols. The
protocol lives in layer 5 and 6 of the OSI network model.
""" % DESCRIPTION

def get_version():
    rval = '0.0.0'
    with open('./blockstream/__init__.py', 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                rval = line.strip().split('=')[-1]
                break
    return rval.replace('\'', '').strip()

VERSION = get_version()

##---SETUP BLOCK

setup(
    # names and description
    name='Blockstream',
    version=VERSION,
    author='Philipp Meier',
    author_email='pmeier82@googlemail.com',
    maintainer='Philipp Meier',
    maintainer_email='pmeier82@googlemail.com',
    url='http://www.ni.tu-berlin.de/',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    # package distribution
    packages=['blockstream'],
    package_data={'':['*.dll', '*.so', '*.ini']},
    zip_safe=False,
    include_package_data=True,
    license='free for non-commercial use',
    classifiers=CLASSIFIERS,
    platforms=['any'],
    install_requires=[],
    )
