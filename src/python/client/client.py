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
PLATFORM_INFO_OTHER_FMTS       = ['{platform}']

START_SCRIPT_PREFIX = 'start'

SCRIPT_RESULTS_DIR = 'result'
SCRIPT_EXTENTIONS = ['exe', 'sh', 'bat', 'py']

TAR_PACK_CMD_FMT = 'tar -cf {name}.tar {wildcard}'
GZIP_PACK_CMD_FMT = 'gzip {name}.tar'
TAR_UNPACK_CMD_FMT = 'tar -xf {name}.tar'
GZIP_UNPACK_CMD_FMT = 'gzip -d {name}.tar.gz'

TRAITS_COLSEP = ' '

TASK_STATUS_FAILED = 'failed'
TASK_STATUS_FINISHED = 'finished'
NODE_STATUS_ACTIVE = 'active'
NODE_STATUS_ACTIVE = 'down'

config = {}

config.update(GRID_CALC_ROLE = 'GRID_CALC_CLIENT')
config.update(NODE_FRONTEND = None)
config.update(SCRIPT_VALID_POSTFIX_FMTS = PLATFORM_INFO_OS_ARCH_REL_FMTS + PLATFORM_INFO_OS_ARCH_FMTS + PLATFORM_INFO_OS_REL_FMTS + PLATFORM_INFO_OTHER_FMTS)
config.update(CLIENT_TRAITS = [])

def pack(name, wildcard, srcpath, dstpath):
    code = 0
    os.chdir(srcpath)
    code += os.system(TAR_PACK_CMD_FMT.format(name = name, wildcard = wildcard))
    code += os.system(GZIP_PACK_CMD_FMT.format(name = name))
    shutil.move(name + '.tar.gz', dstpath)
    return code

def unpack(name, srcpath, dstpath):
    code = 0
    archtgz = name + '.tar.gz'
    os.chdir(dstpath)
    
    path = os.path.join(srcpath, archtgz)
    shutil.copy(path, '.')
    code += os.system(GZIP_UNPACK_CMD_FMT.format(name = name))
    code += os.system(TAR_UNPACK_CMD_FMT.format(name = name))
    return code

### Traits auto extract ###
### TODO: parse from some input file
def auto_extract_traits():
    platf, arch, release = platform.system(), platform.machine(), platform.release()
    config['CLIENT_TRAITS'] += [dict(name = 'os', version = platf)]
    config['CLIENT_TRAITS'] += [dict(name = 'os_version', version = release)]
    config['CLIENT_TRAITS'] += [dict(name = 'architecture', version = arch)]

class EUnrecoverable(Exception):
    def __init__(self, message):
        super(EUnrecoverable, self).__init__(message)

class ERecoverable(Exception):
    def __init__(self, message):
        super(ERecoverable, self).__init__(message)

class ETaskUnrecoverable(Exception):
    def __init__(self, message):
        super(ETaskUnrecoverable, self).__init__(message)

class ETaskRecoverable(Exception):
    def __init__(self, message):
        super(ETaskRecoverable, self).__init__(message)

