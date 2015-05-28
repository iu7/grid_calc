import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from flask import *
import jsonpickle
import json
import datetime
import threading
import time
import requests
from werkzeug import secure_filename

port = None
selfaddress = None
beacon_adapter_cycletime = 10
beacon = None
database = None
stateNormal = 'Operating normally'
stateError = 'Connection issues'
state = stateNormal

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = jsdec(request.data.decode('utf-8'))['traits']
    
    print (str(traits))
    
    nid = requests.post(database + '/agent', \
        data = jsenc({}), \
        headers = {'content-type':'application/json'}).json()['id']
    
    try:
        for trait in traits:
            jstrait = jsenc(trait)
            existing = requests.get(database + '/trait/filter', \
                data = jstrait, \
                headers = {'content-type':'application/json'}).json()['result']
            tid = existing[0]['id'] if existing else \
                reqiests.post(database + '/trait', \
                    data = jstrait, \
                    headers = {'content-type':'application/json'}).json()['id']
            requests.post(database+'/mtm_traitagent', \
                data = jsenc({'agent_id':nid, 'trait_id':tid}), \
                headers =  {'content-type':'application/json'})
    except Exception as e:
        print (str(e))   
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
        subtask = requests.get(database+'/subtask/filter', \
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
    r = requests.get(database+'/custom/free_task_by_agent_id', \
        data = {'agent_id':nid})
    if (r.status_code == 200):
        subtask = r.json()
        sid = subtask['id'] #result_archive
        tid = task['task_id']
        task = requests.get(database+'/task/'+tid).json()
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
        r = requests.put(database+'/subtask/'+sid, \
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
    global beacon
    global state
    gotadr = False
    
    while (not gotadr):
        try:
            r = requests.get(beacon + '/services/database')
            try: database = 'http://'+list(r.json().keys())[0]
            except: errorDatabase()
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_getter)
            thr.daemon = True
            thr.start()
            gotadr = True
            state = stateNormal
        except:
            errorBeacon()
            time.sleep(5)

def beacon_setter():
    messaged = False
    global selfaddress
    global port
    global beacon
    global state
    while (not messaged):
        try:
            if selfaddress == None:
                selfaddress = requests.post(beacon + '/services/balancer', data={'port':port, 'state':state}).json()['address']
            else:
                requests.put(beacon + '/services/balancer/' + selfaddress, data={'state':state})
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_setter)
            thr.daemon = True
            thr.start()
            
            state = stateNormal
            messaged = True
        except:
            errorBeacon()
            time.sleep(5)

def errorBeacon():
    state = stateError
    print ('Unable to reach beacon')
def errorDatabase():
    state = stateError
    print ('No database found')

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    try:
        beacon = 'http://'+sys.argv[1]
        port = int(sys.argv[2])
    except Exception as e:
        print('Usage: {0} beacon_host:beacon_port port'.format(sys.argv[0]))
        sys.exit()

    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    beacon_setter()
    beacon_getter()
    cleaner()
    app.run(host = host, port = port)