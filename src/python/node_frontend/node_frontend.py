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
    
@app.route('/nodes/<int:nid>', methods=['PUT'])
def nodesSpecificHandler(nid):
    if not has_url_parameter('key'):
        return msg_required_params_fmt.format('valid "nid", "key" cortege'), 422

    #variants:
    #1 -- key, key_old
    #2 -- key, node_status
    #3 -- key, subtask_id, status
    key = get_url_parameter('key')
    if has_url_parameter('key_old'):
        # Case 1: update keys
        keyold = get_url_parameter('key_old')

        if not is_key_id_valid(keyold, nid):
            return msg_required_params_fmt.format('valid "nid", "key" cortege'), 422

        dr = jsr('put', bw['database'] + '/agent/filter', {'id': nid, 'key': keyold, 'changes': {'key' : key}})
        if int(dr.json()['count']) == 0:
            return msg_required_params_fmt.format('valid (nid(in endpont), "key", "key_old") cortege'), 422
        return jsenc({'status': 'success'}), 200
    elif has_url_parameter('node_status'):
        # Case 2: update node_status
        br = requests.put(bw['balancer'] + '/nodes/' + str(nid), data = {'node_status': node_status})
        return br.text, br.status_code
    else:
        # Case 3: update task status
        status = get_url_parameter('status')
        sid = get_url_parameter('subtask_id')
        if not (status and sid):
            return msg_required_params_fmt.format('status, subtask_id')
        r = requests.put(bw['balancer'] + '/nodes/' + str(nid), data = {'status': get_url_parameter('status'), 'subtask_id': sid})
        return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    key = get_url_parameter('key')
    nid = get_url_parameter('node_id')
    if not is_key_id_valid(key, nid):
        return msg_required_params_fmt.format('valid "nid", "key" cortege'), 422
    r = requests.get(bw['balancer'] + '/tasks/newtask', data = {'node_id': nid})
    return r.text, r.status_code
    
@app.route('/tasks', methods=['POST'])
def submitTaskHandler():
    key = get_url_parameter('key')
    nid = get_url_parameter('node_id')
    if not is_key_id_valid(key, nid):
        return msg_required_params_fmt.format('valid "id", "key" cortege'), 422

    fl = request.files['file']
    if not fl:
        return msg_required_params_fmt.format('"file" as file parameter'), 422

    status = get_url_parameter('status') # can be failed, but still contain some results
    sid = get_url_parameter('subtask_id')
    if not (status and sid):
        return msg_required_params_fmt.format('status, subtask_id'), 422

    if allowed_file(fl.filename):
        filename = secure_filename(fl.filename)
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        fl.save(fullpath)
        
        r = requests.post(bw['filesystem'] + '/static', files = {'file':open(fullpath, 'rb')})
        
        if r.status_code == 200:
            r = requests.post(bw['balancer'] + '/tasks', data = {'filename': r.json()['name'], 'node_id': nid, 'subtask_id': sid, 'status': status})

        os.unlink(fullpath)
        return r.text, r.status_code
    else:
        return msg_error_params_fmt.format(\
            '"file". Allowed extensions: {0}'.format(','.join(app.config['ALLOWED_EXTENSIONS']))\
        ), 422

@app.route('/getfile', methods=['GET'])
def getfile():
    key = get_url_parameter('key')
    nid = get_url_parameter('node_id')
    if not is_key_id_valid(key, nid):
        return msg_required_params_fmt.format('valid "id", "key" cortege'), 422
    
    filename = get_url_parameter('archive_name')
    if not filename:
        return msg_required_params_fmt.format('archive_name'), 422
    
    sid = get_url_parameter('subtask_id')
    if not sid:
        return msg_required_params_fmt.format('subtask_id'), 422


    resp = jsr('get', bw['database'] + '/subtask/filter', {'archive_name': filename, 'id': sid})
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