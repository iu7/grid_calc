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

unauthorized = render_template('login.html', message='Неавторизованный доступ')

@app.route('/create', methods=['GET'])
def create():
    sesid = request.cookies['session_id']
    ##############
    
    return render_template('create.html')

@app.route('/create-submit', methods=['POST'])
def createsubmit():
    sesid = request.cookies['session_id']
    ##############
    
    return redirect(url_for('/view'))



@app.route('/getfile', methods=['GET'])
def getfile():
    sesid = request.cookies['session_id']
    fileid = request.args['id']
    ##############
    return 'wot', 404

    

#######################################################################
# done
#######################################################################

def getuid(sesid)
    return requests.get(bw['session_backend'], data={'session_id':sesid}).json()['user_id']
    
@app.route('/logout', methods=['GET'])
def logout():
    sesid = request.cookies['session_id']
    
    try:
        requests.post(bw['session_backend']+'/logout', data={'session_id':sesid})
    except:
        pass
    
    response = make_response(redirect(url_for('login')))
    response.set_cookie('session_id', '', expires=0)
    return response
    
@app.route('/login-submit', methods=['POST'])
def loginsubmit():
    try:
        login = request.form['login']
        password = request.form['password']
        button = request.form['button']
    except:
        return '', 400
          
    if button == 'register':
        try:
            uid = requests.post(bw['session_backend']+'/register', \  
                data={'username':login, 'password':password})\
                .json()['user_id']
        except:
            return render_template('login.html', message='Ошибка регистрации')
    try:
        sid = requests.get(bw['session_backend'] + '/login', \
            data={'username':login, 'password':password}).json()['session_id']
        response = make_response(redirect(url_for('state')))
        response.set_cookie('session_id', sid)
        return response
    except:
        return render_template('login.html', message='Ошибка входа')

        
@app.route('/login', methods=['GET'])
def loginpage():
    return render_template('login.html', message=request.args.get('message', ''))
    
@app.route('/view', methods=['GET'])
def view():
    try:
        sesid = request.cookies['session_id']
        uid = getuid(sessid)
    except:
        return unauthorized
    
    tasks = jsr('get', bw['logic_backend'] + '/tasks', {'uid':uid}).json()['tasks']
    
    return render_template('view.html', tasks = tasks)
    
@app.route('/state', methods=['GET'])
def state():
    try:
        sesid = request.cookies['session_id']
        uid = getuid(sessid)
    except:
        return unauthorized
    
    services = requests.get(bw.beacon + '/services').json()
    servers = []
    for type in services:
        for address in services[type]:
            servers.append({'type':type, 'address':address, 'state':services[type][address]['state']})
    
    return render_template('state.html', servers = servers)
        
@app.route('/cancel', methods=['GET'])
def cancel():
    try:
        sesid = request.cookies['session_id']
        uid = getuid(sessid)
    except:
        return unauthorized
    try:
        taskid = int(request.args['id'])
    except:
        return '', 400
        
    jsr('delete', bw['logic_backend'] + '/tasks/' + str(taskid), {'uid':uid})
    return redirect(url_for('/view'))
    
if __name__ == '__main__':
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    global bw
    bw = BeaconWrapper(beacon, port, 'services/user_frontend', {'logic_backend', 'filesystem'})
    
    bw.beacon_setter()
    bw.beacon_getter()
    app.run(host = host, port = port)