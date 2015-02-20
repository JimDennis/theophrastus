#!/usr/bin/env python
'''Test a web form posting page by posting lorem ipsum data thereto
   as quickly as possible

   Dependencies:
    loremipsum
    requests
'''

from loremipsum import get_sentences
import requests
import time

def gen_test_data(num):
    '''Generate a list of {{num}} dictionaries suitable for posting
    '''
    start = time.time()
    results = [{'name':x.split()[0], 'message':x} for x in get_sentences(num)]
    elapsed = time.time() - start
    return results, elapsed

def testpost(tst, url='http://localhost:8080/confirmation'):
    '''Post a test data
       Return error count (0 or 1) and request results (for debugging)
    '''
    results = None
    err = 0
    r = None
    try:
        r = requests.post(url, data=tst)
    except Exception, e:
        results = 'Exception Raised for %s: %s' % (tst, e)
        err = 1

    if r and not r.ok:
        results = 'Not OK: %s' % tst
        err = 1
    return (err, results)

if __name__ == '__main__':
    import sys
    from multiprocessing import Pool

    args = sys.argv[1:]
    num_tests = 1000
    num_procs = 10
    if len(args) > 0:
        try:
            num_tests = int(args[0])
        except ValueError, e:
            print >> sys.stderr, 'Unable to parse int(%s): %s' % (args[0], e)
    if len(args) > 1:
        try:
            num_procs = int(args[1])
        except ValueError, e:
            print >> sys.stderr, 'Unable to parse int(%s): %s' % (args[1], e)

    tstsuite, gen_time = gen_test_data(num_tests)

    results = list()

    start = time.time()
    pool = Pool(num_procs)
    hammer = pool.imap(testpost, tstsuite)
    for i in hammer:
        results.append(i[0])
    elapsed = time.time() - start

    err_count = sum(results)

    n = len(tstsuite)
    print 'Took %0.2g seconds to generate %d tests' % (gen_time, n)
    print 'Took %0.2g seconds to post %d tests (%0.2g/second)' % (elapsed, n, n/elapsed)
    if err_count:
        print 'There were %d errors reported in testpost()' % err_count

