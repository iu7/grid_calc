import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import settings
from common.models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

def init_db(dbhost, dbport = 5432):
    SQLALCHEMY_DATABASE_URI = settings.get_connection_string(dbhost, dbport)

    engine = create_engine(SQLALCHEMY_DATABASE_URI, convert_unicode=True)
    db_session = scoped_session(sessionmaker(autocommit=True, autoflush=True, bind=engine))
    Base = declarative_base()
    Base.query = db_session.query_property()

    init_models(Base)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    dbaddrs = []
    try:
        dbaddrs = sys.argv[1].split(',')
    except:
        print('Usage {0}: python init_db dbhost:dbport[,dbhost:dbport]')
    
    for dba in dbaddrs:
        try:
            h, p = dba.split(':')
            print('Processing {0}:{1}'.format(h, p))
            init_db(h, p)
        except Exception as e:
            print('Failed: {0}'.format(str(e)))

    print('Done')
