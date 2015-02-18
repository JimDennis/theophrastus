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
    err = 0
    r = requests.post(url, data=tst)
    if not r.ok:
        print 'Not OK:', tst
        err = 1
    return (err, r)

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    num_tests = 1000
    if args:
        try:
            num_tests = int(args[0])
        except ValueError, e:
            print >> sys.stderr, 'Unable to parse int(%s): %s' % (args[0], e)
    tstsuite, gen_time = gen_test_data(num_tests)

    err_count = 0
    start = time.time()
    for each in tstsuite:
        err, _ = testpost(each)
        err_count += err
    elapsed = time.time() - start

    n = len(tstsuite)
    print 'Took %s seconds to generate %d tests' % (gen_time, n)
    print 'Took %s seconds to post %d tests (%g/second)' % (elapsed, n, n/elapsed)
    if err_count:
        print 'There were %d error reported in testpost()' % err_count

