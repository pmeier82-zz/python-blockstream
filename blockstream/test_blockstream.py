from blockstream import *
from p_sort import *
import scipy as sp

TET = 1
TF = 20
NC = 4
TEMP = sp.array(
    [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    for i in xrange(NC)], dtype=sp.float32
).T
FILT = -TEMP
BLOCK = BS3SortDataBlock([(0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5)])
BLOCK_BYTES = BLOCK.payload()
BLOCK_LEN = len(BLOCK_BYTES)

if __name__ == '__main__':
    LIB = load_blockstream()
    print 'got lib'
    LIB.finalizeWriter(0)
    print 'returned: LIB.finalizeWriter(0)'
    LIB.initQt()
    print 'returned: LIB.initQt()'
    LIB.initApp('test', 15000)
    print "returned: LIB.initQt('test', 15000)"
    WID = LIB.startWriter('pyTestSortWriter', 'SORT')
    print "returned: WID = LIB.startWriter('pyTestSortWriter', 'SORT')"
    PREAMBLE = BS3SortSetupBlock([
        [0, NC, TF, 0, sp.eye(TF * NC, dtype=sp.float32),
            [(0, FILT, TEMP, 1.0, 1, 0, 0)]]
    ])
    LIB.setPreamble(WID, PREAMBLE.BLOCK_CODE, PREAMBLE.payload(),
                    len(PREAMBLE))
    try:
        while True:
            LIB.sendBlock(WID, BLOCK.BLOCK_CODE, BLOCK_BYTES, BLOCK_LEN)
            print '.',
    except Exception, ex:
        print ex
    finally:
        LIB.finalizeAll()
        print 'exit!'
