from .. . .. . settings . python import *

def get_sqlite_connection_string():
    return 'sqlite:///{0}/{1}'.format('.', DATABASE_NAME)