class Node:
    key            = None
    pdesc          = None
    req_timeout    = 1
    task_req_timeout = 1
    node_id        = None
    task_id        = None
    max_time       = None
    status         = None
    task_id        = None
    subtask_id     = None
    archive_name   = None

    def __init__(self):
        self.key = random_string(64)

    def __repr__(self):
        return ', '.join(map(lambda x: str(getattr(self, x)), filter(lambda x: not hasattr(x, '__call__'))))

    def clear(self):
        self.pdesc, self.node_id, self.task_id, self.max_time, self.status, self.subtask_id, self.archive_name = [None] * 7

    def put_task_status(self, adr, status):
        return requests.put(\
            adr + '/nodes/{0}'.format(self.node_id),\
            data = {'key': self.key, 'status': status, 'subtask_id': self.subtask_id}\
        )

    def run(self):
        self.clear()
        homedir = config['HOME_DIRECTORY']
        workdir = config['WORKING_DIRECTORY']
        front = 'http://{0}'.format(config['NODE_FRONTEND'])
        keyfile = config['KEYFILE']
        tasklockfile = config['TASK_LOCKFILE']
        
        ###>> keyfile ###
        if (os.path.exists(keyfile)):
            ifh = open(keyfile, 'r')
            ifs = ifh.read()
            id_, oldkey = None, None
            try:
                id_, oldkey = ifs.split('#')
            except:
                raise ERecoverable('Syntax error in {0}. Removing it and restarting.'.format(keyfile))
                os.unlink(keyfile)
            resp = requests.put(front + '/nodes/{0}'.format(id_), data = {'key': self.key, 'key_old': oldkey})
            assert_response(resp, EUnrecoverable)
            self.node_id = id_
        else:
            auto_extract_traits()
            resp = jsr('post', front + '/nodes', data = {'key': self.key, 'traits': config['CLIENT_TRAITS']})
            assert_response(resp, EUnrecoverable)
            self.node_id = resp.json()['agent_id']

        ofs = open(keyfile, 'w')
        ofs.write('#'.join(map(str, [self.node_id, self.key])))
        ofs.close()
        ###<< keyfile ###

        if not os.path.exists(tasklockfile):
            print('Found nothing to resume.')
            clear_directory(config['WORKING_DIRECTORY'])
            clear_directory(config['ARCHIVE_DIRECTORY'])

            resp = requests.get(front + '/tasks/newtask', data = {'key': self.key, 'node_id': self.node_id})
            if resp.status_code != 200:
                print('No available tasks so far')
                return False
        
            print('Retrieved a task!')
            try:
                self.max_time = resp.json()['max_time']
                self.subtask_id = resp.json()['subtask_id']
                self.archive_name = resp.json()['archive_name']
            except Exception as e:
                raise EUnrecoverable('Server error: not all task parameters were sent by server!')

            ###>> retrieving file
            while True:
                try:
                    fresp = requests.get(front + '/getfile', data = {'key': self.key, 'node_id': self.node_id, 'subtask_id': self.subtask_id, 'archive_name': self.archive_name}, stream = True)
                    assert_response(fresp, None)
                    print('Retrieving archive!')
                    download_file(fresp, os.path.join(config['ARCHIVE_DIRECTORY'], '.'.join([self.archive_name, ARCHIVE_EXTENTION])))
                    break
                except Exception as e:
                    print('Error occured during retrieving archive: {0}!'.format(str(e)))
                    print('Retrying after {0}s'.format(self.req_timeout))
                    sleep(self.req_timeout)
            ###<< retrieving file
        else:
            print('Found unfinished task')
            clear_directory(config['WORKING_DIRECTORY'])
            ###>> extracting data from lockfile
            try:
                ifs = open(tasklockfile, 'r')
                fdata = ifs.read()
                self.subtask_id, self.max_time, self.archive_name = fdata.split('#')
                self.max_time = int(self.max_time)
            except Exception as e:
                requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
                assert_response(resp, ETaskRecoverable) # It is recoverable unless we can properly reply that it is not
                raise ETaskUnrecoverable('Malformed task lockfile')
            finally:
                ifs.close()
            ###<< extracting data from lockfile

        ###>> unzipping
        try:
            print('  Extracting archive')
            code = unpack(self.archive_name, config['ARCHIVE_DIRECTORY'], config['WORKING_DIRECTORY'])
            if code:
                raise Exception('Failed to extract: {0}'.format(unzipcmd))
            print('  Done')
        except Exception as e:
            requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
            assert_response(resp, ETaskRecoverable) # It is recoverable unless we can properly reply that it is not
            raise ETaskUnrecoverable(str(e))
        ###<< unzipping

        ###>> creating lockfile
        if not os.path.exists(tasklockfile):
            print('Creating task lock file: {0}'.format(tasklockfile))
            ofs = open(tasklockfile, 'w')
            ofs.write('#'.join(list(map(str, [self.subtask_id, self.max_time, self.archive_name]))))
            ofs.close()
        ###<< creating lockfile

        # Let's put here, we can recover task at least
        requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'node_status': NODE_STATUS_ACTIVE})
        assert_response(resp, ERecoverable)

        ###>> finding scripts
        start_script = find_script(START_SCRIPT_PREFIX, config['WORKING_DIRECTORY'], config['SCRIPT_VALID_POSTFIX_FMTS'])
        if not (start_script):
            msg = 'Not found start script: start = {0}'.format(start_script)
            requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
            assert_response(resp, ETaskRecoverable) # It is recoverable unless we can properly reply that it is not
            raise ETaskUnrecoverable(msg)
        ###< finding scripts

        ###>> starting
        try:
            print('  Attempting to run {0}'.format(start_script))
            os.chdir(config['WORKING_DIRECTORY'])
            self.pdesc = run(start_script)
        except Exception as e:
            msg = 'Failed to run: {0}'.format(str(e))
            requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
            assert_response(resp, ETaskRecoverable) # It is recoverable unless we can properly reply that it is not
            raise ETaskUnrecoverable(msg)
        ###<< starting

        ###>> watchdog
        ### bark-bark!
        print('Setting watchdog on PID = {0}'.format(self.pdesc.pid))
        try:
            w = Watchdog(self.pdesc, self.max_time)
            w.start()
            w.wait()
            print('Good boy!')
        except Exception as e:
            msg = 'Watchdog is sick: {0}'.format(str(e))
            print(msg)
            raise EUnrecoverable(msg)
        ###<< wahchdog

        if self.pdesc.returncode:
            msg = 'Task failed with code: {0}'.format(self.pdesc.returncode)
            print(msg + ', but we will return what we can')
            requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
            assert_response(resp, ETaskRecoverable)
            self.status = TASK_STATUS_FAILED
        else:
            self.status = TASK_STATUS_FINISHED

        ###>> task done, find results
        os.chdir(config['WORKING_DIRECTORY'])
        resdir = os.path.join(config['WORKING_DIRECTORY'], SCRIPT_RESULTS_DIR)
        if not os.path.exists(resdir):
            msg = 'Results directory <{0}> not found in archive root'.format(SCRIPT_RESULTS_DIR)
            requests.put(front + '/nodes/{0}'.format(self.node_id), data = {'key': self.key, 'status': TASK_STATUS_FAILED, 'subtask_id': self.subtask_id})
            assert_response(resp, ETaskRecoverable) # It is recoverable unless we can properly reply that it is not
            raise ETaskUnrecoverable(msg)
        
        ### results dir exists, zip it
        newarchfn = random_string(32)
        newarchfile = os.path.join(config['ARCHIVE_DIRECTORY'], newarchfn)
        code = pack(newarchfn, '*', resdir, config['ARCHIVE_DIRECTORY'])

        if code:
            raise ETaskUnrecoverable('Failed to compress: {0}'.format(zipcmd))
        os.chdir(config['WORKING_DIRECTORY'])

        ### send it
        newarchfile = '.'.join([newarchfile, ARCHIVE_EXTENTION])
        front = 'http://{0}'.format(config['NODE_FRONTEND'])
        resp = requests.post(\
            front + '/tasks',\
            files = {'file': open(newarchfile, 'rb')},\
            data = {'key': self.key, 'node_id': self.node_id, 'status': self.status, 'subtask_id': self.subtask_id}\
        )
        assert_response(resp, ETaskRecoverable)

        os.unlink(tasklockfile)
        os.chdir(config['WORKING_DIRECTORY'])

        return True

