from flask import *
import requests as pyrequests
import threading, time
import sys
import jsonpickle

# [{'name':'tr1', 'version':'v1'}]
# 'agent' / 'task'
# 7
# http://example.com:0123

def jsr(method, address, data):
    return getattr(pyrequests, method)(data = data, headers = {'content-type':'application/json'})

def place_bulk_traits(arroftraits, itemtype, jsonid, dbadr):
    traits = jsdec(request.data.decode('utf-8'))['traits']
        
    nid = requests.post(dbadr + '/' + itemtype, \
        data = jsenc({}), \
        headers = {'content-type':'application/json'}).json()['id']
        
    try:
        for trait in traits:
            jstrait = jsenc(trait)
            existing = requests.get(dbadr + '/trait/filter', \
                data = jstrait, \
                headers = {'content-type':'application/json'})
            existing = existing.json()['result'] if existing.status_code == 200 else []
            
            tid = existing[0]['id'] if existing else \
                requests.post(dbadr + '/trait', \
                    data = jstrait, \
                    headers = {'content-type':'application/json'}).json()['id']
            
            requests.post(dbadr+'/mtm_trait'+itemtype, \
                data = jsenc({(itemtype + '_id'):nid, 'trait_id':tid}), \
                headers =  {'content-type':'application/json'}).json()['trait_id']
    except Exception as e:
        return jsenc({'status':'failure'}), 422
    return jsenc({'status':'success', (itemtype + '_id'):nid}), 200

def jsdec(o):
    return jsonpickle.decode(o)

def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

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
def parse_db_argv(argv):
    try:
        beacon = 'http://'+sys.argv[1]
        dbhost, dbport = sys.argv[2].split(':')
        dbport = int(dbport)
        port = int(sys.argv[3])
    except Exception as e:
        print('Usage: {0} beacon_host:beacon_port dbhost:dbport port'.format(sys.argv[0]))
        sys.exit()
    return beacon, dbhost, dbport, port

def parse_argv(argv):
    try:
        beacon = 'http://'+sys.argv[1]
        port = int(sys.argv[2])
    except Exception as e:
        print('Usage: {0} beacon_host:beacon_port port'.format(sys.argv[0]))
        sys.exit()
    return beacon, port

def parse_beacon_argv(argv):
    try:
        port = int(sys.argv[1])
    except Exception as e:
        print('Usage: {0} port'.format(sys.argv[0]))
        sys.exit()
    return port

### Beacon related ###

class BeaconWrapper:
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

    def __getitem__(self,index):
        return self.addresses[index]
        
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
        