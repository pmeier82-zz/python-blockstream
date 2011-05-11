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

from ctypes import CDLL, byref, c_int64, c_char, POINTER
from ctypes.util import find_library
import os
from threading import Thread, Event
from Queue import Queue, Empty
from struct import pack, unpack, calcsize
import scipy as sp
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














class BS3Reader(Thread):
    """thread handling incoming blockstream data"""

    ## constructor

    def __init__(self, poll_timeout=1000, input_q=None, verbose=False):
        """
        :Paramters:
            input_q : Queue
                input queue for new listeners
            poll_timeout : int
                non - negative int will be interpreted as timeout in milliseconds,
                negative int will wait indefinitly
            verbose : bool
                if True, report internal activity
        """

        # super for thread
        Thread.__init__(self, name='pyBlockStreamReader')
        self.daemon = True

        # members
        self.poll_timeout = int(poll_timeout)
        self._reader_id = None
        self._serving = False
        self._is_shutdown = Event()
        self._is_shutdown.set()
        self._is_initialised = Event()
        self._is_initialised.clear()
        self._blkstr = None
        self._listeners = {}
        self._setup_block = None
        self._verbose = bool(verbose)
        self._input_q = input_q or Queue()

    ## blockstream

    def start_blockstream(self):
        """initialises the blockstream library for reading"""

        self.stop_blockstream()
        self._blkstr = load_blockstream_lib()
        self._blkstr.init()
        self._reader_id = self._blkstr.startReader(self.name)

    def stop_blockstream(self):
        """frees the resources allocated from the library"""

        if self._blkstr is not None:
            self._blkstr.finalizeAll()
        self._reader_id = None
        while len(self._listeners) > 0:
            k, v = self._listeners.popitem()
            if isinstance(v[0], Queue):
                v[0].put_nowait(None)
#                v[0].join()
            del k, v

    ## internals



    ## interface

    def add_listener(self, q, group):
        """register a new listener, identified by a set of constraints

        :Parameters:
            queue : Queue.Queue
                Queue where data will be received
            group : int
                the group we are interested in, must be existent!
        :Returns:
            None, when the request has been processes
        :Raises:
            BS3Error : is no setupblockis present.
        """

        if self._is_initialised.is_set() is False:
            raise BS3Error('not initialized!')
        if not isinstance(q, Queue):
            raise TypeError('must pass q (Queue.Queue) and group (int)!')
        self._input_q.join()
        self._input_q.put((q, int(group)))
        self._input_q.join()

    ## threading

    def run(self):
        """handle blockstream io

        Polls for new data and puts it on the receive queue, while sending items
        on the send queue.
        """

        # setup stuff
        self.start_blockstream()
        self._serving = True
        self._is_shutdown.clear()

        # doomsday loop
        if self._verbose:
            print 'starting doomsday loop'
        while self._serving:

            # input queue
            if not self._input_q.empty():
                item = self._input_q.get()
                if item[1] < len(self._setup_block.group_lst):
                    lst_id = len(self._listeners)
                    q = item[0]
                    g = self._setup_block.group_lst[item[1]][-1]
                    sri = self._setup_block.anchan_lst[g[0]][1]
                    self._listeners[lst_id] = (q, g, sri)
                    q.put(lst_id)
                    q.put(self._setup_block)
                else:
                    q.put(None)
                self._input_q.task_done()

            # receive data
            i64_latency = c_int64()
            i64_blocksize = c_int64()
            car_data = POINTER(c_char)()
            b_got_block = self._blkstr.readBlock(self._reader_id,
                                                 byref(i64_latency),
                                                 byref(i64_blocksize),
                                                 byref(car_data),
                                                 self.poll_timeout)
            if b_got_block:
                # we received a block
                if self._verbose:
                    print 'incoming[%s][%s]' % (i64_latency.value, i64_blocksize.value)
                if i64_blocksize.value < BS3DataBlockHeader.__len__():
                    raise BS3Error('bad block size!')
                data = str(car_data[:i64_blocksize.value])
                # lets segement the data
                at = BS3DataBlockHeader.__len__()
                blk_h = BS3DataBlockHeader.from_data(data[:at])
                if blk_h.block_code == 'BXPD':
                    # got a BXPD block
                    bxpd_h = BS3BxpdBlockHeader.from_data(data[at:at + BS3BxpdBlockHeader.__len__()])
                    at += BS3BxpdBlockHeader.__len__()
                    if bxpd_h.block_type == 0:
                        # SETUP BLOCK HERE
                        setup_block = BS3BxpdSetupBlock.from_data(bxpd_h, data[at:])
                        self._setup_block = setup_block
                        self._is_initialised.set()
                        for q, g, sri in self._listeners.values():
                            q.put(self._setup_block)
                        if self._verbose:
                            print '#' * 25
                            print 'new setup block:'
                            print self._setup_block
                            print '#' * 25
                    elif bxpd_h.block_type == 1:
                        # DATA BLOCK HERE
                        data_block = BS3BxpdDataBlock.from_data(bxpd_h, data[at:])
                        for q, g, sri in self._listeners.values():
                            if len(data_block.anchan_lst) < g:
                                this_blk = tuple([blk_h.block_index,
                                                  data_block.srate_lst[sri]] +
                                                  [data_block.anchan_lst[i] for i in g])
                                q.put(this_blk)
                        if self._verbose:
                            print 'got %s' % data_block
                    else:
                        if self._verbose:
                            print '%s::%s' % (blk_h, bxpd_h)
                else:
                    # other blocks -- whats wrong here?
                    if self._verbose:
                        print 'not a bxpd block! %s' % blk_h
                # done handling the block
                self._blkstr.releaseBlock(self._reader_id)

        # proper shutdown code here
        if self._verbose:
            print 'left doomsday loop'
        self.stop_blockstream()
        self._is_shutdown.set()

    def stop(self):
        """stop the thread"""

        self._serving = False
        self._is_shutdown.wait()


##---MAIN

if __name__ == '__main__':

    import time

    try:
        bs_reader = BS3Reader(verbose=False)
        bs_reader.start()

        Q = Queue()
        print 'trying to connect listener'
        while True:
            try:
                bs_reader.add_listener(Q, 0)
                break
            except Exception, ex:
                print ex
                time.sleep(1)
        print
        print 'connected!'
        while True:
            item = Q.get()
            print 'got item:', item
    except Exception, ex:
        print ex
        bs_reader.stop()
    finally:
        print 'exit!'
