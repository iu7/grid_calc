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

defaultbeacon = '127.0.0.1:666'
defaultport = 671
beacon_adapter_cycletime = 3

port = None

beacon = None
database = None
stateNormal = 'Operating normally'
stateNoBeacon = 'Unable to find beacon'
stateNoDatabase = 'Unable to find active database'
state = stateNormal

selfaddress = None

@app.route('/nodes', methods=['POST'])
def nodesHandler():
    traits = request.form['traits'] if 'traits' in request.form else '{}'
    
    #todo
    
    return 'test', 200
    
@app.route('/nodes/<string:nodeid>', methods=['PUT'])
def nodesSpecificHandler(nodeid):
    state = request.form['state'] if 'state' in request.form else ''
    
    #todo
    
    return 'test', 200
    
@app.route('/tasks/newtask', methods=['GET'])
def newTaskHandler():
    nid = request.form['nodeid'] if 'nodeid' in request.form else ''
    
    #todo
    
    return 'test', 200
    
@app.route('/tasks/<string:taskid>', methods=['POST'])
def submitTaskHandler(taskid):
    nid = request.form['nodeid'] if 'nodeid' in request.form else ''
    file = request.files['file']
    if not (file and allowed_file(file.filename)):
        return '', 422
        
    filename = secure_filename(file.filename)
    fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(fullpath)
    
    #todo
    
    return r.text, r.status_code







def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def beacon_getter():
    global database
    gotadr = False
    oldadr = database
    
    while (not gotadr):
        try:
            nobeacon = True
            nodatabase = True
            
            r = requests.get('http://'+beacon + '/services/database')
            nobeacon = False
            database = list(r.json().keys())[0]
            nodatabase = False
            if (database != oldadr):
                print ('Database address set to ' + str(database))
                databaseUpMsg()
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_getter)
            thr.daemon = True
            thr.start()
            gotadr = True
            state = stateNormal
            databaseUpMsg()
            beaconUpMsg()
        except:
            if (nobeacon):
                state = stateNoBeacon
                beaconDownMsg()
            if (nodatabase):
                state = stateNoDatabase   
                databaseDownMsg()
            time.sleep(3)

def beacon_setter():
    messaged = False
    global selfaddress
    global port
    while (not messaged):
        try:
            if selfaddress == None:
                selfaddress = requests.post('http://'+beacon + '/services/balancer', data={'port':port, 'state':state}).json()['address']
            else:
                requests.put('http://'+beacon + '/services/balancer/' + selfaddress, data={'state':state})
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_setter)
            thr.daemon = True
            thr.start()
            messaged = True
            beaconUpMsg()
        except:
            beaconDownMsg()

dbmsg = False
def databaseDownMsg():
    global dbmsg
    if (not dbmsg): 
        print ('Database is down. Waiting to reconnect.')
        dbmsg = True

def databaseUpMsg():
    global dbmsg
    if (dbmsg): 
        print ('Database is back up.')
        dbmsg = False
        

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
        beacon = sys.argv[1]
        print ('Beacon address set to ' + str(beacon))
        print ('Port number defaulted to ' + str(port))
    elif len(sys.argv) == 3:
        beacon = sys.argv[1]
        port = int(sys.argv[2])
        print ('Beacon address set to ' + str(beacon))
        print ('Port number set to ' + str(port))
    
    beacon_setter()
    beacon_getter()
    app.run(host = '0.0.0.0', port = port)