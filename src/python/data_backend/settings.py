import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from common.global_settings import *

DATABASE_URIS = [\
  'pg_shd0_master',\
  'pg_shd0_slave'\
]

DATABASE_PORTS = [\
  5432,\
  5432\
]

def get_connection_string(host, port):
    return '{0}://{1}:{2}@{3}:{4}/{5}'.format(DATABASE_ENGINE, DATABASE_USER, DATABASE_PW, host, port, DATABASE_NAME)