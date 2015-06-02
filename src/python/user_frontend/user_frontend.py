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
import datetime
from werkzeug import secure_filename
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'USER_FRONTEND')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = set(['zip'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#######################################################################
# done
#######################################################################

@app.route('/viewtraits', methods=['GET'])
def viewtraits():
    try:
        uid = getuid()
    except:
        return unauthorized()
        
    traits = jsr('get', bw['logic_backend'] + '/traits').json()['result']
    
    return render_template('traits.html', traits=traits)

@app.route('/create', methods=['GET'])
def create():
    try:
        uid = getuid()
    except:
        return unauthorized()
        
    archivePending = False
    traitsPending = False
    if uid in pendingCreations:
        pc = pendingCreations[uid]
        if 'pending_archive' in request.cookies:
            pa = request.cookies['pending_archive'] 
            if 'archive' in pc and pc['archive'] == pa:
                archivePending = True
            else:
                response = make_response(redirect(url_for('create')))
                response.set_cookie('pending_archive', '', expires=0)
                return response
        if 'pending_traits' in request.cookies:
            if 'traits' in pc:
                traitsPending = True
            else:
                response = make_response(redirect(url_for('create')))
                response.set_cookie('pending_traits', '', expires=0)
                return response
    
    return render_template('create.html', archivePending = archivePending, traitsPending = traitsPending)

@app.route('/create', methods=['POST'])
def createsubmit():
    try:
        uid = getuid()
    except:
        return unauthorized()
        
    try:
        archivename = pendingCreations[uid]['archive']
        traits = pendingCreations[uid]['traits']
        taskname = request.form['taskname']
        maxtime = request.form['maxtime']
        subtaskcount = request.form['subtaskcount']
        assert jsr('post', bw['logic_backend'] + '/tasks', {'uid':uid, 'traits':traits, 'task_name':taskname, 'archive_name':archivename, 'max_time':maxtime, 'subtask_count':subtaskcount}).status_code == 200
        
        pendingCreations[uid]['archive_time'] = pendingCreations[uid]['traits_time'] = datetime.datetime.now() + datetime.timedelta(-30)
        pending_cleaner_clean(uid)
        
        return redirect(url_for('view'))
    except:
        return redirect(url_for('create'))

pendingCreations = {}

@app.route('/sendarchive', methods=['POST'])
def sendarchive():
    try:
        uid = getuid()
    except:
        return unauthorized()
    
    response = make_response(redirect(url_for('create')))
    if not uid in pendingCreations:
        pendingCreations[uid] = {}
    try:
        f = request.files['archive']
        filename = secure_filename(random_string(32))
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(fullpath)
        
        if 'archive' in pendingCreations[uid]:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], \
                pendingCreations[uid]['archive']))
        
        pendingCreations[uid]['archive'] = filename
        pendingCreations[uid]['archive_time'] = datetime.datetime.now()
        
        response.set_cookie('pending_archive', filename)
        return response
    except:
        pendingCreations[uid].pop('archive', '')
        response.set_cookie('pending_archive', '', expires=0)                
        return response
    
@app.route('/sendtraits', methods=['POST'])
def sendtraits():
    try:
        uid = getuid()
    except:
        return unauthorized()
    
    response = make_response(redirect(url_for('create')))
    if not uid in pendingCreations:
        pendingCreations[uid] = {}
    try:
        f = request.files['traits']
        filename = secure_filename(random_string(32))
        fullpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(fullpath)
        
        traits = []
        with open(fullpath) as f:
            lines = f.readlines()
            for line in lines:
                s = list(filter(None, line.split(' ')))
                assert len(s) == 2
                traits.append({'name':s[0], 'version':s[1].replace('\n', '')})
        safedel(fullpath)
    #except:
    #   redirect with 'wrong file syntax'
    #try:
        pendingCreations[uid]['traits'] = traits
        pendingCreations[uid]['traits_time'] = datetime.datetime.now()
        
        response.set_cookie('pending_traits', filename)
        return response
    except Exception as e:
        print (e)
        safedel(fullpath)
        response.set_cookie('pending_traits', '', expires=0)     
        return response
    
@app.route('/cancelarchive', methods=['POST'])
def cancelarchive():
    try:
        uid = getuid()
    except:
        return unauthorized()
    if uid in pendingCreations:
        if 'archive' in pendingCreations[uid]:
            safedel(os.path.join(app.config['UPLOAD_FOLDER'], \
                pendingCreations[uid]['archive']))
            pendingCreations[uid].pop('archive', '')
            pendingCreations[uid].pop('archive_time', '')
            
    response = make_response(redirect(url_for('create')))
    response.set_cookie('pending_archive', '', expires=0)      
    return response
        