class Watchdog:
    pdesc     = None
    timestamp = None
    timeout   = None
    cycletime = 60 # 1 minutes
    running   = False
    kill_to_term = 10 # seconds

    def __init__(self, pdesc, timeout):
        self.pdesc = pdesc
        self.timeout = timeout
        self.timestamp = datetime.utcnow()

    def check(self):
        if self.pdesc.poll() == None:
            if (datetime.utcnow() - self.timestamp).seconds > self.timeout:
                self.pdesc.terminate()
                sleep(self.kill_to_term)
                if self.pdesc.poll() == None:
                    self.pdesc.kill()
            else:
                print('Bark!')
                self.running = True
                self.start()
        self.running = False

    def start(self):
        self.running = True
        thr = threading.Timer(self.cycletime, self.check)
        thr.daemon = True
        thr.start()

    def wait(self):
        while self.running:
            sleep(self.cycletime)

def assert_response(resp, ExcClass, code = 200):
    if resp.status_code != code:
        msg = 'Response was not {0}: {1}'.format(code, resp.text)
        if ExcClass:
            raise ExcClass(msg)
        else:
            print(msg)

###
def jsr(method, address, data = {}):
    return getattr(requests, method)(address, data = json.dumps(data), headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}) 

WINDOWS_DETACHED_PROCESS = 8
def run(cmd):
    sysname = platform.system()
    cmd_args = shlex.split(cmd)
    if sysname == 'Windows':
        print('  Attempting to run detached ...')
        popen = subprocess.Popen(cmd_args, creationflags=WINDOWS_DETACHED_PROCESS)
        print('  Attempting to set IDLE_PRIORITY_CLASS ...')
        psutil.Process(popen.pid).nice(psutil.IDLE_PRIORITY_CLASS)
        return popen
    elif sysname == 'Linux':
        print('  Attempting to run and nice(20) ...')
        cmd_args[0] = os.path.join(os.getcwd(), cmd_args[0])
        cmd_args += ['&']
        return subprocess.Popen(cmd_args, close_fds=True, preexec_fn=lambda : os.nice(20))
    else:
        raise Exception('Executing on OS {0} is currently not supported'.format(sysname))

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
    print('  Searching for start script:')
    for fmt in valid_fmts + [[]]:
        if fmt:
            name = PLATFORM_INFO_SEP.join([\
                prefix,\
                fmt.format(\
                    platform = platform.system(),\
                    architecture = platform.machine(),\
                    release = platform.release()\
                )\
            ])
        else:
            name = prefix
        fullpath = os.path.join(path, name)
        for ext in SCRIPT_EXTENTIONS:
            fn = '.'.join([fullpath, ext])
            print('  Attempting {0}'.format(fn))
            if os.path.exists(fn):
                print('  Found: {0}'.format(fn))
                return '.'.join([name, ext])
    return None

