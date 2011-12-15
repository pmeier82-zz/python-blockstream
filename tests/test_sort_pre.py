from blockstream import *
import scipy as sp
import traceback

GID = 0
UID = 1
TF = 3
NC = 1
TEMP = sp.array([[0, 1.0, 0] for i in xrange(NC)], dtype=sp.float32).T
FILT = TEMP

if __name__ == '__main__':
    try:
        LIB = load_blockstream('test')
        print 'got lib:', LIB, 'APPNAME:'
        WID = LIB.startWriter('pyTestSortWriter', 'SORT')
        print 'returned: WID = LIB.startWriter(\'pyTestSortWriter\', \'SORT\')'
        PREAMBLE = BS3SortSetupBlock([
            [GID, NC, TF, 0, sp.eye(TF * NC, dtype=sp.float32),
                [(UID, FILT, TEMP, 1.0, 1, 0, 0)]]
        ])
        LIB.setPreamble(WID, PREAMBLE.BLOCK_CODE, PREAMBLE.payload(),
                        len(PREAMBLE))
        raw_input()
    except Exception, ex:
        traceback.print_exc()
    finally:
        LIB.finalizeAll()
        print 'exit!'
