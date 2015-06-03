from flask import *
import requests as pyrequests
import json as pyjson
import threading, time
import jsonpickle
import os, sys, platform, shutil, random, string

TASK_STATUS_QUEUED = 'queued'
TASK_STATUS_ASSIGNED = 'assigned'
TASK_STATUS_FAILED = 'failed'
TASK_STATUS_FINISHED = 'finished'

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

# [{'name':'tr1', 'version':'v1'}]
# 'agent' / 'task'
# 7
# http://example.com:0123

def safedel(fname):
    try:
        os.remove(fname)
    except:
        pass

def jsr(method, address, data = {}):
    return getattr(pyrequests, method)(address, data = pyjson.dumps(data), headers = {'Content-type': 'application/json', 'Accept': 'text/plain'})    
    
def jsdec(o):
    return jsonpickle.decode(o)

def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def getFileFromTo(adr, fname):
    with open(fname, 'wb') as handle:
        response = pyrequests.get(adr, stream=True)

        if not response.ok:
            raise Exception('File was not downloaded')

        for block in response.iter_content(1024):
            if block:
                handle.write(block)
                handle.flush()

def preparedir(folder, flush=False):
    if not os.path.exists(folder):
        os.makedirs(folder)
    if not flush: return
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except:
            pass
            
def place_bulk_traits(arroftraits, itemtype, jsonid, dbadr):
    id_fld = itemtype + '_id'
    try:
        for trait in arroftraits:
            existing = jsr('get', dbadr + '/trait/filter', trait)
            existing = existing.json()['result']
            
            tid = None
            if len(existing) > 0:
                tid = existing[0]['id']
            else: 
                tid = jsr('post', dbadr + '/trait', trait).json()['id']
            
            r = jsr('post', dbadr + '/mtm_trait' + itemtype,\
                data = {str(id_fld) : jsonid, 'trait_id' : tid}\
            )
            _ = r.json()['trait_id']
    except Exception as e:
        return jsenc({'status':'failure', 'message':'failed to place traits'}), 422
    return jsenc({'status' : 'success', str(id_fld) : jsonid}), 200

### flask.request related ###

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
    selfaddress = None
    beacon_adapter_cycletime = 10
    beacon = None
    backend_port = None
    
    seterr = False
    geterr = False
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
        thr = threading.Timer(self.beacon_adapter_cycletime, self.beacon_setter_internal)
        thr.daemon = True
        thr.start()
    
    def beacon_setter_internal(self):
        self.seterr = True
        while (self.seterr):
            try:
                if self.selfaddress == None:
                    self.selfaddress = pyrequests.post('/'.join([self.beacon, self.setterEndpoint]), data={'port':self.backend_port, 'state':self.state}).json()['address']
                else:
                    pyrequests.put('/'.join([self.beacon, self.setterEndpoint, self.selfaddress]), data={'state':self.state})
                
                self.seterr = False
                if (not self.seterr) and (not self.geterr):
                    self.state = self.stateNormal
                    
                self.beacon_setter()
            except:
                self.seterr = True
                self.errorBeacon()
                time.sleep(5)

    def beacon_getter(self):
        thr = threading.Timer(self.beacon_adapter_cycletime, self.beacon_getter_internal)
        thr.daemon = True
        thr.start()
        
    def beacon_getter_internal(self):
        self.geterr = True
        while (self.geterr):
            try:
                errorOccured = False
                for sname in self.addresses.keys():
                    r = pyrequests.get(self.beacon + '/services/' + sname)
                    try: self.addresses[sname] = 'http://'+list(r.json().keys())[0]
                    except:
                        errorOccured = True
                        self.errorGeneric(sname)
                
                if errorOccured: raise Exception('Did not retrieve some address')
                
                self.geterr = False
                if (not self.seterr) and (not self.geterr):
                    self.state = self.stateNormal
                    
                self.beacon_getter()
            except:
                self.geterr = True
                self.errorBeacon()
                time.sleep(5)

### Platform-dependent ###
def platform_dependent_on_run(backend_name):
    osname = platform.system()
    if osname == 'Linux':
        os.system("echo $'\033]30;{0}\007'".format(backend_name))
