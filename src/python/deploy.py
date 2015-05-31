
#
# Sample usage:
# ./deploy.py 10.0.0.10:5432,10.0.0.20:5432 2>/dev/null

import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import subprocess, platform, shlex
from common.sharding_settings import SHARDS_COUNT

WINDOWS_DETACHED_PROCESS = 8

def run(cmd):
    sysname = platform.system()
    cmd_args = shlex.split(cmd)
    if sysname == 'Windows':
        args = ['py'] + cmd_args
        subprocess.Popen(args, creationflags=WINDOWS_DETACHED_PROCESS, close_fds=True)
    elif sysname == 'Linux':
        args = ['konsole', '--new-tab', '-e', 'python'] + cmd_args + ['&']
        subprocess.Popen(args, close_fds=True)
    else:
        raise Exception('Auto deploy on OS {0} is currently not supported'.format(sysname))

def get_data_backends_run_fmt(shards_count, dbaddrs, fmt_template):
    res = []
    for i in range(shards_count):
        res += [fmt_template.format(shnum = i, dbaddr = dbaddrs[i])]
    return res

def auto_adjust_port_run(run_cmd_fmt, port_from, port_to, beacon_address = None):
    for port in range(port_from, port_to):
        run_cmd = run_cmd_fmt.format(port = port, beacon = beacon_address)
        print(run_cmd)
        try:
            run(run_cmd)
            return port;
        except Exception as e:
            print('FAILED: {0}'.format(str(e)))

    raise Exception('Unable to run in specified range {0} - {1}!'.format(port_from, port_to))

def auto_port_deploy_beacon(beacon_run_fmt, beacon_address_fmt, port_start = 5000, port_max = 65535):
    port = auto_adjust_port_run(beacon_run_fmt, port_start, port_max)
    beacon_address = beacon_address_fmt.format(port = port)
    return port, beacon_address

def auto_port_deploy_data(beacon_address, data_backend_fmt_fmt, port_start = 5000, port_max = 65535):
    dbc_fmts = get_data_backends_run_fmt(SHARDS_COUNT, dbaddrs, data_backend_fmt_fmt)
    dbc_ports = []
    port = port_start
    for dbc_fmt in dbc_fmts:
        port = auto_adjust_port_run(dbc_fmt, port + 1, port_max, beacon_address)
        dbc_ports += [port]
    return port, dbc_ports

def auto_port_deploy(beacon_address, backends_run_fmt, port_start = 5000, port_max = 65535):
    port = port_start
    for backend_fmt in backends_run_fmt:
        port = auto_adjust_port_run(backend_fmt, port + 1, port_max, beacon_address)
 
if __name__ == '__main__':
    beacon_host = 'localhost'
    dbaddrs = None
    try:
        sdbaddrs = sys.argv[1]
        dbaddrs = sdbaddrs.split(',')
    except Exception as e:
        print('Usage {0}: dbhost:dbport[,dbhost:dbport]')
        sys.exit()

    beacon_addr_fmt = "{0}:{{port}}".format(beacon_host)
    curport, beacon_address = auto_port_deploy_beacon('beacon_backend/beacon_backend.py {port}', beacon_addr_fmt)
    curport, data_backend_ports = auto_port_deploy_data(beacon_address, 'data_backend/data_backend.py {shnum} {{beacon}} {dbaddr} {{port}}', curport + 1)
    dbcaddrs = ','.join(list(map(lambda dbp: 'localhost:{0}'.format(dbp), data_backend_ports)))
    auto_port_deploy(
        beacon_address,\
        [\
            'sharding_backend/sharding_backend.py {{beacon}} {{port}} {dbcaddrs}'.format(dbcaddrs = dbcaddrs),\
            'file_backend/file_backend.py {beacon} {port}',\
            'balancer_backend/balancer_backend.py {beacon} {port}',\
            'node_frontend/node_frontend.py {beacon} {port}'
        ],\
        curport + 1,\
    )