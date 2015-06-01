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
from common.common import *
import tempfile

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'NODE_FRONTEND')
app.config.update(UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), '_'.join([app.config['GRID_CALC_ROLE'], 'upload'])))
app.config.update(ALLOWED_EXTENSIONS = ['zip'])

msg_required_params_fmt = 'Required: {0}'
msg_error_params_fmt = 'Error parameters: {0}'

def allowed_file(filename):
    if '.' in filename:
        if filename[::-1].split('.')[0][::-1] in app.config['ALLOWED_EXTENSIONS']:
            return True
    return False

def save_file_locally(filename):
    filename = secure_filename(fl.filename)
    fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    fl.save(fullpath)

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    if 'key' not in request.data:
        return msg_required_params_fmt.format('"key"'), 422
    r = jsr('post', bw['balancer'] + '/nodes', data = request.data) 
    return r.text, r.status_code
    
@app.route('/nodes/<string:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    if 'key_new' not in request.data and 'key_old' not in request.data:
        return msg_required_params_fmt.format('"key_old", "key"'), 422
    r = jsr('put', bw['balancer'] + '/nodes/' + nodeid, data = request.data) 
    return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    if 'key' not in request.data:
        return msg_required_params_fmt.format('"key"'), 422
    r = jsr('get', bw['balancer'] + '/tasks/newtask', data = request.data)
    
    arch = r.get_json()['archive_name']
    fr = requests.get(bw['filesystem']  + '/static/{0}'.format(arch))
    if fr.status_code != 200:
        return r.text, 500
    save_file_locally(requests['file'])

    return r.text, r.status_code
    
@app.route('/tasks/<string:taskid>', methods=['POST'])
def submitTaskHandler(taskid):
    if 'key' not in request.data:
        return msg_required_params_fmt.format('"key"'), 422

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
            r = jsr('post', bw['balancer'] + '/tasks/' + taskid, data = {'filename': r.json()['name']})

        os.unlink(fullpath)
        return r.text, r.status_code
    else:
        return msg_error_params_fmt.format(\
            '"file". Allowed extensions: {0}'.format(','.join(app.config['ALLOWED_EXTENSIONS']))\
        )
    
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/node_frontend', {'balancer', 'filesystem'})
    
    bw.beacon_setter()
    bw.beacon_getter()
 
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        print('Creating directories for temp upload files: {0}'.format(app.config['UPLOAD_FOLDER']))
        os.makedirs(app.config['UPLOAD_FOLDER'])

    print(app.config['GRID_CALC_ROLE'])
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)