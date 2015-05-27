from flask import *
import jsonpickle
import datetime
import threading
import time
import sys
import atexit

timeout = 20
collector_cycletime = 10

app = Flask(__name__)
app.config.update(DEBUG=True)

services = {}

@app.route('/services', methods=['GET'])
def servicesHandler():
    return jsenc(services)
    
@app.route('/services/<string:type>', methods=['GET', 'POST'])
def servicesOfTypeHandler(type):
    if request.method == 'GET':
        if type in services:
            return jsenc(services[type])
        else:
            return jsenc({})
    else:#POST
        if (not 'port' in request.form) or (not isInt (request.form['port'])):
            abort(422)
        else:
            port = request.form['port']
            state = request.form['state'] if 'state' in request.form else ''
            ipaddr = request.remote_addr
            addr = ipaddr + ':' + port
            
            if not type in services:
                services[type] = {}
            services[type][addr] = ServiceState(state)
            
            print('Incoming request from {0}: port = {1}, state = {2}'.format(ipaddr, port, state))
            return jsenc({'status':'success', 'address':addr})
            
@app.route('/services/<string:type>/<string:addr>', methods=['GET', 'PUT'])
def serviceExactHandler(type, addr):
    if request.method == 'GET':
        if type in services and addr in services[type]:
            return jsenc(services[type][addr])
        else:
            abort(404)
    else:
        state = request.form['state'] if 'state' in request.form else ''
        if not type in services:
            services[type] = {}
        services[type][addr] = ServiceState(state)
        print('Incoming request from {0}: state = {1}'.format(addr, state))
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
    
    thr = threading.Timer(collector_cycletime, collector)
    thr.daemon = True
    thr.start()
        
def jsenc(o):
    return jsonpickle.encode(o, unpicklable=False)

def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False
    
class ServiceState:
    state = ''
    lastbeat = None
    def __init__(self, state):
        self.state = state
        self.lastbeat = datetime.datetime.now()
    def __getstate__(self):
        state = self.__dict__.copy()
        state['lastbeat'] = str(state['lastbeat'])
        return state

if __name__ == '__main__':
    host = '0.0.0.0'
    port = None
    try:
        port = int(sys.argv[1])
    except Exception as e:
        print('Usage: {0} port'.format(sys.argv[0]))
        sys.exit()

    print('Starting with settings: self: {1}:{0}'.format(host, port))
    
    collector()
    app.run(host = host, port = port)