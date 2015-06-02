import os, sys, shutil, shlex
from datetime import datetime
from time import sleep
import requests, json
import tempfile
import subprocess
import platform
import itertools
import psutil
import threading
import random, string

ARCHIVE_EXTENTION = 'tar.gz'

PLATFORM_INFO_SEP = '_'
PLATFORM_INFO_OS_ARCH_REL_FMTS = list(map(lambda cortege: PLATFORM_INFO_SEP.join(list(cortege)), itertools.permutations(['{platform}', '{architecture}', '{release}'])))
PLATFORM_INFO_OS_ARCH_FMTS     = list(map(lambda cortege: PLATFORM_INFO_SEP.join(list(cortege)), itertools.permutations(['{platform}', '{architecture}'])))
PLATFORM_INFO_OS_REL_FMTS      = list(map(lambda cortege: PLATFORM_INFO_SEP.join(list(cortege)), itertools.permutations(['{platform}', '{release}'])))
PLATFORM_INFO_OTHER_FMTS       = ['{platform}', '']

START_SCRIPT_PREFIX = 'start'
STOP_SCRIPT_PREFIX  = 'stop'

SCRIPT_RESULTS_DIR = 'results'
SCRIPT_EXTENTIONS = ['', 'exe', 'sh', 'py']

ZIPPER_CMD_FMT   = 'tar -czf {{name}}.{archext} {{wildcard}}'.format(archext = ARCHIVE_EXTENTION)
UNZIPPER_CMD_FMT = 'tar -xzf {wildcard}'

config = {}

config.update(GRID_CALC_ROLE = 'GRID_CALC_CLIENT')
config.update(WORKING_DIRECTORY = os.path.join(tempfile.gettempdir(), '_'.join([config['GRID_CALC_ROLE'], 'work'])))
config.update(HOME_DIRECTORY = os.path.join(os.path.expanduser("~"), config['GRID_CALC_ROLE']))
config.update(ARCHIVE_DIRECTORY = os.path.join(tempfile.gettempdir(), '_'.join([config['GRID_CALC_ROLE'], 'arch'])))
config.update(NODE_FRONTEND = None)
config.update(LOCK_FILE = 'key.lock')
config.update(SCRIPT_VALID_POSTFIX_FMTS = PLATFORM_INFO_OS_ARCH_REL_FMTS + PLATFORM_INFO_OS_ARCH_FMTS + PLATFORM_INFO_OS_REL_FMTS + PLATFORM_INFO_OTHER_FMTS)
config.update(CLIENT_TRAITS = [])

### Traits auto extract ###
### TODO: parse from some input file
def auto_extract_traits():
    platf, arch, release = platform.system(), platform.machine(), platform.release()
    config['CLIENT_TRAITS'] += [dict(name = 'os', version = platf)]
    config['CLIENT_TRAITS'] += [dict(name = 'os_version', version = release)]
    config['CLIENT_TRAITS'] += [dict(name = 'architecture', version = arch)]