def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        print('Creating directory: {0}'.format(path))
        os.makedirs(path)
 
def clear_directory(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(str(e))

def parse_cli_argv():
    try:
        cli_num, node_front = sys.argv[1], sys.argv[2]
        if len(sys.argv) == 4:
            traits_file = sys.argv[3]
            try:
                print('Parsing traits:')
                with open(traits_file, 'r') as ifs:
                    for line in ifs:
                        ln = ''.join(filter(lambda s: s not in ['\r', '\n'], line))
                        if len(ln) > 0:
                            name, ver = ln.split(TRAITS_COLSEP, 1)
                            config['CLIENT_TRAITS'] += [dict(name = name, version = ver)]
                            print('  name: "{0}", version = "{1}"'.format(name, ver))
            except Exception as e:
                print('Traits syntax error {0}'.format(str(e)))
                raise e
    except Exception as e:
        print('Usage: {0} number node_frontend_host:node_frontend_port [traits_file]')
        print('Traits name and version must be separated with single space character.')
        print('Everything after the first space is treated as version.')
        sys.exit()
    return cli_num, node_front

def set_lowest_priority():
    sysname = platform.system()
    if sysname == 'Windows':
        psutil.Process(os.getpid()).nice(psutil.IDLE_PRIORITY_CLASS)
    else:
        psutil.Process(os.getpid()).nice(20)


if __name__ == '__main__':
    print(config['GRID_CALC_ROLE'])

    node_num, config['NODE_FRONTEND'] = parse_cli_argv()
    config['GRID_CALC_ROLE'] = '_'.join([config['GRID_CALC_ROLE'], str(node_num)])
    config.update(WORKING_DIRECTORY = os.path.join(tempfile.gettempdir(), '_'.join([config['GRID_CALC_ROLE'], 'work'])))
    config.update(HOME_DIRECTORY = os.path.join(os.path.expanduser("~"), config['GRID_CALC_ROLE']))
    config.update(ARCHIVE_DIRECTORY = os.path.join(tempfile.gettempdir(), '_'.join([config['GRID_CALC_ROLE'], 'arch'])))
    config.update(TASK_LOCKFILE = os.path.join(config['HOME_DIRECTORY'], 'task.lock'))
    config.update(KEYFILE = os.path.join(config['HOME_DIRECTORY'], 'key.dat'))

    create_dir_if_not_exists(config['WORKING_DIRECTORY'])
    create_dir_if_not_exists(config['ARCHIVE_DIRECTORY'])
    create_dir_if_not_exists(config['HOME_DIRECTORY'])

    print('Setting lowest priority')
    set_lowest_priority()
    
    n = Node()
    while True:
        try:
            if n.run():
                clear_directory(config['WORKING_DIRECTORY'])
                clear_directory(config['ARCHIVE_DIRECTORY'])
            else:
                sleep(n.task_req_timeout)
        except ETaskRecoverable as tre:
            print('Retring task: {0}, retrying'.format(str(tre)))
            clear_directory(config['WORKING_DIRECTORY'])
        except ETaskUnrecoverable as ture:
            print('Task is dropped: {0}'.format(str(ture)))
            clear_directory(config['WORKING_DIRECTORY'])
            clear_directory(config['ARCHIVE_DIRECTORY'])
            if os.path.exists(config['TASK_LOCKFILE']):
                os.unlink(config['TASK_LOCKFILE'])
        except ERecoverable as re:
            print('Restarting: {0}'.format(str(re)))
        except (EUnrecoverable, Exception) as ue:
            print('Unrecoverable error: {0}'.format(str(ue)))
            clear_directory(config['WORKING_DIRECTORY'])
            clear_directory(config['ARCHIVE_DIRECTORY'])
            break