@app.route('/canceltraits', methods=['POST'])
def canceltraits():
    try:
        uid = getuid()
    except:
        return unauthorized()
    if uid in pendingCreations:
        if 'traits' in pendingCreations[uid]:
            pendingCreations[uid].pop('traits', '')
            pendingCreations[uid].pop('traits_time', '')
            
    response = make_response(redirect(url_for('create')))
    response.set_cookie('pending_traits', '', expires=0)      
    return response
    
def pending_cleaner_clean(uid):  
    now = datetime.datetime.now()
    t = pendingCreations[uid]
    if 'archive_time' in t:
        if (now - t['archive_time']).total_seconds() > 60*20:
            safedel(os.path.join(app.config['UPLOAD_FOLDER'], \
                t['archive']))
            t.pop('archive_time', '')
            t.pop('archive', '')
    if 'traits_time' in t:
        if (now - t['traits_time']).total_seconds() > 60*20:
            t.pop('traits_time', '')
            t.pop('traits', '')  
            
def pending_cleaner():
    for uid in pendingCreations:
        pending_cleaner_clean(uid)
        
    thr = threading.Timer(60, pending_cleaner)
    thr.daemon = True
    thr.start()
    
@app.route('/getfile', methods=['GET'])
def getfile():
    try:
        uid = getuid()
    except:
        return unauthorized()
    try:
        fileid = request.args['id']
    except:
        return jsenc({'status':'failure', 'message':'File not found'}), 400
    
    try:
        getFileFromTo(bw['filesystem']+'/static/'+fileid, os.path.join(app.config['UPLOAD_FOLDER'], fileid))
        return send_from_directory(app.config['UPLOAD_FOLDER'], fileid)
    except Exception as e:
        print (e)
        return jsenc({'status':'failure', 'message':'File not found'}), 404
    
def unauthorized():
    return render_template('login.html', message='Неавторизованный доступ')    

def getuid():
    return pyrequests.get(bw['session_backend']+'/auth', {'session_id':request.cookies['session_id']}).json()['user_id']

def is_authorized():
    try:
        getuid()
        return True
    except:
        return False
    
@app.route('/', methods=['GET'])
def default():
    if is_authorized():
        return redirect(url_for('state'))
    else:
        return redirect(url_for('login'))
        
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
        try:
            uid = pyrequests.post(bw['session_backend']+'/register', {'username':login, 'pw_hash':pw_hash}).json()['user_id']
        except:
            return render_template('login.html', message='Ошибка регистрации')
    try:
        sidr = pyrequests.get(bw['session_backend'] + '/login', {'username':login, 'pw_hash':pw_hash})
        sid = sidr.json()['session_id']
        response = make_response(redirect(url_for('state')))
        response.set_cookie('session_id', sid)
        return response
    except:
        return render_template('login.html', message='Ошибка входа')
        
@app.route('/login', methods=['GET'])
def login():
    if is_authorized():
        return redirect(url_for('default'))
    return render_template('login.html', message=request.args.get('message', ''))
    
@app.route('/view', methods=['GET'])
def view():
    try:
        uid = getuid()
    except:
        return unauthorized()
    try:
        tasks = jsr('get', bw['logic_backend'] + '/tasks', {'uid':uid}).json()['tasks']
        message = ''
    except:
        tasks = []
        message = 'Ошибка при чтении задач'
    return render_template('view.html', tasks = tasks, message = message)
    
@app.route('/state', methods=['GET'])
def state():
    if not is_authorized():
        return unauthorized()
    services = pyrequests.get(bw.beacon + '/services').json()
    servers = []
    for type in services:
        for address in services[type]:
            servers.append({'type':type, 'address':address, 'state':services[type][address]['state']})
    return render_template('state.html', servers = servers)
        
@app.route('/cancel', methods=['GET'])
def cancel():
    try:
        uid = getuid()
    except:
        return unauthorized()
    try:
        taskid = int(request.args['id'])
    except:
        return '', 400
        
    jsr('delete', bw['logic_backend'] + '/tasks/' + str(taskid), {'uid':uid})
    return redirect(url_for('view'))

###    
    
if __name__ == '__main__':
    preparedir(app.config['UPLOAD_FOLDER'], flush=True)
    
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv)
    print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port, 'services/user_frontend', {'logic_backend', 'filesystem', 'session_backend'})
    
    bw.beacon_setter()
    bw.beacon_getter()
    pending_cleaner()
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)