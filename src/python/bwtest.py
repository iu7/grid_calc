from common.common import BeaconWrapper
from time import sleep
import requests, subprocess, sys, time

beacon = 'http://localhost:1666'
self_port = 1667
self_addr = '127.0.0.1:' + str(self_port)
badadr = 'http://localhost:1650'

name = 'test_service'
target = 'test_target1'
targets = {target}

bw = None
bw2 = None
def TestCreation():
    print ('Running TestCreation...')
    global bw
    bw = BeaconWrapper(beacon, self_port, 'services/' + name, targets)
    assert bw != None, 'TestCreation failed'
    print('TestCreation passed')
    
def TestSetterGood():
    print ('Running TestSetterGood...')
    bw.beacon_setter()
    time.sleep(3)
    assert requests.get(beacon + '/services').json()[name][self_addr]['state'] == bw.stateNormal, 'TestSetterGood failed'
    assert bw.state == bw.stateNormal, 'TestSetterGood failed'
    print('TestSetterGood passed')
    
def TestSetterBad():
    print ('Running TestSetterBad...')
    bw.beacon = badadr
    time.sleep(30)
    
    assert bw.state == bw.stateError
    try:
        st = requests.get(beacon + '/services').json()[name][self_addr]['state']
    except:
        bw.beacon = beacon
        print('TestSetterBad passed')
        return
    bw.beacon = beacon
    raise 'TestSetterBad failed'
    
def TestGetterGood():
    print ('Running TestGetterGood...')
    global bw2
    bw2 = BeaconWrapper(beacon, self_port + 1, 'services/' + target, {})
    bw2.beacon_setter()
    bw.beacon_getter()
    time.sleep(10)
    assert bw[target] == 'http://127.0.0.1:'+str(self_port+1), 'TestGetterGood failed'
    print('TestGetterGood passed')

def TestGetterBad():
    print ('Running TestGetterBad...')
    global bw2
    bw2.beacon = badadr
    time.sleep(40)
    print (bw.state)
    assert bw.state == bw.stateError, 'TestGetterBad failed'
    print('TestGetterBad passed')


DETACHED_PROCESS = 8
def run(str):
    subprocess.Popen('py ' + str, creationflags=DETACHED_PROCESS, close_fds=True)
    
if __name__ == '__main__':
    run('beacon_backend/beacon_backend.py 1666')
    time.sleep(5)
    
    TestCreation()
    TestSetterGood()
    TestSetterBad()
    TestGetterGood()
    TestGetterBad()