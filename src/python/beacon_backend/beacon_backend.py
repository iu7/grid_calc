from flask import *
import jsonpickle
import datetime
import threading
import time

timeout = 10

app = Flask(__name__)

services = {}

@app.route('/services', methods=['GET'])
def servicesHandler():
    error = None
    return jsenc(services)
    
@app.route('/services/<string:type>', methods=['GET', 'POST'])
def servicesOfTypeHandler(type):
    if request.method == 'GET':
        if type in services:
            return jsenc(services[type])
        else:
            return jsenc({})
    else:
        if not 'port' in request.form:
            abort(422)
        else:
            port = request.form['port']
            state = request.form['state'] if 'state' in request.form else ''
            ipaddr = request.remote_addr
            addr = ipaddr + ':' + port
            
            if not type in services:
                services[type] = {}
            services[type][addr] = ServiceState(state)
            
            return jsenc({'status':'success', 'address':addr})
            
@app.route('/services/<string:type>/<string:addr>', methods=['GET', 'PUT'])
def serviceExactHandler(type, addr):
    if request.method == 'GET':
        if type in services and addr in services[type]:
            return jsenc(services[type][addr])
        else:
            abort(404)
    else:
        services[type][addr] = ServiceState(
            request.form['state'] if 'state' in request.form else '')
        return jsenc({'status':'success'})

def collector():
    now = datetime.datetime.now()
    
    for type in list(services.keys()):
        typedict = services[type]
        
        for addr in list(typedict.keys()):
            if (now - typedict[addr].lastbeat).seconds > timeout:
                del typedict[addr]
                
        if len(typedict) == 0:
            del services[type]
    
    threading.Timer(timeout, collector).start()
        
def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

class ServiceState:
    state = ""
    lastbeat = None
    def __init__(self, state):
        self.state = state
        self.lastbeat = datetime.datetime.now()
    def __getstate__(self):
        state = self.__dict__.copy()
        state['lastbeat'] = str(state['lastbeat'])
        return state

if __name__ == '__main__':
    collector()
    app.run(host = '0.0.0.0', port = 666)