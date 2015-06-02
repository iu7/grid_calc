import os, sys
from datetime import datetime
import time
import requests
import expanduser
import tempfile
import subprocess
import zipfile

config = {}

config.update(GRID_CALC_ROLE = 'GRID_CALC_CLIENT')
config.update(WORKING_DIRECTORY = os.path.join(tempfile.gettempdir(), '_'.join([config['GRID_CALC_ROLE'], 'upload'])))
config.update(HOME_DIRECTORY = os.path.join(os.path.expanduser("~"), config['GRID_CALC_ROLE']))
config.update(NODE_FRONTEND = None)
config.update(LOCK_FILE = 'key.lock')

class Node:
    key            = None
    busy           = False
    pid            = None
    timestamp      = None
    timeout        = 172800 # 2 days is seconds
    input_archive  = None
    output_archive = None    
    sleep_interval = 600 # 10 minutes
    node_id        = None

    def __init__(self):
        self.key = random_string(64)

    def __repr__(self):
        return ', '.join(map(lambda x: str(getattr(self, x)), filter(lambda x: not hasattr(x, '__call__'))))

    def run():
        homedir = config['HOME_DIRECTORY']
        workdir = config['WORKING_DIRECTORY']
        front = 'http://{0}'.format(config['NODE_FRONTEND'])
        lockfile = os.path.join(homedir, lockfile)
        
        if not busy:
            self.busy = True
        else:
            return False
        
        ###>> Lockfile ###
        if (os.path.exists(os.path.join(lockfile))):
            ifs = open('r', lockfile).read()
            id_, oldkey = None, None
            try:
                id_, oldkey = ifs.split('#')
            except:
                raise Exception('Syntax error in {0}. Try to remove it and retart.'.format(lockfile))
            resp = requests.put(front + '/nodes/{0}'.format(id_), data = {'key': self.key, 'key_old': oldkey})
            assert_response(resp)
            self.node_id = id_
            ifs.close()
        else:
            resp = requests.post(front + '/nodes', data = {'key': self.key})
            assert_response(resp)
            self.node_id = resp.json()['id']

        ofs = open('w', lockfile)
        ofs.write('#'.join(self.node_id, self.key))
        ofs.close()
        ###<< Lockfile ###

        resp = requests.get(front + '/tasks/newtask', data = {'key': self.key})
        assert_response(resp)

        

###

def assert_response(resp, code = 200):
    if resp.status_code != code:
        raise Exception('Response was not {0}: {1}'.format(code, resp.get_json()))

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        print('Creating directory: {0}'.format(path))
        os.makedirs(path)
 
def parse_cli_argv():
    try:
        node_front = sys.argv[1]
    except Exception as e:
        print('Usage: {0} node_frontend_host:node_frontend_port')
        sys.exit()
    return node_front

if __name__ == '__main__':
    print(config['GRID_CALC_ROLE'])
    platform_dependent_on_run(config['GRID_CALC_ROLE'])

    config['NODE_FRONTEND'] = parse_cli_argv()

    create_dir_if_not_exists(config['WORKING_DIRECTORY'])
    create_dir_if_not_exists(config['HOME_DIRECTORY'])

    n = Node()