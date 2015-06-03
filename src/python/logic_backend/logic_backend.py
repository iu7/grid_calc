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
app.config.update(GRID_CALC_ROLE = 'LOGIC_BACKEND')

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['tar.gz'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config.update(DEBUG = True)

@app.route('/traits', methods=['GET'])
def traitsViewing():
    traits = jsr('get', bw['database'] + '/trait').json()['result']
    traits = list(map(lambda x:{'name':x['name'], 'version':x['version']}, traits))
    return jsenc({'result':traits}), 200

@app.route('/tasks', methods=['POST'])
def taskPlacing():
    try:
        payload = request.get_json()
        uid = payload['uid']
        traits = payload['traits']
        task_name = payload['task_name']
        for trait in traits:
            assert 'name' in trait and 'version' in trait
        
        archive_name = payload['archive_name']
        subtask_count = int(payload['subtask_count'])
        max_time = int(payload['max_time'])
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    tid = jsr('post', bw['database'] + '/task', \
        {'user_id':uid, \
        'max_time':max_time, \
        'task_name':task_name, \
        'archive_name':archive_name \
        }).json()['id']

    for _ in range (0, subtask_count):
        sid = jsr('post', bw['database'] + '/subtask', \
            {'task_id':tid, \
            'status':TASK_STATUS_QUEUED, \
            }).json()['id']
        
    return place_bulk_traits(traits, 'task', tid, bw['database'])

@app.route('/tasks', methods=['GET'])
def taskViewing():
    try:
        payload = request.get_json()
        uid = payload['uid']
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    tasks = None
    try:
        tasks = jsr('get', bw['database'] + '/task/filter', {'user_id':uid}).json()['result']
    except: 
        tasks = []
    
    taskpars = []
    for task in tasks:
        taskpar = {}
        subtasks = jsr('get', bw['database'] + '/subtask/filter', {'task_id':task['id']}).json()['result']
        traitids = jsr('get', bw['database'] + '/mtm_traittask/filter', {'task_id':task['id']}).json()['result']
        traitids = list(map(lambda x: x['trait_id'], traitids))
        traits = jsr('get', bw['database'] + '/trait/arrayfilter', {'id':traitids}).json()['result']
        traits = list(map(lambda x: x['name'] + ' ' + x['version'], traits))
        
        taskpar['taskname'] = task['task_name']
        taskpar['traits'] = traits
        taskpar['statuses'] = []
        taskpar['id'] = task['id']
        taskpar['dateplaced'] = None
        for subtask in subtasks:
            if taskpar['dateplaced'] is None:
                taskpar['dateplaced'] = subtask['dateplaced']
            if (subtask['status'] == TASK_STATUS_FINISHED or subtask['status'] == TASK_STATUS_FAILED and subtask['archive_name']):
                taskpar['statuses'].append({'result':subtask['archive_name'], 'status' : subtask['status']})
            else:
                taskpar['statuses'].append({'status':subtask['status']})
        
        taskpars.append(taskpar)
    return jsenc({'status':'success', 'tasks':taskpars}), 200
    
@app.route('/tasks/<int:tid>', methods=['DELETE'])
def taskCancelling(tid):
    try:
        payload = jsdec(request.data.decode('utf-8'))
        uid = int(payload['uid'])
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    if (jsr('delete', bw['database']+'/task/filter', {'user_id':uid, 'id':tid}).status_code != 200):
        return jsenc({'status':'failure', 'message':'user / task pair unrecognized'}), 422
    
    jsr('delete', bw['database'] + '/subtask/filter', {'task_id':tid})
    jsr('delete', bw['database'] + '/mtm_traittask/filter', {'task_id':tid})
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
    
    bw = BeaconWrapper(beacon, port, 'services/logic_backend', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)