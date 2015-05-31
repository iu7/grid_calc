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
app.config.update(GRID_CALC_ROLE = 'SESSION_BACKEND')

sessions = {}

@app.route('/register', methods=['POST'])
def registration():
    try:
        username = request.form['username']
        pw_hash = request.form['pw_hash']
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    try:
        existing = jsr('get', bw['data_backend'] + '/user/filter', {'username':username}).json()['result'][0]['id']
        return jsenc({'status':'failure', 'message':'Username taken'}), 422
    except:
        pass
        
    try:
        uid = jsr('post', bw['data_backend'] + '/user', {'username':username, 'pw_hash':pw_hash}).json()['id']
        return jsenc({'status':'success', 'user_id':uid}), 200
    except:
        return jsenc({'status':'failure', 'message':'failed to register'}), 500       

@app.route('/login', methods=['GET'])
def login():
    try:
        username = request.form['username']
        pw_hash = request.form['pw_hash']
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = jsr('get', bw['data_backend'] + '/user/filter', {'username':username, 'pw_hash':pw_hash}).json()['result'][0]['id']
        if not uid in sessions:
            sessions[uid] = randomword(256)
        return jsenc({'status':'success', 'session_id':sessions[uid]}), 200
    except:
        return jsenc({'status':'failure', 'message':'Unauthorized'}), 403

@app.route('/auth', methods=['GET'])
def auth():
    try:
        sesid = request.form['session_id']
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
        sesid = request.form['session_id']
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = getkbv(sessions, sesid)
        del sessions[uid]
    except:
        return jsenc({'status':'failure', 'message':'Session unrecognized'}), 403
            
def getkbv(dict, val):
    for k, v in dict:
        if (v == val):
            return k
    raise 'Value not found'
    
def randomword(length):
   return ''.join(random.choice(string.lowercase) for i in range(length))
    
################################

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    global bw
    bw = BeaconWrapper(beacon, port, 'services/session_backend', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)