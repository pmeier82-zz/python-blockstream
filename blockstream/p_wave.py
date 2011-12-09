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


##---ALL

__all__ = [
    # protocol classes
    'BS3SortBlockHeader',
    'BS3SortBaseBlock',
    'BS3SortSetupBlock',
    'BS3SortDataBlock',
    ]


##---IMPORTS

from struct import pack, unpack, calcsize
import scipy as sp
from blockstream import BS3BaseHeader, BS3BaseBlock


##---CLASSES

class BS3SortBlockHeader(BS3BaseHeader):
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
        if len(data) < BS3SortBlockHeader.__len__():
            raise ValueError(
                'data must have len >= %s' % BS3SortBlockHeader.__len__())
        ver, btp = unpack(BS3SortBlockHeader.signature,
                          data[:BS3SortBlockHeader.__len__()])
        if ver != BS3SortBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3SortBlockHeader(btp)


class BS3SortBaseBlock(BS3BaseBlock):
    """"Sort data block"""

    BLOCK_CODE = 'SORT'


class BS3SortSetupBlock(BS3SortBaseBlock):
    """"SORT - setupblock"""

    def __init__(self,
                 # header
                 header,
                 # setupblock stuff
                 group_lst):
        """
        :Paramters:
            header : BS3SortBlockHeader

            group_lst : list
                list of group specs. entry:
                    grp_idx::uint16,
                    nc::uint16,
                    tf::uint16,
                    cutleft::uint16,
                    ncov::f32[tf*nc*tf*nc],
                    unit_lst::list (
                        unit_idx::uint32 (0=mu)
                        filter::f32[tf*nc],
                        template::f32[tf*nc],
                        snr::f32,
                        active::uint8 (0=off, 1=on)
                        user1::uint16,
                        user2::uint16)
                    )
        """

        # super
        super(BS3SortSetupBlock, self).__init__(header)

        # members
        self.group_lst = list(group_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<H', len(self.group_lst))
        for group in self.group_lst:
            grp_idx, nc, tf, cl = group[:4]
            rval += pack('<HHHH', grp_idx, nc, tf, cl)
            rval += group[4].astype(sp.float32).tostring()
            rval += pack('<I', len(group[5]))
            for unit in group[5]:
                rval += pack('<I', unit[0])
                rval += unit[1].T.astype(sp.float32).tostring()
                rval += unit[2].T.astype(sp.float32).tostring()
                rval += pack('<fBHH', unit[3], unit[4], unit[5])
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3SortSetupBlock, self).__str__()
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
                grp_idx, nc, tf, cl = unpack('<HHHH', data[at:at + 8])
                at += 8
                tf_nc = tf * nc
                cov = sp.frombuffer(data[at:at + tf_nc * tf_nc * 4],
                                    dtype=sp.float32)
                at += tf_nc * tf_nc * 4
                cov.shape = (tf_nc, tf_nc)
                nunit, = unpack('<I', data[at:at + 4])
                at += 4
                unit_lst = []
                if nunit > 0:
                    for _ in xrange(nunit):
                        filt = sp.frombuffer(
                            data[at:at + tf_nc * 4],
                            dtype=sp.float32
                        ).reshape(tf, nc).T
                        at += tf_nc * 4
                        temp = sp.frombuffer(
                            data[at:at + tf_nc * 4],
                            dtype=sp.float32
                        ).reshape(tf, nc).T
                        at += tf_nc * 4
                        snr, active, u1, u2 = unpack('<fBHH', data[at:at + 9])
                        at += 9
                        unit_lst.append((filt, temp, snr, active, u1, u2))
                group_lst.append((grp_idx, nc, tf, cl, cov, unit_lst))
        return BS3SortSetupBlock(header, group_lst)


class BS3SortDataBlock(BS3SortBaseBlock):
    """"SORT - datablock"""

    def __init__(self,
                 # header
                 header,
                 # datablock stuff
                 event_lst):
        """
        :Paramters:
            header : BS3SortBlockHeader

            event_lst : list
                list of event channel chunks. entry:
                    group_nr::uint16,
                    unit_nr::uint32,
                    time_val::uint64,
                    event_type::uint16,
                    user1::uint16,
                    user2::uint16
        """

        # super
        super(BS3SortDataBlock, self).__init__(header)

        # members
        self.event_lst = list(event_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<I', len(self.event_lst))
        if len(self.event_lst) > 0:
            for ev in self.event_lst:
                rval += pack('<HIQHHH', *ev)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3SortDataBlock, self).__str__()
        return '%s::[ev:%d]' % (super_str, len(self.event_lst))

    @staticmethod
    def from_data(header, data):
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
                ev = unpack('<HIQHHH', data[at:at + 20])
                at += 20
                event_lst.append(ev)
        return BS3SortDataBlock(header, event_lst)


##---PROTOCOL

PROT = {
    'H':BS3SortBlockHeader,
    'B':BS3SortBaseBlock,
    0:BS3SortSetupBlock,
    1:BS3SortDataBlock,
}

##---MAIN

if __name__ == '__main__':
    pass