class Node:
    key            = None
    busy           = False
    pdesc          = None
    input_archive  = None
    output_archive = None
    req_timeout    = 1
    node_id        = None
    task_id        = None

    def __init__(self):
        self.key = random_string(64)

    def __repr__(self):
        return ', '.join(map(lambda x: str(getattr(self, x)), filter(lambda x: not hasattr(x, '__call__'))))

    def run(self):
        auto_extract_traits()
        import pdb
        pdb.set_trace()
        homedir = config['HOME_DIRECTORY']
        workdir = config['WORKING_DIRECTORY']
        front = 'http://{0}'.format(config['NODE_FRONTEND'])
        keyfile = os.path.join(homedir, 'key.dat')
        tasklockfile = os.path.join(homedir, 'task.lock')
        
        ###>> keyfile ###
        if (os.path.exists(os.path.join(keyfile))):
            ifh = open(keyfile, 'r')
            ifs = ifh.read()
            id_, oldkey = None, None
            try:
                id_, oldkey = ifs.split('#')
            except:
                raise Exception('Syntax error in {0}. Try to remove it and retart.'.format(keyfile))
            resp = requests.put(front + '/nodes/{0}'.format(id_), data = {'key': self.key, 'key_old': oldkey, 'nodeid': id_})
            assert_response(resp)
            self.node_id = id_
        else:
            resp = jsr('post', front + '/nodes', data = {'key': self.key, 'traits': config['CLIENT_TRAITS']})
            assert_response(resp)
            self.node_id = resp.json()['agent_id']

        ofs = open(keyfile, 'w')
        ofs.write('#'.join(map(str, [self.node_id, self.key])))
        ofs.close()
        ###<< keyfile ###

        if not os.path.exists(tasklockfile):
            print('Found nothing to resume.')
            clear_directory(config['WORKING_DIRECTORY'])
            clear_directory(config['ARCHIVE_DIRECTORY'])

            resp = requests.get(front + '/tasks/newtask', data = {'key': self.key, 'nodeid': self.node_id})
            if resp.status_code != 200:
                print('No available tasks so far')
                return False, None
        
            print('Retrieved a task!')
            ###>> retrieving file
            while True:
                try:
                    arch = resp.json()['archive_name']
                    fresp = requests.get(front + '/getfile', data = {'key': self.key, 'nodeid': self.node_id, 'archive_name': arch}, stream = True)
                    assert_response(fresp)
                    print('Retrieving archive!')
                    download_file(fresp, os.path.join(config['ARCHIVE_DIRECTORY'], '.'.join([arch, ARCHIVE_EXTENTION])))
                    break
                except Exception as e:
                    print('Error occured during retrieving archive: {0}!'.format(str(e)))
                    print('Retrying after {0}s'.format(self.req_timeout))
                    sleep(self.req_timeout)
            ###<< retrieving file

            ###>> unzipping
            try:
                print('  Extracting archive')
                os.chdir(config['ARCHIVE_DIRECTORY'])
                unzipcmd = UNZIPPER_CMD_FMT.format(wildcard = '*')
                if not os.system(unzipcmd):
                    raise Exception('Failed to extract: {0}'.format(unzipcmd))
                os.chdir(config['WORKING_DIRECTORY'])
                print('  Done')
            except Exception as e:
                print('Failed: {0}'.format(str(e)))
                requests.put(front, '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': 'failed', 'message': str(e)})
                print('  Clearing working and archive directories')
                clear_directory(config['ARCHIVE_DIRECTORY'])
                clear_directory(config['WORKING_DIRECTORY'])
                return False, None
            ###<< unzipping
        else:
            print('Found unfinished task')

        try:
            print('Creating task lock file: {0}'.format(tasklockfile))
            ofs = open(tasklockfile, 'w')
            ofs.write('Make it so!')
            ofs.close()
        except Exception as e:
            print('Failed: {0}'.format(str(e)))
            print('Proceeding to next step')

        ###>> finding scripts
        start_script = find_script(START_SCRIPT_PREFIX, config['WORKING_DIRECTORY'], config['SCRIPT_VALID_POSTFIX_FMTS'])
        if not (start_script):
            msg = 'Failed: Not found start script: start = {0}'.format(start_script)
            print(msg)
            requests.put(front, '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': 'failed', 'message': msg})
            return False, None
        ###>> finding scripts

        ###>> starting
        try:
            print('  Attemting to run {0}'.format(start_script))
            os.chdir(config['WORKING_DIRECTORY'])
            self.pdesc = run(start_script)
        except Exception as e:
            msg = 'Failed to run: {0}'.format(str(e))
            print(msg)
            requests.put(front, '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': 'failed', 'message': msg})
            return False, None
        ###<< starting

        ###>> watchdog
        ### bark-bark!
        print('Setting watchdog on PID = {0}'.format(pdesc.pid))
        try:
            w = Watchdog(n.pdesc)
            w.start()
            print('Good boy!')
        except Exception as e:
            msg = 'Watchdog is sick: {0}'.format(str(e))
            print(msg)
            raise Exception(msg)
        ###<< wahchdog

        if self.popen.returncode:
            print('Task failed with code: {0}, but we will return what we can'.format(self.popen.returncode))

        ###>> task done, find results
        os.chdir(config['WORKING_DIRECTORY'])
        resdir = os.path.join(config['WORKING_DIRECTORY'], SCRIPT_RESULTS_DIR)
        if not os.path.exists(resdir):
            msg = 'Failed: results directory not found'
            print(msg)
            requests.put(front, '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': 'failed', 'message': msg})
            raise Exception(msg)
        
        ### results dir exists, zip it
        os.chdir(resdir)
        newarchfn = random_string(32)
        newarchfile = os.path.join(config['ARCHIVE_DIRECTORY'], '.'.join(newarchfn, ARCHIVE_EXTENTION))
        zipcmd = ZIPPER_CMD_FMT.format(name = newarchfile, wildcard = '*')
        if not os.system(zipcmd):
            raise Exception('Failed to compress: {0}'.format(zipcmd))
        os.chdir(config['WORKING_DIRECTORY'])

        ### send it
        front = 'http://{0}'.format(config['NODE_FRONTEND'])
        resp = requests.post(front, '/tasks', files = {'file': open(newarchfile, 'rb')}, data = {'key': self.key, 'nodeid': self.node_id})
        if resp.status_code != 200:
            raise Exception('Failed: {0}'.format(str(e)))

        os.unlink(tasklockfile)
        os.chdir(config['WORKING_DIRECTORY'])
        clear_directory(config['ARCHIVE_DIRECTORY'])
        clear_directory(config['WORKING_DIRECTORY'])

        print('WOOOOOOOAH! WOOOOOAH! MASAKA! IMPOSSIBURU! STILL NOTHING FAILED, SRSLY?!')
        print('THEN:')
        print('DISCONNECT THE CIRCUITS!')
        print('rm -rf /')
        print('shutdown --explode --timer=0')
        print('RIP {0}'.format(datetime.utcnow()))

        return True, None

