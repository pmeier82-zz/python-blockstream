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
#
# This is free software; you can redistribute it and/or modify it under the
# terms of version 1.1 of the EUPL, European Union Public Licence.
# The software is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS
# FOR A PARTICULAR PURPOSE. See the EUPL for more details.
#___________________________________________________________________________
#

"""protocol for the waveforms"""
__docformat__ = 'restructuredtext'
__all__ = ['BS3WaveBlockHeader', 'BS3WaveBaseBlock', 'BS3WaveDataBlock',
           'WAVEProtocolHandler']

##---IMPORTS

from struct import pack, unpack
import scipy as sp
from blockstream import BS3BaseHeader, BS3BaseBlock
from bs_reader import ProtocolHandler

##---CLASSES

class BS3WaveBlockHeader(BS3BaseHeader):
    """header for a datablock of type SORT from the blockstream protocol"""

    version = 1
    signature = '<BB'

    def __init__(self, block_type):
        """
        :Parameters:
            block_type : uint8
                BT=0 -> setup block; BT=1 -> data block
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
        if len(data) < BS3WaveBlockHeader.__len__():
            raise ValueError(
                'data must have len >= %s' % BS3WaveBlockHeader.__len__())
        ver, btp = unpack(BS3WaveBlockHeader.signature,
                          data[:BS3WaveBlockHeader.__len__()])
        if ver != BS3WaveBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3WaveBlockHeader(btp)


class BS3WaveBaseBlock(BS3BaseBlock):
    """"Sort data block"""

    BLOCK_CODE = 'WAVE'


class BS3WaveDataBlock(BS3WaveBaseBlock):
    """"WAVE - datablock"""

    def __init__(self, event_lst, header=None):
        """
        :Paramters:
            event_lst : list
                list of waveform data entry:
                    group_idx::uint16,
                    unit_idx::uint32,
                    time_val::uint64,
                    nC::uint16,
                    nS::uint16,
                    samples::uint16[nS*nC]
            header : BS3WaveBlockHeader
        """

        # super
        super(BS3WaveDataBlock, self).__init__(
            header or BS3WaveBlockHeader(0))

        # members
        self.event_lst = list(event_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<I', len(self.event_lst))
        if len(self.event_lst) > 0:
            for ev in self.event_lst:
                rval += pack('<HIQHH', ev[:-1])
                rval += ev[-1].T.astype(sp.float32).tostring()
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3WaveDataBlock, self).__str__()
        return '%s::[ev:%d]' % (super_str, len(self.event_lst))

    @staticmethod
    def from_data(data, header=None):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # events
        event_lst = []
        nevent, = unpack('<I', data[at:at + 4])
        at += 4
        if nevent > 0:
            for _ in xrange(nevent):
                gid, uid, tv, nc, ns = unpack('<HIQHH', data[at:at + 18])
                at += 18
                wf = sp.frombuffer(
                    data[at:at + ns * nc * 2],
                    dtype=sp.int16
                ).reshape(nc, ns).T
                at += ns * nc * 2
                event_lst.append((gid, uid, tv, nc, ns, wf))
        return BS3WaveDataBlock(event_lst, header=header)

##---PROTOCOL

class WAVEProtocolHandler(ProtocolHandler):
    PROTOCOL = 'WAVE'

    def on_block_ready(self, block_header, block_data):
        if block_header.block_code == self.PROTOCOL:
            at = BS3WaveBlockHeader.__len__()
            prot_header = BS3WaveBlockHeader.from_data(block_data[:at])
            prot_block = None
            if prot_header.block_type == 0:
                prot_block = BS3WaveDataBlock.from_data(block_data[at:])
            else:
                print 'unknown block_code: %s::%s' % (
                    block_header, prot_header)
            return prot_block
        else:
            # other blocks -- what is wrong here?
            print 'received block for other protocol! %s' % block_header
            return None


PROT = {'H': BS3WaveBlockHeader,
        'B': BS3WaveBaseBlock,
        0: BS3WaveDataBlock, }

##---MAIN

if __name__ == '__main__':
    pass
