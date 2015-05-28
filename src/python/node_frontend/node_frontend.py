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


port = None
selfaddress = None
beacon_adapter_cycletime = 10
beacon = None
balancer = None
fileserver = None
stateNormal = 'Operating normally'
stateError = 'Connection issues'
state = stateNormal

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    r = requests.post(balancer + '/nodes', \
        data = request.data, \
        headers = {'content-type':'application/json'})
    return r.text, r.status_code
    
@app.route('/nodes/<string:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    r = requests.put(balancer + '/nodes/' + nodeid, \
        data = request.data, \
        headers = {'content-type':'application/json'})
    return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    r = requests.get(balancer + '/tasks/newtask', \
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
        
        r = requests.post(fileserver + '/static',
            files = {'file':open(fullpath, 'rb')})
        
        r = requests.post(balancer + '/tasks/'+taskid, \
            data = {'filename':nid}, \
            headers = {'content-type':'application/json'})
        return r.text, r.status_code
    else:
        return '', 422
        
def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def beacon_getter():
    global balancer
    global fileserver
    global beacon
    global state
    gotadr = False
    
    while (not gotadr):
        try:            
            r = requests.get(beacon + '/services/balancer')
            try: balancer = 'http://'+list(r.json().keys())[0]
            except: errorBalancer()
                
            r = requests.get(beacon + '/services/fileserver')
            try: fileserver = 'http://'+list(r.json().keys())[0]
            except: errorBalancer()
            
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
                selfaddress = requests.post(beacon + '/services/node_frontend', data={'port':port, 'state':state}).json()['address']
            else:
                requests.put(beacon + '/services/node_frontend/' + selfaddress, data={'state':state})
            
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
def errorBalancer():
    state = stateError
    print ('No balancer found')
def errorFileserver():
    state = stateError
    print ('No fileserver found')
    
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
    app.run(host = '0.0.0.0', port = port)