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
# Copyright (c) 2011 Philipp Meier, Felix Franke & Technische Universität
# Berlin
# Acknowledgement: This work was supported by Deutsche Forschungs Gemeinschaft
#                  (DFG) with grant GRK 1589/1 and Bundesministerium für
# Bildung
#                  und Forschung (BMBF) with grants 01GQ0743 and 01GQ0410.
#
#___________________________________________________________________________
# ___
#
# This is free software; you can redistribute it and/or modify it under the
# terms of version 1.1 of the EUPL, European Union Public Licence.
# The software is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS
# FOR A PARTICULAR PURPOSE. See the EUPL for more details.
#___________________________________________________________________________
# ___
#

"""protocol for the sorting results with respect to the bxpd protocol"""
__docformat__ = 'restructuredtext'
__all__ = [
    # protocol classes
    'BS3CoveBlockHeader',
    'BS3CoveBaseBlock',
    'BS3CoveDataBlock',
    'COVEProtocolHandler',
    ]

##---IMPORTS

from struct import pack, unpack
import scipy as sp
from blockstream import BS3BaseHeader, BS3BaseBlock
from bs_reader import ProtocolHandler

##---CLASSES

class BS3CoveBlockHeader(BS3BaseHeader):
    """header for a datablock of type COVE from the blockstream protocol"""

    version = 1
    signature = '<BB'

    def __init__(self, block_type):
        """
        :Parameters:
            block_type : uint8
                BT=0 -> only BT=0 for now
        """

        self.block_type = int(block_type)

    def payload(self):
        return pack(self.signature, self.version, self.block_type)

    def __str__(self):
        return '[$%s]' % self.block_type

    @staticmethod
    def from_data(data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        if len(data) < BS3CoveBlockHeader.__len__():
            raise ValueError(
                'data must have len >= %s' % BS3CoveBlockHeader.__len__())
        ver, btp = unpack(BS3CoveBlockHeader.signature,
                          data[:BS3CoveBlockHeader.__len__()])
        if ver != BS3CoveBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3CoveBlockHeader(btp)


class BS3CoveBaseBlock(BS3BaseBlock):
    """"Sort data block"""

    BLOCK_CODE = 'COVE'


class BS3CoveDataBlock(BS3CoveBaseBlock):
    """"COVE - datablock"""

    def __init__(self,
                 data_lst):
        """
        :Paramters:
            data_lst : list
                grp_idx::uint16,
                kind::char,
                nc::uint16,
                tf::uint16,
                xcorrs::[nc*nc * 2*tf-1]
                ncov::[tf*nc * tf*nc]
        """

        # super
        super(BS3CoveDataBlock, self).__init__(BS3CoveBlockHeader(0))

        # members
        self.data_lst = list(data_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()

        grp_idx, kind, nc, tf = self.data_lst[:4]
        rval += pack('<HcHH', grp_idx, kind, nc, tf)
        rval += self.data_lst[4].satype(sp.float32).tostring()
        rval += self.data_lst[5].astype(sp.float32).tostring()
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3CoveDataBlock, self).__str__()
        return '%s::[%d]' % (super_str, self.data_lst[0])

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # begin to build package
        grp_idx, kind, nc, tf = unpack('<HcHH', data[at:at + 7])
        data_lst = [grp_idx, kind, nc, tf]
        tf_nc = tf * nc
        at += 7

        xcoors = sp.frombuffer(data[at:at + (nc * nc * (tf * 2 - 1) * 4)],
                               dtype=sp.float32)
        xcoors.shape = (nc * nc, 2 * tf - 1)
        data_lst.append(xcoors)
        at += nc * nc * (tf * 2 - 1) * 4

        cov = sp.frombuffer(data[at:at + (tf_nc * tf_nc * 4)],
                            dtype=sp.float32)
        cov.shape = (tf_nc, tf_nc)
        data_lst.append(cov)

        return BS3CoveDataBlock(header, data_lst)


class COVEProtocolHandler(ProtocolHandler):
    def on_block_ready(self, block_header, block_data):
        if block_header.block_code == 'COVE':
            # handle our protocol
            at = BS3CoveBlockHeader.__len__()
            cove_header = BS3CoveBlockHeader.from_data(block_data[:at])
            cove_block = None
            if cove_header.block_type == 0:
                #data block
                cove_block = BS3CoveDataBlock.from_data(cove_header,
                                                        block_data[at:])
            else:
                print 'unknown block_code: %s::%s' % (
                    block_header, cove_header)
            return cove_block
        else:
            # other blocks -- what is wrong here?
            print 'received block for other protocol! %s' % block_header
            return None


def test_single(n=100):
    try:
        from Queue import Queue
        from bs_reader import BS3Reader

        Q = Queue()
        bs_reader = BS3Reader(COVEProtocolHandler, Q, verbose=True,
                              ident='TestCOVE')
        bs_reader.start()
        for _ in xrange(n):
            item = Q.get()
            print 'got item:', item
            test_visualize_block(item[1])
    except Exception, ex:
        print ex
    finally:
        bs_reader.stop()
        print 'exit!'


def test_visualize():
    indata = open("C:\\Dev\\blockstream_runtimes\\test_file1_res.cove",
                  'rb').read()
    bh = BS3CoveBlockHeader.from_data(indata[38:40])
    print bh.version, bh.block_type
    bk = BS3CoveDataBlock.from_data(bh, indata[40:])
    print bk.data_lst

    from plot import P

    P.matshow(bk.data_lst[-1])
    P.show()


def test_visualize_block(block):
    from plot import P

    P.matshow(block.data_lst[-2])
    P.matshow(block.data_lst[-1])
    P.show()

##---MAIN

if __name__ == '__main__':
    test_single()
