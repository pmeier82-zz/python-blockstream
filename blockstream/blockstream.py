# -*- coding: utf-8 -*-
# This file is part of the package SpikePy that provides signal processing
# algorithms tailored towards spike sorting. 
#
# Authors: Philipp Meier and Felix Franke
# Affiliation:
#   Bernstein Center for Computational Neuroscience (BCCN) Berlin
#     and
#   Neural Information Processing Group
#   School for Electrical Engineering and Computer Science
#   Berlin Institute of Technology
#   FR 2-1, Franklinstrasse 28/29, 10587 Berlin, Germany
#   Tel: +49-30-314 26756
#
# Date: 2011-02-25
# Copyright (c) 2011 Philipp Meier, Felix Franke & Technische Universität Berlin
# Acknowledgement: This work was supported by Deutsche Forschungs Gemeinschaft
#                  (DFG) with grant GRK 1589/1 and Bundesministerium für Bildung
#                  und Forschung (BMBF) with grants 01GQ0743 and 01GQ0410.
#
#______________________________________________________________________________
#
# This is free software; you can redistribute it and/or modify it under the
# terms of version 1.1 of the EUPL, European Union Public Licence.
# The software is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the EUPL for more details.
#______________________________________________________________________________
#

"""test dll loading and ctype stuff"""
__docformat__ = 'restructuredtext'


##---ALL

__all__ = [
    # library loading
    'load_lib',
    'load_blockstream',
    # protocoll classes
    'BS3Error',
    'BS3BaseHeader',
    'BS3DataBlockHeader'
]


##---IMPORTS

from ctypes import CDLL
from ctypes.util import find_library
import os
from struct import pack, unpack, calcsize
import platform


##---CONSTANTS

LIBNAME = 'libBlockStream.so'
if platform.system() == 'Windows':
    LIBNAME = 'BlockStream.dll'


##---FUNCTIONS

def load_lib(libname, verbose=False):

    if verbose:
        print 'libname:', libname
        print 'find_library("%s"):' % libname, find_library(libname)
    target_dir = os.path.dirname(__file__)
    if os.getcwd() != target_dir:
        os.chdir(target_dir)
    rval = CDLL(find_library(LIBNAME))
    if verbose:
        print rval
    return rval

def load_blockstream_lib(verbose=False):

    return load_lib(LIBNAME, verbose=verbose)


##---CLASSES

class BS3Error(Exception):
    pass

class BS3BaseHeader(object):
    """baseclass for blockstream protocol headers
    
    Subclasses should define the version and the binary signature as of the
    header as a class attribute. The version is an int, the signature is a str
    as explained in the `struct` package. Subclasses must implement the payload
    and from_data method.
    """

    version = 0
    signature = ''

    def payload(self):
        raise NotImplementedError

    @classmethod
    def __len__(cls):
        return calcsize(cls.signature)

    @staticmethod
    def from_data(data):
        raise NotImplementedError


class BS3DataBlockHeader(BS3BaseHeader):
    """header for a generic datablock from the blockstream protocol
    
    Only used when receiving packages! The datapackages are formed by the
    blockstream libray internally.
    """

    version = 3
    signature = '<BIHHQqB4sQ'

    type_code = 1
    header_size = 31

    def __init__(self,
                 block_size=31,
                 writer_id=0,
                 block_index=0,
                 time_stamp=0,
                 block_code='NONE'):
        """
        :Paramters:
            block_size : uint32 = 31
            writer_id : uint16 = 0
            block_index : uint64 = 0
            time_stamp : int64 = 0
            block_code : char[4] = 'NONE'
        """

        self.block_size = int(block_size)
        self.writer_id = int(writer_id)
        self.block_index = int(block_index)
        self.time_stamp = int(time_stamp)
        self.block_code = str(block_code)

    def payload(self):
        """return the binary data str"""

        return pack(self.signature,
                    self.version,
                    self.block_size,
                    self.header_size,
                    self.writer_id,
                    self.block_index,
                    self.time_stamp,
                    self.block_code,
                    0)

    def __str__(self):
        return 'BS3(#%s~@%s~[%s])' % (self.block_size,
                                      self.writer_id,
                                      self.block_code)

    @staticmethod
    def from_data(data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        if len(data) < BS3DataBlockHeader.__len__():
            raise ValueError('data must have len >= %s' % BS3DataBlockHeader.__len__())
        ver, bsz, hsz, wid, bix, tsp, tcd, bcd, xxx = unpack(BS3DataBlockHeader.signature,
                                                             data[:BS3DataBlockHeader.__len__()])
        if ver != BS3DataBlockHeader.version or tcd != 1:
            raise ValueError('invalid protocol version(%s) or blocktype(%s)!' % (ver, tcd))
        return BS3DataBlockHeader(bsz, wid, bix, tsp, bcd)
