from flask import *
import jsonpickle
import datetime
import threading
import time
import sys
import atexit

timeout = 60
defaultport = 666
collector_cycletime = 3

app = Flask(__name__)
app.config.update(DEBUG=True)

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
        if type not in services:
            services.update({type:{}})
        if addr not in services[type]:
            services[type].update({addr : None})
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
    p = defaultport
    if len(sys.argv) == 1:
        print ('Port number defaulted to ' + str(p))
    else:
        if sys.argv[1].isdigit():
            p = int(sys.argv[1])
        else:
            print('Unprocessable port number')
            sys.exit()
    
    collector()
    app.run(host = '0.0.0.0', port = p)