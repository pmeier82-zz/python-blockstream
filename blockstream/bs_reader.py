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
    'ProtocolHandler'
]


##---IMPORTS

from ctypes import byref, c_int64, c_char, POINTER
from threading import Thread, Event
from Queue import Queue
from blockstream import (load_blockstream, BS3Error, BS3DataBlockHeader)


##---CLASSES

class ProtocolHandler(object):
    """abstract protocol _handler"""

    def _init__(self):
        pass

    def on_block_ready(self, block_header, block_data):
        """returns BS3BaseBlock"""
        pass


class BS3SingleProtocolReader(Thread):
    """thread relaying handling incoming blockstream packages
    
    works with a single tier 2 protocol
    """

    ## constructor

    def __init__(self, protocol_handler_cls, out_q, verbose=False, ident='?'):
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
        Thread.__init__(self, name='pyBlockStreamReader' + ident)
        self.daemon = True

        # members
        self._ident = str(ident)
        self._serving = False
        self._is_shutdown = Event()
        self._is_shutdown.set()
        self._is_initialised = Event()
        self._is_initialised.clear()
        self._bs_lib = None
        self._verbose = bool(verbose)
        self._protocol_handler_cls = protocol_handler_cls
        self._handler = None
        self._reader_id = None

        if not isinstance(out_q, Queue):
            raise BS3Error('no output queue passed!')
        self._out_q = out_q

    ## blockstream

    def _initialize(self):

        self._handler = self._protocol_handler_cls()


    def start_blockstream(self):
        """initialises the blockstream library for reading"""

        self._bs_lib = load_blockstream()
        self._bs_lib.init()
        self._reader_id = self._bs_lib.startReader(self._ident)
        if self._verbose:
            print 'reader id:', self._reader_id
        self._is_initialised.set()

    def stop_blockstream(self):
        """frees the resources allocated from the library"""

        if self._bs_lib is not None:
            self._bs_lib.finalizeAll()
#            self._bs_lib.finalizeReader(self._reader_id) # TODO: new blockstream
        self._out_q.put_nowait(None)
        self._is_initialised.clear()

    ## threading

    def run(self):
        """polls for new data and relays to self._out_q"""

        # setup stuff
        self._initialize()
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
            b_got_block = self._bs_lib.readBlock(self._reader_id,
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

                # call on block ready
                protocol_block = self._handler.on_block_ready(blk_h, data[at:])
                if protocol_block is not None:
                    self._out_q.put((blk_h, protocol_block))

                # release block
                self._bs_lib.releaseBlock(self._reader_id)

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

    pass
