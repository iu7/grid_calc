import sys
import os

from flask import *
from werkzeug.routing import BaseConverter
from werkzeug import secure_filename

from common import *

import random, string

app = Flask(__name__, static_path='/static')
app.config.update(DEBUG = True, UPLOAD_FOLDER = 'static/')

filename_size = 32

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
            filename = secure_filename(random_string(filename_size))
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

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 50001
    try:
        port = int(sys.argv[1])
    except Exception as e:
        print('Usage: {0} [port]'.format(sys.argv[0]))
        sys.exit()

    print('Starting with settings: self: {0}:{1}'.format(host, port))
    app.run(host = host, port = port)