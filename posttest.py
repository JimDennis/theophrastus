#!/usr/bin/env python
from loremipsum import get_sentences
import requests
import time
start = time.time()
generate_elapsed = time.time() - start
err_count = 0
tstsuite = [{'name':x.split()[0],'message':x} for x in get_sentences(1000)]
def testpost(tst):
    r = requests.post('http://localhost:8080/confirmation', data=tst)
    if not r.ok:
        print 'Not OK:', nm
        err_count += 1
    return r

if __name__ == '__main__':
    start = time.time();
    for each in tstsuite:
        testpost(each)
    elapsed = time.time() - start

    n =  len(tstsuite)
    print 'Took %s seconds to generate %d tests' % (generate_elapsed, n)
    print 'Took %s seconds to post %d tests (%g/second)' % (elapsed, n, n/elapsed)
    if err_count:
        print 'There were %d error reported in testpost()' % err_count

