import requests, json, time

url = 'http://localhost:666'

selfip = '127.0.0.1'
selfport = '345'
selfadr = selfip +':'+ selfport
selfnewstate = '789'

def emptytest():
    assert requests.get(url + '/services').json() == {} \
        , 'error: GET /services -> not empty'

    assert requests.get(url + '/services/test').json() == {} \
        , 'error: GET /services/test -> not empty'    

    assert requests.get(url + '/services/test/' + selfadr).status_code == 404 \
        , 'error: GET /services/test/'+selfadr+' -> not failed' 
    return 0

testnum = 1
def testname(name):
    global testnum
    print ('#'+str(testnum) + ': Running ' + name + '... ', end='')
    testnum = testnum + 1
    return 0
    
#####    
testname ('empty run test')
emptytest()

print ('[PASSED]')

#####
testname ('incorrect POST placing test')
assert (requests.post(url + '/services/test', data={}).status_code) == \
    422 \
    , 'error: POST /services/type -> wrong answer'

print ('[PASSED]')

#####
testname ('correct POST placing test')
assert (requests.post(url + '/services/test', data={'port':selfport}).json()) == \
    {'status':'success', 'address':selfadr} \
    , 'error: POST /services/type -> wrong answer'

print ('[PASSED]')

#####
testname ('root request test')
r = requests.get(url + '/services').json()
assert 'test' in r, 'error: GET /services -> no \'test\' category in answer'
r = r['test']
assert selfadr in r, 'error: GET /services -> no chosen server in answer'
r = r[selfadr]
assert r['state']=='' and 'lastbeat' in r \
    , 'error: GET /services/test -> wrong state returned'

print ('[PASSED]')

#####
testname ('role request test')
r = requests.get(url + '/services/test').json()
assert selfadr in r, 'error: GET /services/test -> no chosen server in answer'
r = r[selfadr]
assert r['state']=='' and 'lastbeat' in r \
    , 'error: GET /services/test -> wrong state returned'

print ('[PASSED]')

#####
testname ('data modification test')
r = requests.put(url + '/services/test/'+selfadr, data={'state':selfnewstate}).json()
assert r['status']=='success', 'error: PUT /services/test/address -> request failed'

print ('[PASSED]')

#####
testname ('specific access test')
assert requests.get(url+'/services/test/'+selfadr).json()['state']==selfnewstate, \
    'error: GET /services/test/address -> wrong state returned'

print ('[PASSED]')

#####
testname ('expiration test')
time.sleep(15)
emptytest()

print ('[PASSED]')

#####
print ('All tests passed.')