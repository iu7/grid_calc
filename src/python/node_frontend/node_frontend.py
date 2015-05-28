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

bw = None

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    r = requests.post(bw.addresses['balancer'] + '/nodes', \
        data = request.data, \
        headers = {'content-type':'application/json'})
    return r.text, r.status_code
    
@app.route('/nodes/<string:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    r = requests.put(bw.addresses['balancer'] + '/nodes/' + nodeid, \
        data = request.data, \
        headers = {'content-type':'application/json'})
    return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    r = requests.get(bw.addresses['balancer'] + '/tasks/newtask', \
        data = request.data, \
        headers = {'content-type':'application/json'})
    return r.text, r.status_code
    
@app.route('/tasks/<string:taskid>', methods=['POST'])
def submitTaskHandler(taskid):
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fullpath)
        
        r = requests.post(bw.addresses['fileserver'] + '/static',
            files = {'file':open(fullpath, 'rb')})
        
        r = requests.post(bw.addresses['balancer'] + '/tasks/'+taskid, \
            data = {'filename':nid}, \
            headers = {'content-type':'application/json'})
        return r.text, r.status_code
    else:
        return '', 422

def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)
    
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    global bw
    bw = BeaconWrapper(beacon, port, 'services/node_frontend', {'balancer', 'filesystem'})
    
    bw.beacon_setter()
    bw.beacon_getter()
    app.run(host = host, port = port)