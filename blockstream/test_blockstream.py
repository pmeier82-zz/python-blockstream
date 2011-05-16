from blockstream import *
from p_bxpd import *
from p_sort import *
from bxpd_reader import *
import scipy as sp
import time
from Queue import Queue

TET = 1
TF = 20
NC = 4
TEMP = sp.array([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1] for i in xrange(NC)], dtype=sp.float32).T
FILT = -TEMP
BLOCK = BS3SortDataBlock(BS3SortBlockHeader(1), [(0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5)])
BLOCK_BYTES = BLOCK.payload()
BLOCK_LEN = len(BLOCK_BYTES)


if __name__ == '__main__':

    LIB = load_blockstream(True)
    LIB.init()
    WID = LIB.startWriter('pyTestSortWriter')
    PREAMBLE = BS3SortSetupBlock(BS3SortBlockHeader(0),
                                 [[0, NC, TF, 0,
                                   sp.eye(TF * NC, dtype=sp.float32),
                                   [(FILT, TEMP, 0, 0, 0)]]])
    LIB.setPreamble(WID, PREAMBLE.BLOCK_CODE, PREAMBLE.payload(), len(PREAMBLE))

    import time

    try:
        bs_reader = BS3BxpdReader(verbose=False)
        bs_reader.start()

        Q = Queue()
        print 'trying to connect listener'
        while True:
            try:
                bs_reader.add_listener(Q, TET)
                break
            except Exception, ex:
                print ex
                time.sleep(1)
        print
        print 'connected!'
        while True:
            item = Q.get()
            if item is None:
                raise RuntimeError('got None -> quiting')
            LIB.sendBlock(WID, BLOCK.BLOCK_CODE, BLOCK_BYTES, BLOCK_LEN)
    except Exception, ex:
        print ex
        bs_reader.stop()
    finally:
        LIB.finalizeAll()
        print 'exit!'
