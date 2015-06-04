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
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'BALANCER_BACKEND')

#UPLOAD_FOLDER = '/uploads'
#ALLOWED_EXTENSIONS = set(['zip'])

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = request.get_json()['traits']
    key = get_url_parameter('key')
    nidr = jsr('post', bw['database'] + '/agent', {'key': key})
    if nidr.status_code == 200:
        nid = nidr.json()['id']
    else:
        return nidr.text, nidr.status_code
    return place_bulk_traits(traits, 'agent', nid, bw['database'])

@app.route('/nodes/<int:nid>', methods=['PUT'])
def nodesSpecificHandler(nid):
    if not 'status' in request.form: return 'Required: status', 422
    status = request.form['status']
    try:
        if nid in activenodes:
            activenodes[nid].update(status)
        else:
            subtask = jsr('get', bw['database']+'/subtask/filter', {'agent_id':nid}).json()['result'][0]
            sid = subtask['id']
            tid = subtask['task_id']
            maxtime = subtask['max_time']
            activenodes[nid] = ActiveNode(status, tid, sid, nid, maxtime)
        n = activenodes[nid]
        resp = jsr('put', bw['database'] + '/subtask/{0}'.format(n.sid), {'status': status})
        return jsenc({'status':'success'}), 200
    except:
        return jsenc({'status':'failure', 'message':'task was cancelled or reassigned'}), 404
        
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    if not 'nodeid' in request.form: return 'Required: nodeid', 422
    nid = request.form['nodeid']
    r = requests.get(bw['database']+'/custom/get_free_subtask_by_agent_id', \
        data = {'agent_id':nid})
    if (r.status_code == 200):
        subtask = r.json()
        sid = subtask['id']
        tid = subtask['task_id']
        task = requests.get(bw['database']+'/task/'+str(tid)).json()
        archive_name = task['archive_name']
        max_time = task['max_time']
        
        activenodes[nid] = ActiveNode('Was assigned task', tid, sid, nid, max_time)
        
        return jsenc({'archive_name':archive_name, 'max_time': max_time}), 200
    else:
        return jsenc({'status':'failure', 'message':'no suitable tasks'}),404
    
@app.route('/tasks', methods=['POST'])
def submitTaskHandler():
    if not (('nodeid' in request.form) and ('filename' in request.form) and ('status' in request.form)): 
        return 'Required: nodeid, filename, status', 422
    nid = request.form['nodeid']
    filename = request.form['filename']
    status = request.form['status']
    if nid in activenodes: 
        sid = activenodes[nid].sid
        r = jsr('put', bw['database']+'/subtask/'+str(sid), {'archive_name':filename, 'status':status})
        return jsenc({'status':'success'}), 200
    return jsenc({'message': 'task is dropped'}), 422

################################

def actualityCheck():
    try:
        sts = jsr('get', bw['database']+'/subtask/filter', {'status':TASK_STATUS_ASSIGNED}).json()['result']
    except:
        print("Error while trying to get list of actual tasks")
        return
        
    now = datetime.datetime.now()
    for st in sts:
        try:
            stid = st['id']
            nid = st['agent_id']
            if nid in activenodes:
                if activenodes[nid].stid == stid:
                    n = activenodes[nid]
                    if (now - n.lastbeat).total_seconds() > n.maxtime:
                        jsr('put', bw['database']+'/subtask/filter', {'status':TASK_STATUS_ASSIGNED, 'id':stid, 'agent_id':nid, \
                            'changes':{'status':TASK_STATUS_QUEUED, 'agent_id':None}})
                else:
                    activenodes.pop(nid, '')
            else:
                activenodes[nid] = ActiveNode('Was assigned task', tid, sid, nid, max_time)
        except Exception as e:
            print('During handling of a subtask cleaning:')
            print(e)
            pass
                

def actualityChecker():
    actualityCheck()
    
    thr = threading.Timer(60, actualityChecker)
    thr.daemon = True
    thr.start()


################################

activenodes = {}

class ActiveNode:
    tid = None
    nid = None
    sid = None
    lastbeat = None
    maxtime = None
    status = None
    def __init__(self, status, tid, sid, nid, maxtime):
        self.status = status
        self.lastbeat = datetime.datetime.now()
        self.tid = tid
        self.sid = sid
        self.nid = nid
        self.maxtime = maxtime
    def __getstatus__(self):
        status = self.__dict__.copy()
        for key in status:
            status[key] = str(status[key])
        return status
    def update(self, status):
        self.status = status
        self.lastbeat = datetime.datetime.now()
    def update(self):
        self.lastbeat = datetime.datetime.now()

################################

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/balancer', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    actualityChecker()
    print(app.config['GRID_CALC_ROLE'])
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)