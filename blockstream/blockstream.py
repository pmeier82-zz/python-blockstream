"""test dll loading and ctype stuff"""

##---ALL

__all__ = [
    'get_idx',
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

LIBNAME = 'libblockstream.so'
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
    """baseclass for protocol headers
    
    subclasses should define a binary signature along with at least a payload()
    and a static from_data() factory method!
    """

    version = 0
    signature = ''

    @classmethod
    def __len__(cls):
        return calcsize(cls.signature)


class BS3DataBlockHeader(BS3BaseHeader):
    """header for a datablock from the blockstream protocol"""

    version = 3
    signature = '<BIHHQqB4sQ'

    type_code = 1
    header_size = 31

    def __init__(self,
                 block_size=31,
                 writer_id=0,
                 block_index=0,
                 time_stamp=0,
                 block_code='WOOT'):
        """
        :Paramters:
            block_size : uint32 = 31
            writer_id : uint16 = 0
            block_index : uint64 = 0
            time_stamp : int64 = 0
            block_code : char[4] = 'WOOT'
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
        return 'BS3::Data(#%s~@%s~[%s])' % (self.block_size,
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


class BS3BxpdBaseBlock(object):
    """"BXPD data block"""

    BLOCK_CODE = 'BXPD'

    def __init__(self, bxpd_h):
        """
        :Parameters:
        """

        self.bxpd_h = bxpd_h

    def __str__(self):
        return '::%s' % self.bxpd_h


class BS3BxpdSetupBlock(BS3BxpdBaseBlock):
    """"BXPD - setupblock"""

    def __init__(self,
                 # header
                 bxpd_h,
                 # setupblock stuff
                 srate_lst,
                 anchan_lst,
                 dichan_lst,
                 evchan_lst,
                 group_lst):
        """
        :Paramters:
            bxpd_h : BS3BxpdBlockHeader
            
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
        super(BS3BxpdSetupBlock, self).__init__(bxpd_h)

        # members
        self.srate_lst = list(srate_lst)
        self.anchan_lst = list(anchan_lst)
        self.dichan_lst = list(dichan_lst)
        self.evchan_lst = list(evchan_lst)
        self.group_lst = list(group_lst)

    def payload(self):
        rval = ''
        rval += self.bxpd_h.payload()
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
    def from_data(bxpd_h, data):
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
        return BS3BxpdSetupBlock(bxpd_h, srate_lst, anchan_lst, dichan_lst, evchan_lst, group_lst)


class BS3BxpdDataBlock(BS3BxpdBaseBlock):
    """"BXPD - datablock"""

    def __init__(self,
                 # header
                 bxpd_h,
                 # datablock stuff
                 time_stamp,
                 srate_lst,
                 anchan_lst,
                 dichan_lst,
                 evchan_lst):
        """
        :Paramters:
            bxpd_h : BS3BxpdBlockHeader
            
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
        super(BS3BxpdDataBlock, self).__init__(bxpd_h)

        # members
        self.time_stamp = tuple(time_stamp)
        self.srate_lst = list(srate_lst)
        self.anchan_lst = list(anchan_lst)
        self.dichan_lst = list(dichan_lst)
        self.evchan_lst = list(evchan_lst)

    def payload(self):
        rval = ''
        rval += self.bxpd_h.payload()
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
    def from_data(bxpd_h, data):
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
        return BS3BxpdDataBlock(bxpd_h, time_stamp, srate_lst, anchan_lst, dichan_lst, evchan_lst)


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

        if self._blkstr is not None:
            raise RuntimeWarning('blockstream library already loaded!')
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
