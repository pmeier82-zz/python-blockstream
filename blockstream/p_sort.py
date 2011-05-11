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
    # protocoll classes
    'BS3SortBlockHeader',
    'BS3SortBaseBlock',
    'BS3SortSetupBlock',
    'BS3SortDataBlock',
]


##---IMPORTS

from struct import pack, unpack, calcsize
import scipy as sp
from blockstream import BS3BaseHeader


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
            raise ValueError('data must have len >= %s' % BS3SortBlockHeader.__len__())
        ver, btp = unpack(BS3SortBlockHeader.signature, data[:BS3SortBlockHeader.__len__()])
        if ver != BS3SortBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3SortBlockHeader(btp)


class BS3SortBaseBlock(object):
    """"Sort data block"""

    BLOCK_CODE = 'SORT'

    def __init__(self, sort_h):
        """
        :Parameters:
        """

        self.sort_h = sort_h

    def __str__(self):
        return '::%s' % self.sort_h


class BS3SortSetupBlock(BS3SortBaseBlock):
    """"SORT - setupblock"""

    def __init__(self,
                 # header
                 sort_h,
                 # setupblock stuff
                 group_lst):
        """
        :Paramters:
            sort_h : BS3SortBlockHeader
            
            group_lst : list
                list of group specs. entry:
                    (grp_idx::uint16,
                     nc::uint16,
                     tf::uint16,
                     cutleft::uint16,
                     ncov::[tf*nc*tf*nc],
                     unit_lst::list
                         (filter::f32[tf*nc],
                          template::f32[tf*nc],
                          snr::f32,
                          user1::uint16,
                          user2::uint16)
                    )
        """

        # super
        super(BS3SortSetupBlock, self).__init__(sort_h)

        # members
        self.group_lst = list(group_lst)

    def payload(self):
        rval = ''
        rval += self.sort_h.payload()
        rval += pack('<H', len(self.group_lst))
        for group in self.group_lst:
            grp_idx, nc, tf, cl = group[:4]
            rval += pack('<HHHH', grp_idx, nc, tf, cl)
            rval += group[4].astype(sp.float32).tostring()
            rval += pack('<H', len(group[5]))
            for unit in group[5]:
                rval += unit[0].T.astype(sp.float32).tostring()
                rval += unit[1].T.astype(sp.float32).tostring()
                rval += pack('<fHH', unit[2], unit[3], unit[4])
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3SortSetupBlock, self).__str__()
        return '%s::[gr:%d]' % (super_str, len(self.group_lst))

    @staticmethod
    def from_data(blk_h, sort_h, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # groups
        group_lst = []
        ngroup, = unpack('<H', data[at:at + 1])
        at += 1
        if ngroup > 0:
            for _ in xrange(ngroup):
                grp_idx, nc, tf, cl = unpack('<HHHH', data[at:at + 8])
                tf_nc = tf * nc
                at += 8
                cov_buf = unpack('<%df' % tf_nc ** 2, data[at:at + tf_nc * tf_nc * 4])
                at += tf_nc * tf_nc * 4
                cov = sp.frombuffer(cov_buf, dtype=sp.float32)
                cov.shape = (tf_nc, tf_nc)
                nunit, = unpack('<H', data[at:at + 2])
                at += 2
                unit_lst = []
                if nunit > 0:
                    for _ in xrange(nunit):
                        filt_buf = unpack('<%df', data[at:at + tf_nc * 4])
                        at += tf_nc * 4
                        filt = sp.frombuffer(filt_buf, dtype=sp.float32).reshape(tf, nc).T
                        temp_buf = unpack('<%df', data[at:at + tf_nc * 4])
                        at += tf_nc * 4
                        temp = sp.frombuffer(temp_buf, dtype=sp.float32).reshape(tf, nc).T
                        snr, u1, u2 = unpack('<fHH', data[at:at + 8])
                        at += 8
                        unit_lst.append((filt, temp, snr, u1, u2))
                group_lst.append((grp_idx, nc, tf, cl, cov, unit_lst))
        return BS3SortSetupBlock(sort_h, group_lst)


class BS3SortDataBlock(BS3SortBaseBlock):
    """"SORT - datablock"""

    def __init__(self,
                 # header
                 sort_h,
                 # datablock stuff
                 event_lst):
        """
        :Paramters:
            sort_h : BS3SortBlockHeader
        
            event_lst : list
                list of event channel chunks. entry:
                    (group_nr::uint16,
                     unit_nr::uint16,
                     time_val::uint64,
                     event_type::uint16,
                     user1::uint16,
                     user2::uint16)
        """

        # super
        super(BS3SortDataBlock, self).__init__(sort_h)

        # members
        self.event_lst = list(event_lst)

    def payload(self):
        rval = ''
        rval += self.sort_h.payload()
        rval += pack('<I', len(self.event_lst))
        if len(self.event_lst) > 0:
            for ev in self.event_lst:
                rval += pack('<HHQHHH', *ev)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3SortDataBlock, self).__str__()
        return '%s::[ev:%d]' % (super_str, len(self.event_lst))

    @staticmethod
    def from_data(sort_h, data):
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
                ev = unpack('<HHQHHH', data[at:at + 18])
                at += 18
                event_lst.append(ev)
        return BS3SortDataBlock(sort_h, event_lst)


##---MAIN

if __name__ == '__main__':
    pass
