from blockstream import (BS3Reader, COVEProtocolHandler,
                         WAVEProtocolHandler, Queue, Empty, USE_PROCESS)
from common import MxRingBuffer
from spikeplot import plt, waveforms, save_figure

def test_cove_reader(n=10000):
    plt.interactive(True)
    try:
        FIG = plt.figure()
        Q = Queue()
        bs_reader = BS3Reader(COVEProtocolHandler, Q, verbose=True,
                              ident='TestCOVE')
        bs_reader.start()
        for _ in xrange(n):
            print Q.qsize()
            try:
                item = Q.get(block=True, timeout=2)
                FIG.clf()
                plt.imshow(item.data_lst[-1], shape=item.data_lst[-1].shape,
                           figure=FIG)
            except Empty:
                continue
    except Exception, ex:
        print ex
    finally:
        raw_input()
        bs_reader.stop()
        if USE_PROCESS is True:
            bs_reader.terminate()
            # finalize app
        print 'exit!'


def test_wave_reader(n=10000):
    #plt.interactive(True)
    try:
        update = 0
        FIG = plt.figure()
        rb = None
        Q = Queue()
        bs_reader = BS3Reader(WAVEProtocolHandler, Q, verbose=False,
                              ident='TestWAVE')
        bs_reader.start()
        for _ in xrange(n):
            #print Q.qsize()
            try:
                item = Q.get(block=True, timeout=2)
                for wave in item.event_lst:
                    gid, uid, tv, nc, ns, wf = wave
                    if rb is None:
                        rb = MxRingBuffer(dimension=(ns, nc), capacity=2000)
                    rb.append(wf)
                    #print 'rb:', len(rb)
                    update += 1
                if update > 1000:
                    print 'plotting enter'
                    FIG.clear()
                    waveforms({0: rb[:]}, tf=ns, plot_handle=FIG,
                                        plot_separate=False, show=False)
                    #plt.draw()
                    save_figure(FIG, 'wave', file_dir='E:\SpiDAQ')
                    update = 0
                    print 'plotting exit'
            except Empty:
                continue
    except Exception, ex:
        print ex
    finally:
        raw_input()
        bs_reader.stop()
        if USE_PROCESS is True:
            bs_reader.terminate()
            # finalize app
        print 'exit!'


if __name__ == '__main__':
    #test_cove_reader()
    test_wave_reader()
