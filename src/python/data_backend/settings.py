import settings.python.settings as gs

DATABASE_URIS = [\
  'pg_shd0_master',\
  'pg_shd0_slave'\
]

DATABASE_PORTS = [\
  5432,\
  5432\
]

def get_connection_string(host, port):
    return '{0}://{1}:{2}@{3}:{4}/{5}'.format(gs.DATABASE_ENGINE, gs.DATABASE_USER, gs.DATABASE_PW, host, port, gs.DATABASE_NAME)