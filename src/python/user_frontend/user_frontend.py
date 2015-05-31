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
import hashlib
from werkzeug import secure_filename
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'USER_FRONTEND')

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def getuid(sesid):
    return pyrequests.get(bw['session_backend']+'/auth', {'session_id':sesid}).json()['user_id']

def is_authorized():
    if 'session_id' not in request.cookies:
        return False
    sid = request.cookies['session_id']
    try:
        getuid(sid)
    except:
        return False
    return True

@app.route('/', methods=['GET'])
def default():
    if is_authorized():
        return redirect(url_for('state'))
    else:
        return redirect(url_for('login'))
    
@app.route('/create', methods=['GET'])
def create():
    sesid = request.cookies['session_id']
    ##############
    
    return render_template('create.html')

@app.route('/create', methods=['POST'])
def createsubmit():
    sesid = request.cookies['session_id']
    ##############
    
    return redirect(url_for('view'))


@app.route('/getfile', methods=['GET'])
def getfile():
    sesid = request.cookies['session_id']
    fileid = request.args['id']
    ##############
    return 'wot', 404

    
#######################################################################
# done
#######################################################################
    
@app.route('/logout', methods=['GET'])
def logout():
    if not is_authorized():
        return redirect(url_for('login'))

    sesid = request.cookies['session_id']
    
    try:
        pyrequests.post(bw['session_backend']+'/logout', {'session_id':sesid})
    except:
        pass
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('session_id', '', expires=0)
    return response        

@app.route('/login', methods=['POST'])
def loginsubmit():
    if is_authorized():
        return redirect(url_for('logout'))

    try:
        login = request.form['login']
        pw_hash = hashlib.sha256(request.form['password'].encode('utf-8')).hexdigest()
        button = request.form['button']
    except:
        return '', 400
          
    if button == 'register':
        uidr = None
        try:
            uidr = pyrequests.post(bw['session_backend']+'/register', {'username':login, 'pw_hash':pw_hash})
            uid = uidr.json()['user_id']
        except:
            return render_template('login.html', message='Ошибка регистрации: {0}'.format(uidr.json()['message']))
    sidr = None
    try:
        sidr = pyrequests.get(bw['session_backend'] + '/login', {'username':login, 'pw_hash':pw_hash})
        sid = sidr.json()['session_id']
        response = make_response(redirect(url_for('state')))
        response.set_cookie('session_id', sid)
        return response
    except:
        return render_template('login.html', message='Ошибка входа: {0}'.format(sidr.json()['message']))
        
@app.route('/login', methods=['GET'])
def login():
    if is_authorized():
        return redirect(url_for('default'))
    return render_template('login.html', message=request.args.get('message', ''))
    
@app.route('/view', methods=['GET'])
def view():
    if not is_authorized():
        return redirect(url_for('login'))
    tasks = pyrequests.get(bw['logic_backend'] + '/tasks', {'uid':uid}).json()['tasks']
    return render_template('view.html', tasks = tasks)
    
@app.route('/state', methods=['GET'])
def state():
    if not is_authorized():
        return redirect(url_for('login'))
    services = pyrequests.get(bw.beacon + '/services').json()
    servers = []
    for type in services:
        for address in services[type]:
            servers.append({'type':type, 'address':address, 'state':services[type][address]['state']})
    return render_template('state.html', servers = servers)
        
@app.route('/cancel', methods=['GET'])
def cancel():
    if not is_authorized():
        return redirect(url_for('login'))
    try:
        taskid = int(request.args['id'])
    except:
        return '', 400
        
    pyrequests.delete(bw['logic_backend'] + '/tasks/' + str(taskid), {'uid':uid})
    return redirect(url_for('view'))

###    
    
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/user_frontend', {'logic_backend', 'filesystem', 'session_backend'})
    
    bw.beacon_setter()
    bw.beacon_getter()
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)