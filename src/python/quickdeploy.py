import subprocess
import sys, os

DETACHED_PROCESS = 8
def run(str):
    spl = str.split('/')
    subprocess.Popen('cmd /k py ' + spl[1], \
        creationflags=DETACHED_PROCESS, \
        close_fds=True, \
        cwd = (os.getcwd().replace('\\','/') + '/'+spl[0]))

beacon_address = '127.0.0.1:1666'

run('beacon_backend/beacon_backend.py 1666')
run('file_backend/file_backend.py ' + beacon_address + ' 1667')
run('data_backend/data_backend.py 0 ' + beacon_address + ' localhost:5432 1668')
run('sharding_backend/sharding_backend.py ' + beacon_address + ' 1669 localhost:1668')
run('logic_backend/logic_backend.py ' + beacon_address + ' 1670')
run('user_frontend/user_frontend.py ' + beacon_address + ' 1671')
run('session_backend/session_backend.py ' + beacon_address + ' 1672')

run('balancer_backend/balancer_backend.py ' + beacon_address + ' 1673')
run('node_frontend/node_frontend.py ' + beacon_address + ' 1674')