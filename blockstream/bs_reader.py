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

"""reader thread handling single tetrode data management"""
__docformat__ = 'restructuredtext'


##---ALL

__all__ = [
    'BS3SingleProtocolReader',
    'BS3MultiProtocolReader',
]


##---IMPORTS

from ctypes import byref, c_int64, c_char, POINTER
from threading import Thread, Event
from Queue import Queue
from blockstream import (load_blockstream, BS3Error, BS3DataBlockHeader,
                         BS3BaseBlock)
# protocols
import p_bxpd
import p_posi
import p_sort


##---CONSTANTS

PROTOCOLS = {
    'BXPD' : p_bxpd.PROT,
    'POSI' : p_posi.PROT,
    'SORT' : p_sort.PROT,
}
IDX_RID = 0
IDX_PAM = 1
IDX_THR = 0


##---CLASSES

class BS3SingleProtocolReader(Thread):
    """thread relaying handling incoming blockstream packages
    
    works with a single tier 2 protocol
    """

    ## constructor

    def __init__(self, protocol, out_q, verbose=False):
        """
        :Parameters:
            protocol : str
                valid protocol identifier
                Required
            out_q : Queue
                queue for output data
                Required
            verbose : bool
                if True, report internal activity
                Default=False
        """

        # super for thread
        Thread.__init__(self, name='pyBlockStreamReader' + protocol)
        self.daemon = True

        # members
        self._serving = False
        self._is_shutdown = Event()
        self._is_shutdown.set()
        self._is_initialised = Event()
        self._is_initialised.clear()
        self._bs_lib = None
        self._verbose = bool(verbose)
        self._protocol_id = str(protocol).upper()
        if self._protocol_id not in PROTOCOLS:
            raise BS3Error('unknown protocol identifier: %s' % self._protocol_id)
        self._protocol = [None] * 2
        if not isinstance(out_q, Queue):
            raise BS3Error('no output queue passed!')
        self._out_q = out_q

    ## blockstream

    def start_blockstream(self):
        """initialises the blockstream library for reading"""

        self._bs_lib = load_blockstream()
        self._bs_lib.init()
        self._protocol[IDX_RID] = self._bs_lib.startReader(self.name)
        self._out_q.put((self._protocol_id, self._protocol[IDX_RID]))
        self._is_initialised.set()

    def stop_blockstream(self):
        """frees the resources allocated from the library"""

        if self._bs_lib is not None:
            self._bs_lib.finalizeAll()
        self._protocol = [None] * 2
        print '!'
        self._out_q.put_nowait(None)
        self._is_initialised.clear()

    ## threading

    def run(self):
        """polls for new data and relays to self._out_q"""

        # setup stuff
        self.start_blockstream()
        self._serving = True
        self._is_shutdown.clear()

        # doomsday loop
        if self._verbose:
            print 'starting doomsday loop'
        while self._serving:

            # receive data by polling library
            i64_latency = c_int64()
            i64_blocksize = c_int64()
            car_data = POINTER(c_char)()
            b_got_block = self._bs_lib.readBlock(self._protocol[IDX_RID],
                                                 byref(i64_latency),
                                                 byref(i64_blocksize),
                                                 byref(car_data),
                                                 1000)

            # handle data by building blocks
            if b_got_block:
                # we received a block
                if self._verbose:
                    print 'incoming[%s][%s]' % (i64_latency.value, i64_blocksize.value)
                if i64_blocksize.value < BS3DataBlockHeader.__len__():
                    raise BS3Error('bad block size!')
                data = str(car_data[:i64_blocksize.value])
                # lets segment the data
                at = BS3DataBlockHeader.__len__()
                blk_h = BS3DataBlockHeader.from_data(data[:at])
                if blk_h.block_code == self._protocol_id:
                    # handle our protocol
                    header_cls = PROTOCOLS[self._protocol_id]['H']
                    header = header_cls.from_data(data[at:at + header_cls.__len__()])
                    at += header_cls.__len__()
                    if header.block_type in PROTOCOLS[self._protocol_id]:
                        blk_cls = PROTOCOLS[self._protocol_id][header.block_type]
                        blk = blk_cls.from_data(header, data[at:])
                        self._out_q.put(blk)
                    else:
                        if self._verbose:
                            print 'unknown blocktype: %s::%s' % (blk_h, header)
                else:
                    # other blocks -- what is wrong here?
                    if self._verbose:
                        print 'received block for other protocol! %s' % blk_h
                # done handling the block
                self._bs_lib.releaseBlock(self._protocol[IDX_RID])

        # proper shutdown code here
        if self._verbose:
            print 'left doomsday loop'
        self.stop_blockstream()
        self._is_shutdown.set()

    def stop(self):
        """stop the thread"""

        self._serving = False
        self._is_shutdown.wait()


