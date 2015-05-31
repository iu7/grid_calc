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
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(GRID_CALC_ROLE = 'BALANCER_BACKEND')

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = jsdec(request.data.decode('utf-8'))['traits']
        
    nid = requests.post(bw['database'] + '/agent', \
        data = jsenc({}), \
        headers = {'content-type':'application/json'}).json()['id']
        
    return place_bulk_traits(traits, 'agent', nid, bw['database'])
    
@app.route('/nodes/<string:nid>', methods=['PUT'])
def nodesSpecificHandler(nid):
    state = request.form['state'] if 'state' in request.form else ''
    
    if nid in activenodes:
        if 'state' in request.form:
            activenodes[nid].Update(state)
        else:
            activenodes[nid].Update()
    else:
        subtask = requests.get(bw['database']+'/subtask/filter', \
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
    r = requests.get(bw['database']+'/custom/get_free_subtask_by_agent_id', \
        data = {'agent_id':nid})
    if (r.status_code == 200):
        subtask = r.json()
        sid = subtask['id'] #result_archive
        tid = task['task_id']
        task = requests.get(bw['database']+'/task/'+tid).json()
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
        r = requests.put(bw['database']+'/subtask/'+sid, \
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

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/balancer', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    cleaner()
    print(app.config['GRID_CALC_ROLE'])
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)