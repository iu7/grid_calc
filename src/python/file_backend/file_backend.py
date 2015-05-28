import sys
import os
import threading, time
import requests as pypyrequests

from flask import *
from werkzeug.routing import BaseConverter
from werkzeug import secure_filename

from common import *

import random, string

port = None
selfaddress = None
beacon_adapter_cycletime = 10
beacon = None
stateNormal = 'Operating normally'
stateError = 'Connection issues'
state = stateNormal

app = Flask(__name__, static_path='/static')
app.config.update(DEBUG = True, UPLOAD_FOLDER = 'static/')

filename_size = 32
filename_ext = '.dat'

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

def make_folder_structure(path):
    cpth = os.path.join(app.config['UPLOAD_FOLDER'])
    npth = cpth + path
    try:
        if not os.path.exists(npth):
            os.makedirs(npth)
    except Exception as e:
        return api_500(str(e))
    return None

### Views ###

@app.route('/static/<path>', methods=['GET', 'DELETE'])
def hnd_get_delete_file(path):
    sp = path[::-1].split('\\', 1)
    pth, fn = '', path
    if len(sp) > 1:
        pth = sp[1][::-1].replace('\\', '/')
        fn = sp[0][::-1]
    filename = safe_join(app.config['UPLOAD_FOLDER'] + pth, fn)

    if os.path.exists(filename):
        if request.method == 'GET':
            return send_from_directory(app.config['UPLOAD_FOLDER'] + pth, fn, as_attachment=True)
        else:
            try:
                os.remove(filename)
            except Exception as e:
                return api_500(str(e))
            return api_200()
    else:
        return api_404()


@app.route('/static', methods=['POST'])
def hnd_post_file():
    subpath = get_url_parameter('path') if has_url_parameter('path') else ''
    subpath = subpath.replace('\\', '/')
    err = make_folder_structure(subpath)
    if not err:
        f = request.files['file']
        if f:
            filename = secure_filename(random_string(filename_size)+filename_ext)
            newpath = os.path.join(app.config['UPLOAD_FOLDER'] + subpath, filename)
            displaypath = os.path.join(subpath, filename)
            f.save(newpath)
            return api_200({"name" : displaypath.replace('/', '\\')})
        else:
            return api_400('Bad request: File required')
    else:
        return err

### Error handlers ###

@app.errorhandler(500)
def api_500(msg = 'Internal error'):
    return response_builder({'error': msg}, 500)

@app.errorhandler(400)
def api_400(msg = 'Bad request'):
    return response_builder({'error': msg}, 400)

@app.errorhandler(404)
def api_404(msg = 'Not found'):
    return response_builder({'error': msg}, 404)

@app.errorhandler(200)
def api_200(data = {}):
    return response_builder(data, 200)

### Other ###

def errorBeacon():
    state = stateError
    print ('Unable to reach beacon')
        
def beacon_setter():
    messaged = False
    global selfaddress
    global port
    global beacon
    global state
    while (not messaged):
        try:
            if selfaddress == None:
                selfaddress = pyrequests.post(beacon + '/services/fileserver', data={'port':port, 'state':state}).json()['address']
            else:
                pypyrequests.put(beacon + '/services/fileserver/' + selfaddress, data={'state':state})
            
            thr = threading.Timer(beacon_adapter_cycletime, beacon_setter)
            thr.daemon = True
            thr.start()
            
            state = stateNormal
            messaged = True
        except:
            errorBeacon()
            time.sleep(5)

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
    app.run(host = host, port = port)