class Watchdog:
    pdesc     = None
    timestamp = None
    timeout   = 2 # days
    cycletime = 600 # 10 minutes
    running   = False
    kill_to_term = 10 # seconds

    def __init__(self, pdesc):
        self.pdesc = pdesc
        self.timestamp = datetime.utcnow()

    def check():
        if self.pdesc.poll():
            if (datetime.utcnow() - self.timestamp).days > self.timeout:
                self.pdesc.terminate()
                sleep(self.kill_to_term)
                if self.pdesc.poll():
                    self.pdesc.kill()
            else:
                self.running = True
                self.start()
        self.running = False
        print('Bark!')


    def start():
        thr = threading.Timer(self.cycletime, self.check)
        thr.daemon = True
        thr.start()

###
def jsr(method, address, data = {}):
    return getattr(requests, method)(address, data = json.dumps(data), headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}) 

WINDOWS_DETACHED_PROCESS = 8
def run(cmd):
    sysname = platform.system()
    cmd_args = shlex.split(cmd)
    if sysname == 'Windows':
        print('  Attemting to run detached ...')
        popen = subprocess.Popen(cmd_args, creationflags=WINDOWS_DETACHED_PROCESS)
        print('  Attemting to set IDLE_PRIORITY_CLASS ...')
        psutil.Process(popen.pid).nice(psutil.IDLE_PRIORITY_CLASS)
        return popen
    elif sysname == 'Linux':
        print('  Attemting to run and nice(20) ...')
        cmd_args[0] = os.path.join(os.getcwd(), cmd_args[0])
        return subprocess.Popen(cmd_args, close_fds=True, preexec_fn=lambda : os.nice(20))
    else:
        raise Exception('Executing on OS {0} is currently not supported'.format(sysname))

def assert_response(resp, code = 200):
    if resp.status_code != code:
        raise Exception('Response was not {0}: {1}'.format(code, resp.json()))

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

def download_file(resp, fullpath):
    print('  Downloading to path: {0}'.format(fullpath))
    with open(fullpath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    print('  Done.')

def find_script(prefix, path, valid_fmts):
    for fmt in valid_fmts:
        name = PLATFORM_INFO_SEP.join([\
            prefix,\
            fmt.format(\
                platform = platform.system(),\
                architecture = platform.machine(),\
                release = platform.release()\
            )\
        ])
        fullpath = os.path.join(path, name)
        for ext in SCRIPT_EXTENTIONS:
            if os.path.exists('.'.join([fullpath, ext])):
                return name
        return name
    return None

def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        print('Creating directory: {0}'.format(path))
        os.makedirs(path)
 
def clear_directory(folder, whitelist=[config['ARCHIVE_DIRECTORY']]):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                if file_path not in map(lambda fld: os.path.split(fld)[-1], whitelist):
                    shutil.rmtree(file_path)
        except Exception as e:
            print(str(e))

def parse_cli_argv():
    try:
        node_front = sys.argv[1]
    except Exception as e:
        print('Usage: {0} node_frontend_host:node_frontend_port')
        sys.exit()
    return node_front

def set_lowest_priority():
    sysname = platform.system()
    if sysname == 'Windows':
        psutil.Process(os.getpid()).nice(psutil.IDLE_PRIORITY_CLASS)
    else:
        psutil.Process(os.getpid()).nice(20)


if __name__ == '__main__':
    print(config['GRID_CALC_ROLE'])

    config['NODE_FRONTEND'] = parse_cli_argv()

    create_dir_if_not_exists(config['WORKING_DIRECTORY'])
    create_dir_if_not_exists(config['ARCHIVE_DIRECTORY'])
    create_dir_if_not_exists(config['HOME_DIRECTORY'])

    print('Setting lowest priority')
    set_lowest_priority()
    
    n = Node()
    try:
        while True:
            n.run()
    except Exception as e:
        print('Error: {0}'.format(str(e)))