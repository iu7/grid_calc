from flask import *
import requests as pyrequests
import threading, time
import sys
import jsonpickle

def response_builder(r, s):
    resp = None
    try:
        resp = jsonify(r)
        resp.status_code = s
    except RuntimeError as e:
        resp = s
    return resp

def get_url_parameter(name, request = request):
    rjson = request.get_json()
    if name in request.args:
        return request.args[name]
    elif name in request.form:
        return request.form[name]
    elif name in request.headers:
        return request.headers[name]
    elif rjson:
        if name in rjson:
            return rjson[name]
    else:
        return None
                                                                             
def has_url_parameter(name):
    rjson = request.get_json()
    part = (name in request.args) or (name in request.form) or (name in request.headers)
    return ((name in rjson) or part) if rjson else part

def api_func(addr, f):
    return '/'.join([addr, f])

### Startup related ###
def parse_db_argv(argv, custmom_msg = ''):
    try:
        shard_number = int(sys.argv[1])
        beacon = 'http://'+sys.argv[2]
        dbhost, dbport = sys.argv[3].split(':')
        dbport = int(dbport)
        port = int(sys.argv[4])
    except Exception as e:
        print('Usage: {0} SHARD_NUMBER beacon_host:beacon_port dbhost:dbport port {1}'.format(sys.argv[0], custmom_msg))
        sys.exit()
    return shard_number, beacon, dbhost, dbport, port

def parse_argv(argv, custmom_msg = ''):
    try:
        beacon = 'http://'+sys.argv[1]
        port = int(sys.argv[2])
    except Exception as e:
        print('Usage: {0} beacon_host:beacon_port port {1}'.format(sys.argv[0], custmom_msg))
        sys.exit()
    return beacon, port

def parse_beacon_argv(argv, custmom_msg = ''):
    try:
        port = int(sys.argv[1])
    except Exception as e:
        print('Usage: {0} port {1}'.format(sys.argv[0], custmom_msg))
        sys.exit()
    return port

### Beacon related ###

class BeaconWrapper:
    beacon_port = None
    selfaddress = None
    beacon_adapter_cycletime = 10
    beacon = None
    backend_port = None
    stateNormal = 'Operating normally'
    stateError = 'Connection issues'
    setterEndpoint = None
    
    addresses = {}
    
    def __init__(self, beacon, backend_port, endpoint, targets = None):
        self.beacon = beacon
        self.state = self.stateNormal
        self.backend_port = backend_port
        self.setterEndpoint = endpoint
        for target in (targets if targets != None else {}):
            self.addresses[target] = None

    def errorBeacon(self):
        self.state = self.stateError
        print ('Unable to reach beacon')
    
    def errorGeneric(self, service):
        self.state = self.stateError
        print ('No ' + service + ' found') 
    
    def beacon_setter(self):
        self.messaged = False
        while (not self.messaged):
            try:
                if self.selfaddress == None:
                    self.selfaddress = pyrequests.post('/'.join([self.beacon, self.setterEndpoint]), data={'port':self.backend_port, 'state':self.state}).json()['address']
                else:
                    pyrequests.put('/'.join([self.beacon, self.setterEndpoint, self.selfaddress]), data={'state':self.state})
                
                thr = threading.Timer(self.beacon_adapter_cycletime, self.beacon_setter)
                thr.daemon = True
                thr.start()
                
                self.state = self.stateNormal
                self.messaged = True
            except:
                self.errorBeacon()
                time.sleep(5)
                
    def beacon_getter(self):
        gotadr = False
        errorOccured = False
        while (not gotadr):
            try:
                for sname in self.addresses.keys():
                    r = pyrequests.get(self.beacon + '/services/' + sname)
                    try: self.addresses[sname] = 'http://'+list(r.json().keys())[0]
                    except:
                        errorOccured = True
                        self.errorGeneric(sname)
                
                thr = threading.Timer(self.beacon_adapter_cycletime, self.beacon_getter)
                thr.daemon = True
                thr.start()
                gotadr = True
                if not errorOccured:
                    self.state = self.stateNormal
            except:
                self.errorBeacon()
                time.sleep(5)
        