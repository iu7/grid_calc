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

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/tasks', methods=['POST'])
def taskPlacing():
    try:
        payload = jsdec(request.data.decode('utf-8'))
        uid = payload['uid']
        traits = payload['traits']
        for trait in traits:
            _ = trait['name']
            _ = trait['version']
        
        archive_name = payload['archive_name']
        assert archive_name == secure_filename(archive_name)
        subtask_count = int(payload['subtask_count'])
        max_time = int(payload['max_time'])
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
        
    tid = requests.post(bw['database'] + '/task', \
        data = jsenc({\
            'user_id':uid, \
            'max_time':max_time, \
            'archive_name':archive_name}), \
        headers = {'content-type':'application/json'}).json()['id']
    
    for _ in range (0, subtask_count)
        sid = requests.post(bw['database'] + '/subtask', \
            data = jsenc({
                'task_id':tid, \
                'status':'queued', }), \
            headers = {'content-type':'application/json'}).json()['id']
    
    return place_bulk_traits(traits, 'task', tid, bw['database'])

@app.route('/tasks', methods=['GET'])
def taskViewing():
    try:
        payload = jsdec(request.data.decode('utf-8'))
        uid = payload['uid']
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 400
    
    tasks = None
    try:
        tasks = jsr('get', bw['database'] + '/task/filter', {'user_id':uid}).json()['result']
    except: 
        tasks = []
    
    for task in tasks:
        try: subtasks = jsr('get', bw['database'] + '/subtask/filter', {'task_id':task['id']}).json()['result']
        except: subtasks = []
        for subtask in subtasks:
            try: 
                subtask['agent'] = jsr('get', bw['database'] + '/agent/' + subtask['agent_id']).json()
            except:
                subtask['agent'] = None
            subtask.pop('agent_id', None)
        task['subtasks'] = subtasks
    return jsenc({'status':'success', 'tasks':tasks}), 200
    
@app.route('/tasks/<int:tid>', methods=['DELETE'])
def taskCancelling(tid):
    try:
        payload = jsdec(request.data.decode('utf-8'))
        uid = int(payload['uid'])
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 400
    
    if (jsr('delete', bw['database']+'/task/filter', {'user_id':uid, 'id':tid}).status_code != 200):
        return jsenc({'status':'failure', 'message':'user / task pair unrecognized'}), 422
    
    jsr('delete', bw['database'] + '/subtask/filter', {'task_id':tid})
    jsr('delete', bw['database'] + '/mtm_traittask', {'task_id':tid})
    # IMPORTANT: fill in balancer_backend.cleaner method
    return jsenc({'status':'success'}), 200
    
@app.route('/system/state', methods=['GET'])
def systemViewing():
    return requests.get(bw.beacon + '/services').text
    
################################

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    global bw
    bw = BeaconWrapper(beacon, port, 'services/logic_backend', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    app.run(host = host, port = port)