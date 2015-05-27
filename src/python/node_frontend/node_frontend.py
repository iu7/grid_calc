from flask import *
import jsonpickle
import datetime
import threading
import time
import sys
import requests
from werkzeug import secure_filename
import os

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

defaultbeacon = 'http://127.0.0.1:666'
defaultport = 670
beacon_adapter_cycletime = 3

port = None

beacon = None
balancer = None
stateNormal = 'Operating normally'
stateNoBeacon = 'Unable to find beacon'
stateNoBalancer = 'Unable to find active balancer'
state = stateNormal

selfaddress = None

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = request.form['traits'] if 'traits' in request.form else '{}'
    r = requests.post(balancer + '/nodes', \
        data = {'traits':request.form['traits']})
    return r.text, r.status_code
    
@app.route('/nodes/<string:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    state = request.form['state'] if 'state' in request.form else ''
    r = requests.put(balancer + '/nodes/' + nodeid, \
        data = {'state':request.form['state']})
    return r.text, r.status_code
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    nid = request.form['nodeid'] if 'nodeid' in request.form else ''
    r = requests.get(balancer + '/tasks/newtask', \
        data = {'nodeid':nid})
    return r.text, r.status_code
    
@app.route('/tasks/<string:taskid>', methods=['POST'])
def submitTaskHandler(taskid):
    nid = request.form['nodeid'] if 'nodeid' in request.form else ''
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fullpath)
        
        r = requests.post(balancer + '/tasks/'+taskid, \
            data = {'nodeid':nid}, \
            files = {'file':open(fullpath, 'rb')})
        return r.text, r.status_code
    else:
        return '', 422
        
def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def beacon_getter():
    global balancer
    gotadr = False
    oldadr = balancer
    
    while (not gotadr):
        try:
            nobeacon = True
            nobalancer = True
            
            r = requests.get(beacon + '/services/balancer')
            nobeacon = False
            balancer = 'http://'+list(r.json().keys())[0]
            nobalancer = False
            if (balancer != oldadr):
                print ('Balancer address set to ' + str(balancer))
                balancerUpMsg()
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_getter)
            thr.daemon = True
            thr.start()
            gotadr = True
            state = stateNormal
            balancerUpMsg()
            beaconUpMsg()
        except:
            if (nobeacon):
                state = stateNoBeacon
                beaconDownMsg()
            if (nobalancer):
                state = stateNoBalancer    
                balancerDownMsg()
            time.sleep(3)

def beacon_setter():
    messaged = False
    global selfaddress
    global port
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
            messaged = True
            beaconUpMsg()
        except:
            state = stateNoBeacon
            beaconDownMsg()

bdmsg = False
def balancerDownMsg():
    global bdmsg
    if (not bdmsg): 
        print ('Balancer is down. Waiting to reconnect.')
        bdmsg = True

def balancerUpMsg():
    global bdmsg
    if (bdmsg): 
        print ('Balancer is back up.')
        bdmsg = False
        

bcmsg = False
def beaconDownMsg():
    global bcmsg
    if (not bcmsg): 
        print ('Beacon is down. Waiting to reconnect.')
        bcmsg = True

def beaconUpMsg():
    global bcmsg
    if (bcmsg): 
        print ('Beacon is back up.')
        bcmsg = False
        
if __name__ == '__main__':
    global port
    port = defaultport
    beacon = defaultbeacon
    if len(sys.argv) == 1:
        print ('Beacon address defaulted to ' + str(beacon))
        print ('Port number defaulted to ' + str(port))
    elif len(sys.argv) == 2:
        beacon = 'http://'+sys.argv[1]
        print ('Beacon address set to ' + str(beacon))
        print ('Port number defaulted to ' + str(port))
    elif len(sys.argv) == 3:
        beacon = 'http://'+sys.argv[1]
        port = int(sys.argv[2])
        print ('Beacon address set to ' + str(beacon))
        print ('Port number set to ' + str(port))
    
    beacon_setter()
    beacon_getter()
    app.run(host = '0.0.0.0', port = port)