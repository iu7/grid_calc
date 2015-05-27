from glob_settings import *

def get_sqlite_connection_string():
    return 'sqlite:///{0}/{1}'.format('.', DATABASE_NAME)