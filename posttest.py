#!/usr/bin/env python
from loremipsum import get_sentences
import requests
import time
start = time.time() 
generate_elapsed = time.time() - start
tstsuite = [{'name':x.split()[0],'message':x} for x in get_sentences(1000)]
def testpost(tst):
    r = requests.post('http://localhost:8080/confirmation', data=tst)
    if not r.ok:
        print 'No OK:', nm
    return r
start = time.time(); 
for each in tstsuite:
    testpost(each)
elapsed = time.time() - start 

n =  len(tstsuite)
print "Took %s seconds to generate %d tests" % (generate_elapsed, n)
print "Took %s seconds to post %d tests (%g/second)" % (elapsed, n, n/elapsed)
