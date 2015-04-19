from .. . .. . settings . python . settings import *

DATABASE_URIS = []
DATABASE_PORTS = []

def get_connection_string(host, port):
    return '{0}://{1}:{2}@{3}:{4}/{5}'.format(DATABASE_ENGINE, DATABASE_USER, DATABASE_PW, host, port, DATABASE_NAME)