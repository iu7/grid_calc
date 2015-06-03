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
import random, string
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'SESSION_BACKEND')
app.secret_key = 'rly secret key!'

sessions = {}

@app.route('/register', methods=['POST'])
def registration():
    try:
        username = get_url_parameter('username')
        pw_hash = get_url_parameter('pw_hash')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    try:
        existing = jsr('get', bw['database'] + '/user/filter', {'username':username}).json()['result'][0]['id']
        return jsenc({'status':'failure', 'message':'Username taken'}), 422
    except:
        pass
        
    try:
        uid = jsr('post', bw['database'] + '/user', {'username':username, 'pw_hash':pw_hash}).json()['id']
        return jsenc({'status':'success', 'user_id':uid}), 200
    except:
        return jsenc({'status':'failure', 'message':'failed to register'}), 500       

@app.route('/login', methods=['GET'])
def login():
    try:
        username = get_url_parameter('username')
        pw_hash = get_url_parameter('pw_hash')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = jsr('get', bw['database'] + '/user/filter', {'username':username, 'pw_hash':pw_hash}).json()['result'][0]['id']
        if not uid in sessions:
            sessions[uid] = randomword(64)
        return jsenc({'status':'success', 'session_id':sessions[uid]}), 200
    except:
        return jsenc({'status':'failure', 'message':'Unauthorized'}), 403

@app.route('/auth', methods=['GET'])
def auth():
    try:
        sesid = get_url_parameter('session_id')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = getkbv(sessions, sesid)
        return jsenc({'status':'success', 'user_id':uid}), 200
    except:
        return jsenc({'status':'failure', 'message':'Session expired'}), 403
        
@app.route('/logout', methods=['GET'])
def logout():
    try:
        sesid = get_url_parameter('session_id')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = getkbv(sessions, sesid)
        del sessions[uid]
        return jsenc({'status':'success'}), 200
    except:
        return jsenc({'status':'failure', 'message':'Session unrecognized'}), 403
            
def getkbv(d, val):
    for k, v in d.items():
        if (v == val):
            return k
    raise Exception('Value not found')
    
def randomword(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])
    
################################

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/session_backend', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)