class BS3MultiProtocolReader(Thread):
    """thread relaying handling incoming blockstream packages
    
    works with multiple tier 2 protocols by spawning multiple single tier 2
    protocol threads 
    """

    ## constructor

    def __init__(self, protocols, verbose=False):
        """
        :Parameters:
            protocols : list
                list of valid protocol identifiers. one additional thread will
                be spawned per entry/protocol 
                Required
            verbose : bool
                if True, report internal activity
                Default=False
        """

        # super for thread
        Thread.__init__(self, name='pyBlockStreamReader_multi')
        self.daemon = True

        # members
        self._serving = False
        self._is_shutdown = Event()
        self._is_shutdown.set()
        self._is_initialised = Event()
        self._is_initialised.clear()
        self._verbose = bool(verbose)
        self._req_q = Queue()
        self._data_q = Queue()
        self._listeners = {}
        self._protocol_ids = []
        for p in protocols:
            if p.upper() not in PROTOCOLS:
                raise BS3Error('unknown protocol identifier: %s' % p.upper())
            self._protocol_ids.append(p.upper())
        self._protocol = dict(zip(self._protocol_ids, [[None] * 2] * len(self._protocol_ids)))

    ## interface

    def add_listener(self, q):
        """register a new listener

        :Parameters:
            q : Queue.Queue
                Queue where data will be received
                Required
        :Returns:
            None, when the request has been processes
        :Raises:
            BS3Error : is no setupblock is present.
        """

        if self._is_initialised.is_set() is False:
            raise BS3Error('not initialized!')
        if not isinstance(q, Queue):
            raise TypeError('must pass q (Queue.Queue)!')
        self._req_q.join()
        self._req_q.put(q)
        self._req_q.join()

    ## threading

    def run(self):
        """polls for new data from sub_threads and relays to listeners"""

        # setup stuff
        self._serving = True
        self._is_shutdown.clear()

        # start single protocol threads
        for p in self._protocol_ids:
            self._protocol[p][IDX_THR] = BS3SingleProtocolReader(p,
                                                                 self._data_q,
                                                                 verbose=self._verbose)
            self._protocol[p][IDX_THR].start()
        self._is_initialised.set()

        # doomsday loop
        if self._verbose:
            print 'starting doomsday loop'
        while self._serving:

            # receive request from req_q
            while not self._req_q.empty():
                item = self._req_q.get()
                if isinstance(item, Queue):
                    lst_id = 0
                    while True:
                        if lst_id not in self._listeners:
                            break
                        lst_id += 1
                    self._listeners[lst_id] = item
                    item.put(lst_id)
                    for prot in self._protocol_ids:
                        if self._protocol[prot][IDX_PAM] is None:
                            item.put(self._protocol[prot][IDX_PAM])
                self._req_q.task_done()

            # receive data from data_q
            while not self._data_q.empty():
                item = self._data_q.get(True, 1)
                if isinstance(item, BS3BaseBlock):
                    if item.header.block_type == 0:
                        # got new preamble
                        self._protocol[item.BLOCKCODE][IDX_PAM] = item
                    for lq in self._listeners.values():
                        lq.put(item)

        # proper shutdown code here
        if self._verbose:
            print 'left doomsday loop'
        self._is_shutdown.set()

    def stop(self):
        """stop the thread"""

        self._serving = False
        self._is_shutdown.wait()


def test_single(n=100):

    try:
        Q = Queue()
        bs_reader = BS3SingleProtocolReader('bxpd', Q, verbose=True)
        bs_reader.start()
        for _ in xrange(n):
            item = Q.get()
            print 'got item:', item
    except Exception, ex:
        print ex
    finally:
        bs_reader.stop()
        print 'exit!'

def test_multiple(n=100):

    import time

    try:
        Q = Queue()
        bs_reader = BS3MultiProtocolReader(['bxpd', 'sort'], verbose=True)
        bs_reader.start()
        while True:
            try:
                bs_reader.add_listener(Q)
                break
            except Exception, ex:
                print ex
        for _ in xrange(n):
            item = Q.get()
            print 'got item:', item
    except Exception, ex:
        print ex
    finally:
        bs_reader.stop()
        print 'exit!'

##---MAIN

if __name__ == '__main__':

#    print 'testing single protocol with bxpd'
#    test_single()
#    print

    print 'testing single protocol with bxpd & sort'
    test_multiple()
    print
