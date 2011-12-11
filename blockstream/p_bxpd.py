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

"""protocol for the data of tetrodes"""
__docformat__ = 'restructuredtext'
__all__ = [
    # protocol classes
    'BS3BxpdBlockHeader',
    'BS3BxpdBaseBlock',
    'BS3BxpdSetupBlock',
    'BS3BxpdDataBlock',
    'BXPDProtocolHandler',
]


##---IMPORTS

from struct import pack, unpack, calcsize
from blockstream import BS3BaseHeader, BS3BaseBlock
from bs_reader import ProtocolHandler, Queue, BS3Reader, USE_PROCESS

##---CLASSES

class BS3BxpdBlockHeader(BS3BaseHeader):
    """header for a datablock of type BXPD from the blockstream protocol"""

    version = 3
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
        if len(data) < BS3BxpdBlockHeader.__len__():
            raise ValueError('data must have len >= %s' % BS3BxpdBlockHeader.__len__())
        ver, btp = unpack(BS3BxpdBlockHeader.signature, data[:BS3BxpdBlockHeader.__len__()])
        if ver != BS3BxpdBlockHeader.version:
            raise ValueError('invalid protocol version(%s)!' % ver)
        return BS3BxpdBlockHeader(btp)


class BS3BxpdBaseBlock(BS3BaseBlock):
    """"BXPD data block"""

    BLOCK_CODE = 'BXPD'


class BS3BxpdSetupBlock(BS3BxpdBaseBlock):
    """"BXPD - setupblock"""

    def __init__(self,
                 srate_lst,
                 anchan_lst,
                 dichan_lst,
                 evchan_lst,
                 group_lst):
        """
        :Paramters:
            srate_lst : list
                list of sample rates (as double)
            anchan_lst : list
                list of analog channels. entry:
                    (channr::uint16,
                     srate_idx::uint8,
                     name_len::uint16,
                     name::char[name_len])
            dichan_lst : list
                list of digital channels. entry:
                    (channr::uint16,
                     srate_idx::uint8,
                     name_len::uint16,
                     name::char[name_len])
            evchan_lst : list
                list of event channels. entry:
                    (channr::uint16,
                     srate_idx::uint8,
                     name_len::uint16,
                     name::char[name_len])
            group_lst : list
                list of analog channels. entry:
                    (name_len::uint16,
                     name::char[name_len],
                     grp_size::uint16,
                     channel_nrs::uint16[grp_size])
        """

        # super
        super(BS3BxpdSetupBlock, self).__init__(BS3BxpdBlockHeader(0))

        # members
        self.srate_lst = list(srate_lst)
        self.anchan_lst = list(anchan_lst)
        self.dichan_lst = list(dichan_lst)
        self.evchan_lst = list(evchan_lst)
        self.group_lst = list(group_lst)
        self.anchan_index_mapping = {}
        for i in xrange(len(self.anchan_lst)):
            self.anchan_index_mapping[self.anchan_lst[i][0]] = i

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<B%dd' % len(self.srate_lst), len(self.srate_lst), *self.srate_lst)
        rval += pack('<H', len(self.anchan_lst))
        for anchan in self.anchan_lst:
            rval += pack('<HBH%ds' % len(anchan[3]), *anchan)
        rval += pack('<H', len(self.dichan_lst))
        for dichan in self.dichan_lst:
            rval += pack('<HBH%ds' % len(dichan[3]), *dichan)
        rval += pack('<H', len(self.evchan_lst))
        for evchan in self.evchan_lst:
            rval += pack('<HBH%ds' % len(evchan[3]), *evchan)
        rval += pack('<H', len(self.group_lst))
        for group in self.group_lst:
            rval += pack('<H%dsH%dH' % (len(group[1]), len(group[3])), *group)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3BxpdSetupBlock, self).__str__()
        return '%s::[sr:%d][ac:%d][dc:%d][ec:%d][gr:%d]' % (super_str,
                                                            len(self.srate_lst),
                                                            len(self.anchan_lst),
                                                            len(self.dichan_lst),
                                                            len(self.evchan_lst),
                                                            len(self.group_lst))

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # srates
        srate_lst = []
        nsrate, = unpack('<B', data[at:at + 1])
        at += 1
        if nsrate > 0:
            srates = unpack('%dd' % nsrate, data[at:at + calcsize('%dd' % nsrate)])
            at += calcsize('%dd' % nsrate)
            srate_lst = list(srates)
        # anchans
        anchan_lst = []
        nanchan, = unpack('<H', data[at:at + 2])
        at += 2
        if nanchan > 0:
            for _ in xrange(nanchan):
                ch_nr, sr_idx, nlen = unpack('<HBH', data[at:at + 5])
                at += 5
                name, = unpack('<%ds' % nlen, data[at:at + nlen])
                at += nlen
                anchan_lst.append((ch_nr, sr_idx, nlen, name))
        # dichans
        dichan_lst = []
        ndichan, = unpack('<H', data[at:at + 2])
        at += 2
        if ndichan > 0:
            for _ in xrange(ndichan):
                ch_nr, sr_idx, nlen = unpack('<HBH', data[at:at + 5])
                at += 5
                name, = unpack('<%ds' % nlen, data[at:at + nlen])
                at += nlen
                dichan_lst.append((ch_nr, sr_idx, nlen, name))
        # evchans
        evchan_lst = []
        nevchan, = unpack('<H', data[at:at + 2])
        at += 2
        if nevchan > 0:
            for _ in xrange(nevchan):
                ch_nr, sr_idx, nlen = unpack('<HBH', data[at:at + 5])
                at += 5
                name, = unpack('<%ds' % nlen, data[at:at + nlen])
                at += nlen
                evchan_lst.append((ch_nr, sr_idx, nlen, name))
        # groups
        group_lst = []
        ngroup, = unpack('<H', data[at:at + 2])
        at += 2
        if ngroup > 0:
            for _ in xrange(ngroup):
                nlen, = unpack('<H', data[at:at + 2])
                at += 2
                name, = unpack('<%ds' % nlen, data[at:at + nlen])
                at += nlen
                grp_sz, = unpack('<H', data[at:at + 2])
                at += 2
                channels = unpack('<%dH' % grp_sz, data[at:at + 2 * grp_sz])
                at += 2 * grp_sz
                group_lst.append((nlen, name, grp_sz, channels))
        return BS3BxpdSetupBlock(header, srate_lst, anchan_lst, dichan_lst, evchan_lst, group_lst)


