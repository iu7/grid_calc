import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from flask import *
import jsonpickle
import datetime
import threading
import time
import requests
from werkzeug import secure_filename
import tempfile
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'NODE_FRONTEND')
app.config.update(UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), '_'.join([app.config['GRID_CALC_ROLE'], 'upload'])))
app.config.update(ALLOWED_EXTENSIONS = ['tar.gz'])

msg_required_params_fmt = 'Required: {0}'
msg_error_params_fmt = 'Error parameters: {0}'

def allowed_file(filename):
    if '.' in filename:
        for ext in app.config['ALLOWED_EXTENSIONS']:
            if filename[::-1][:len(ext)] == ext[::-1]:
                return True
    return False

def is_key_valid(key):
    if key:
        resp = jsr('get', bw['database'] + '/agent/filter', {'key': key})
        return len(resp.json()['result']) > 0
    return False

def is_key_id_valid(key, id_):
    if key and id_:
        resp = jsr('get', bw['database'] + '/agent/filter', {'key': key, 'id': id_})
        return len(resp.json()['result']) > 0
    return False

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    r = jsr('post', bw['balancer'] + '/nodes', request.get_json()) 
    return r.text, r.status_code
    
@app.route('/nodes/<int:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    keyold = get_url_parameter('key_old')
    if not is_key_id_valid(keyold, nodeid):
        return msg_required_params_fmt.format('valid "nodeid", "key" cortege'), 422

    ### Case 1: update keys
    if has_url_parameter('key'):
        key = get_url_parameter('key')
        dr = jsr('put', bw['database'] + '/agent/filter', {'id': nodeid, 'key': keyold, 'changes': {'key' : key}})
        if int(dr.json()['count']) == 0:
            return msg_required_params_fmt.format('valid (id(in endpont), "key", "key_old") cortege'), 422
        return jsenc('status':'success'), 200
    else:
        return msg_required_params_fmt.format('valid (id(in endpont), "key", "key_old") cortege'), 422
    
    ### Case 2: update state
    r = requests.put(bw['balancer'] + '/nodes/' + str(nodeid), data = {'state': get_url_parameter('state')})
    return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    key = get_url_parameter('key')
    nodeid = get_url_parameter('nodeid')
    if not is_key_id_valid(key, nodeid):
        return msg_required_params_fmt.format('valid "nodeid", "key" cortege'), 422
    r = requests.get(bw['balancer'] + '/tasks/newtask', data = {'nodeid': nodeid})
    return r.text, r.status_code
    
@app.route('/tasks', methods=['POST'])
def submitTaskHandler():
    key = get_url_parameter('key')
    nodeid = get_url_parameter('nodeid')
    if not is_key_id_valid(key, nodeid):
        return msg_required_params_fmt.format('valid "id", "key" cortege'), 422

    fl = request.files['file']
    if not fl:
        return msg_required_params_fmt.format('"file" as file parameter'), 422

    if allowed_file(fl.filename):
        filename = secure_filename(fl.filename)
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        fl.save(fullpath)
        
        r = requests.post(bw['filesystem'] + '/static',
            files = {'file':open(fullpath, 'rb')})
        
        if r.status_code == 200:
            r = requests.post(bw['balancer'] + '/tasks', data = {'filename': r.json()['name'], 'nodeid': nodeid})

        os.unlink(fullpath)
        return r.text, r.status_code
    else:
        return msg_error_params_fmt.format(\
            '"file". Allowed extensions: {0}'.format(','.join(app.config['ALLOWED_EXTENSIONS']))\
        ), 422

@app.route('/getfile', methods=['GET'])
def getfile():
    key = get_url_parameter('key')
    nodeid = get_url_parameter('nodeid')
    if not is_key_id_valid(key, nodeid):
        return msg_required_params_fmt.format('valid "id", "key" cortege'), 422
    
    filename = get_url_parameter('archive_name')
    if not filename:
        return msg_required_params_fmt.format('valid "id", "key", "archive_name" cortege'), 422
    
    resp = jsr('get', bw['database'] + '/subtask/filter', {'agent_id': nodeid})
    if resp.status_code == 200:
        if len(resp.json()['result']) == 0:
            return 'You are not assigned to any task', 403

    subtasks = resp.json()['result']
    task_ids = [s['task_id'] for s in subtasks]
    resp = jsr('get', bw['database'] + '/task/arrayfilter', {'archive_name': [filename], 'id': task_ids})
    if resp.status_code != 200:
        return 'You are not assigned to this task', 403

    try:
        getFileFromTo(bw['filesystem']+'/static/'+filename, os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return 'Error: {0}'.format(str(e)), 500

    
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/node_frontend', {'balancer', 'filesystem', 'database'})
    
    bw.beacon_setter()
    bw.beacon_getter()
 
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        print('Creating directories for temp upload files: {0}'.format(app.config['UPLOAD_FOLDER']))
        os.makedirs(app.config['UPLOAD_FOLDER'])

    print(app.config['GRID_CALC_ROLE'])
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)