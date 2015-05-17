from glob_settings import *

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