class BS3BxpdDataBlock(BS3BxpdBaseBlock):
    """"BXPD - datablock"""

    def __init__(self,
                 time_stamp,
                 srate_lst,
                 anchan_lst,
                 dichan_lst,
                 evchan_lst):
        """
        :Paramters:
            time_stamp: tuple(uint64, uint64)
                (start, end) of chunks in mu_sec
            srate_lst : list
                list of sample offsets per sample rate of the setupblock :: uint64.
            anchan_lst : list
                list of analog channel chunks. entry:
                     values::int16[]
            dichan_lst : list
                list of digital channel chunks. entry:
                    (chan_nr::uint16,
                     time::uint64,
                     event_type::uint8)
            evchan_lst : list
                list of event channel chunks. entry:
                    (chan_nr::uint16,
                     time::uint64,
                     event_type::uint8)
        """

        # super
        super(BS3BxpdDataBlock, self).__init__(BS3BxpdBlockHeader(1))

        # members
        self.time_stamp = tuple(time_stamp)
        self.srate_lst = list(srate_lst)
        self.anchan_lst = list(anchan_lst)
        self.dichan_lst = list(dichan_lst)
        self.evchan_lst = list(evchan_lst)

    def payload(self):
        rval = ''
        rval += self.header.payload()
        rval += pack('<QQ', *self.time_stamp)
        rval += pack('<B%dQ', len(self.srate_lst), *self.srate_lst)
        for anchan in self.anchan_lst:
            anchan_len = len(anchan)
            if anchan_len < 256:
                rval += pack('<B', anchan_len)
            else:
                rval += pack('<BQ', 255, anchan_len)
            rval += pack('<%di' % len(anchan), *anchan)
        rval += pack('<I', len(self.dichan_lst))
        for dichan in self.dichan_lst:
            rval += pack('<HQB', *dichan)
        rval += pack('<I', len(self.evchan_lst))
        for evchan in self.evchan_lst:
            rval += pack('<HQB', *evchan)
        return rval

    def __len__(self):
        return len(self.payload())

    def __str__(self):
        super_str = super(BS3BxpdDataBlock, self).__str__()
        return '%s::[sr:%d][ac:%d][dc:%d][ec:%d]' % (super_str,
                                                     len(self.srate_lst),
                                                     len(self.anchan_lst),
                                                     len(self.dichan_lst),
                                                     len(self.evchan_lst))

    @staticmethod
    def from_data(header, data):
        """build from data"""

        if not isinstance(data, str):
            raise TypeError('needs a sting as input!')
        at = 0

        # srates
        time_stamp = unpack('<QQ', data[at:at + 16])
        at += 16
        srate_lst = []
        nsrate, = unpack('<B', data[at:at + 1])
        at += 1
        if nsrate > 0:
            srates = unpack('%dQ' % nsrate, data[at:at + 8 * nsrate])
            at += 8 * nsrate
            srate_lst = list(srates)
        # anchans
        anchan_lst = []
        nanchan, = unpack('<H', data[at:at + 2])
        at += 2
        if nanchan > 0:
            for _ in xrange(nanchan):
                anchan_len, = unpack('<B', data[at:at + 1])
                at += 1
                if anchan_len == 255:
                    anchan_len, = unpack('<Q', data[at:at + 8])
                    at += 8
                values = unpack('<%dh' % anchan_len, data[at:at + anchan_len * 2])
                at += anchan_len * 2
                anchan_lst.append(values)
        # dichans
        dichan_lst = []
        ndichan, = unpack('<I', data[at:at + 4])
        at += 4
        if ndichan > 0:
            for _ in xrange(ndichan):
                ch_nr, t_val, e_typ = unpack('<HQB', data[at:at + 11])
                at += 11
                dichan_lst.append((ch_nr, t_val, e_typ))
        # evchans
        evchan_lst = []
        nevchan, = unpack('<I', data[at:at + 4])
        at += 4
        if nevchan > 0:
            for _ in xrange(nevchan):
                ch_nr, t_val, e_typ = unpack('<HQB', data[at:at + 11])
                at += 11
                evchan_lst.append((ch_nr, t_val, e_typ))
        return BS3BxpdDataBlock(header, time_stamp, srate_lst, anchan_lst, dichan_lst, evchan_lst)


