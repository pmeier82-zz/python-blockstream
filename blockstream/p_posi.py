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

"""protocol for the position information and steering of recoding devices"""
__docformat__ = 'restructuredtext'


##---ALL

__all__ = [
    # protocol classes
    'BS3PosiBlockHeader',
    'BS3PosiBaseBlock',
    'BS3PosiSetupBlock',
    'BS3PosiDataBlock',
]


##---IMPORTS

from struct import pack, unpack
from blockstream import BS3BaseHeader, BS3BaseBlock


##---CLASSES

class BS3PosiBlockHeader(BS3BaseHeader):
    """header for a datablock of type POSI from the blockstream protocol"""

    version = 1
    signature = '<BB'

    def __init__(self, block_type):
        """
        :Parameters:
            block_type : uint8
                BT=0 -> setup block; BT=1 -> info block; BT=2 -> steering block
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
        if len(data) < BS3PosiBlockHeader.__len__():
            raise ValueError('data must have len >= %s' % BS3PosiBlockHeader.__len__())
        ver, btp = unpack(BS3PosiBlockHeader.signature, data[:BS3PosiBlockHeader.__len__()])
        if ver != BS3PosiBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3PosiBlockHeader(btp)


class BS3PosiBaseBlock(BS3BaseBlock):
    """"Posi data block"""

    BLOCK_CODE = 'POSI'


class BS3PosiSetupBlock(BS3PosiBaseBlock):
    """"POSI - setupblock"""

    def __init__(self,
                 # header
                 header,
                 # setupblock stuff
                 group_lst):
        """
        :Paramters:
            header : BS3PosiBlockHeader
            
            group_lst : list
                list of group specs. entry:
                    grp_idx::uint16
        """

        # super
        super(BS3PosiSetupBlock, self).__init__(header)

        # members
        self.group_lst = list(group_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<H', len(self.group_lst))
        for group in self.group_lst:
            grp_idx, = group
            rval += pack('<H', grp_idx)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3PosiSetupBlock, self).__str__()
        return '%s::[gr:%d]' % (super_str, len(self.group_lst))

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # groups
        group_lst = []
        ngroup, = unpack('<H', data[at:at + 2])
        at += 2
        if ngroup > 0:
            for _ in xrange(ngroup):
                grp_idx, = unpack('<H', data[at:at + 2])
                at += 2
                group_lst.append((grp_idx,))
        return BS3PosiSetupBlock(header, group_lst)


class BS3PosiDataBlock(BS3PosiBaseBlock):
    """"POSI - datablock"""

    def __init__(self,
                 # header
                 header,
                 # datablock stuff
                 grp_lst):
        """
        :Paramters:
            header : BS3PosiBlockHeader
        
            grp_lst : list
                list of positions per group. entry:
                    (group_nr::uint16,
                     position::uint64)
        """

        # super
        super(BS3PosiDataBlock, self).__init__(header)

        # members
        self.grp_lst = list(grp_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<H', len(self.grp_lst))
        if len(self.grp_lst) > 0:
            for grp in self.grp_lst:
                rval += pack('<HQ', *grp)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3PosiDataBlock, self).__str__()
        return '%s::[ev:%d]' % (super_str, len(self.grp_lst))

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # events
        grp_lst = []
        ngrp, = unpack('<H', data[at:at + 2])
        at += 2
        if ngrp > 0:
            for _ in xrange(ngrp):
                grp = unpack('<HQ', data[at:at + 10])
                at += 10
                grp_lst.append(grp)
        return BS3PosiDataBlock(header, grp_lst)


class BS3PosiSteerBlock(BS3PosiBaseBlock):
    """"POSI - steeringblock"""

    def __init__(self,
                 # header
                 header,
                 # datablock stuff
                 grp_lst):
        """
        :Paramters:
            header : BS3PosiBlockHeader
        
            grp_lst : list
                list of positions per group. entry:
                    (group_nr::uint16,
                     position::uint64)
        """

        # super
        super(BS3PosiDataBlock, self).__init__(header)

        # members
        self.grp_lst = list(grp_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<H', len(self.grp_lst))
        if len(self.grp_lst) > 0:
            for grp in self.grp_lst:
                rval += pack('<HQ', *grp)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3PosiDataBlock, self).__str__()
        return '%s::[ev:%d]' % (super_str, len(self.grp_lst))

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # events
        grp_lst = []
        ngrp, = unpack('<H', data[at:at + 2])
        at += 2
        if ngrp > 0:
            for _ in xrange(ngrp):
                grp = unpack('<HQ', data[at:at + 10])
                at += 10
                grp_lst.append(grp)
        return BS3PosiDataBlock(header, grp_lst)


##---PROTOCOL

PROT = {
    'H' : BS3PosiBlockHeader,
    0 : BS3PosiSetupBlock,
    1 : BS3PosiDataBlock,
    2 : BS3PosiSteerBlock,
}


##---MAIN

if __name__ == '__main__':
    pass
