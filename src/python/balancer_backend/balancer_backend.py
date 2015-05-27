from flask import *
import jsonpickle
import datetime
import threading
import time
import sys
import requests
from werkzeug import secure_filename
import os

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

defaultbeacon = 'http://127.0.0.1:666'
defaultport = 671
beacon_adapter_cycletime = 3

port = None

beacon = None
database = None
stateNormal = 'Operating normally'
stateNoBeacon = 'Unable to find beacon'
stateNoDatabase = 'Unable to find active database'
state = stateNormal

selfaddress = None

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = request.form['traits'] if 'traits' in request.form else '{}'
    traits = jsdec(traits)
    
    nid = request.post(database + '/agent', \
        data = jsenc({}), \
        headers = {'content-type':'application/json'}).json()['id']
    
    for trait in traits.items():
        jstrait = jsenc(trait)
        existing = request.get(database + '/trait/filter', \
            data = jstrait, \
            headers = {'content-type':'application/json'}).json()['result']
        tid = None
        if existing:
            global tid
            tid = existing[0]['id']
        else:
            global tid
            tid = reqiest.post(database + '/trait', \
                data = jstrait, \
                headers = {'content-type':'application/json'}).json()['id']
        request.post(database+'/mtm_traitagent', \
            data = jsenc({'agent_id':nid, 'trait_id':tid}), \
            headers =  {'content-type':'application/json'})
            
    return jsenc({'status':'success', 'nodeid':nid}), 200
    
@app.route('/nodes/<string:nid>', methods=['PUT'])
def nodesSpecificHandler(nid):
    state = request.form['state'] if 'state' in request.form else ''
    
    if nid in activenodes:
        if 'state' in request.form:
            activenodes[nid].Update(state)
        else:
            activenodes[nid].Update()
    else:
        subtask = request.get(database+'/subtask/filter', \
            data = jsenc({'agent_id':nid}), \
            headers = {'content-type':'application/json'}).json()['result'][0]
        sid = subtask['id']
        tid = subtask['task_id']            
        
        activenodes[nid] = ActiveNode(state, tid, sid, nid)
    
    return jsenc({'status':'success'}), 200
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    if not 'nodeid' in request.form: return '', 422
    nid = request.form['nodeid']
    r = request.get(database+'/custom/free_task_by_agent_id', \
        data = {'agent_id':nid})
    if (r.status_code == 200):
        subtask = r.json()
        sid = subtask['id'] #result_archive
        tid = task['task_id']
        task = request.get(database+'/task/'+tid).json()
        archive_name = task['archive_name']
        
        activenodes[nid] = ActiveNode('Was assigned task', tid, sid, nid)
        
        return jsenc({'archive_name':archive_name}), 200
    else:
        return jsenc({'status':'failure', 'message':'no suitable tasks'}),404
    
@app.route('/tasks/<string:taskid>', methods=['POST'])
def submitTaskHandler(taskid):
    if not 'nodeid' in request.form: return '', 422
    nid = request.form['nodeid']
    filename = request.form['filename']
    if nid in activenodes: 
        sid = activenodes[nid].tid
        r = request.put(database+'/subtask/'+sid, \
            data = jsenc({'archive_name':filename, 'status':'finished'}))
    return jsenc({'status':'success'}), 200

################################

def cleaner():
    return 0


################################

activenodes = {}

class ActiveNode:
    tid = None
    nid = None
    sid = None
    lastbeat = None
    state = None
    def __init__(self, state, tid, sid, nid):
        self.state = state
        self.lastbeat = datetime.datetime.now()
        self.tid = tid
        self.sid = sid
        self.nid = nid
    def __getstate__(self):
        state = self.__dict__.copy()
        for key in state:
            state[key] = str(state[key])
        return state
    def update(self, state):
        self.state = state
        self.lastbeat = datetime.datetime.now()
    def update(self):
        self.lastbeat = datetime.datetime.now()

################################

def jsdec(o):
    return jsonpickle.decode(o)

def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def beacon_getter():
    global database
    gotadr = False
    oldadr = database
    
    while (not gotadr):
        try:
            nobeacon = True
            nodatabase = True
            
            r = requests.get(beacon + '/services/database')
            nobeacon = False
            database = 'http://'+list(r.json().keys())[0]
            nodatabase = False
            if (database != oldadr):
                print ('Database address set to ' + str(database))
                databaseUpMsg()
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_getter)
            thr.daemon = True
            thr.start()
            gotadr = True
            state = stateNormal
            databaseUpMsg()
            beaconUpMsg()
        except:
            if (nobeacon):
                state = stateNoBeacon
                beaconDownMsg()
            if (nodatabase):
                state = stateNoDatabase   
                databaseDownMsg()
            time.sleep(3)

def beacon_setter():
    messaged = False
    global selfaddress
    global port
    while (not messaged):
        try:
            if selfaddress == None:
                selfaddress = requests.post(beacon + '/services/balancer', data={'port':port, 'state':state}).json()['address']
            else:
                requests.put(beacon + '/services/balancer/' + selfaddress, data={'state':state})
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_setter)
            thr.daemon = True
            thr.start()
            messaged = True
            beaconUpMsg()
        except:
            beaconDownMsg()

dbmsg = False
def databaseDownMsg():
    global dbmsg
    if (not dbmsg): 
        print ('Database is down. Waiting to reconnect.')
        dbmsg = True

def databaseUpMsg():
    global dbmsg
    if (dbmsg): 
        print ('Database is back up.')
        dbmsg = False
        

bcmsg = False
def beaconDownMsg():
    global bcmsg
    if (not bcmsg): 
        print ('Beacon is down. Waiting to reconnect.')
        bcmsg = True

def beaconUpMsg():
    global bcmsg
    if (bcmsg): 
        print ('Beacon is back up.')
        bcmsg = False
        
if __name__ == '__main__':
    global port
    port = defaultport
    beacon = defaultbeacon
    if len(sys.argv) == 1:
        print ('Beacon address defaulted to ' + str(beacon))
        print ('Port number defaulted to ' + str(port))
    elif len(sys.argv) == 2:
        beacon = 'http://'+sys.argv[1]
        print ('Beacon address set to ' + str(beacon))
        print ('Port number defaulted to ' + str(port))
    elif len(sys.argv) == 3:
        beacon = 'http://'+sys.argv[1]
        port = int(sys.argv[2])
        print ('Beacon address set to ' + str(beacon))
        print ('Port number set to ' + str(port))
    
    beacon_setter()
    beacon_getter()
    cleaner()
    app.run(host = '0.0.0.0', port = port)