class BXPDProtocolHandler(ProtocolHandler):

    def on_block_ready(self, block_header, block_data):

        if block_header.block_code == 'BXPD':

            # handle our protocol
            bxpd_header = BS3BxpdBlockHeader.from_data(block_data[:BS3BxpdBlockHeader.__len__()])
            at = BS3BxpdBlockHeader.__len__()
            bxpd_block = None
            if bxpd_header.block_type == 0:
                #setup block
                bxpd_block = BS3BxpdSetupBlock.from_data(bxpd_header, block_data[at:])
            elif bxpd_header.block_type == 1:
                #setup block
                bxpd_block = BS3BxpdDataBlock.from_data(bxpd_header, block_data[at:])
            else:
                print 'unknown block_code: %s::%s' % (block_header, bxpd_header)
            return bxpd_block
        else:
            # other blocks -- what is wrong here?
            print 'received block for other protocol! %s' % block_header
            return None


def test_single(n=100):

    try:
        Q = Queue()
        bs_reader = BS3Reader(BXPDProtocolHandler, Q, verbose=False, ident='TestBXPD')
        bs_reader.start()
        for _ in xrange(n):
            item = Q.get()
#            print 'got item:', item
            del item
    except Exception, ex:
        print ex
    finally:
        bs_reader.stop()
        if USE_PROCESS:
            bs_reader.terminate()
        print 'exit!'


##---MAIN

if __name__ == '__main__':

    test_single(1000)
