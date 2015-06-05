import os, sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from flask import *
import jsonpickle
import json
from datetime import datetime, timedelta
import threading
import time
import requests
import random, string
import tempfile
from common.common import *

bw = None

app = Flask(__name__)
app.config.update(DEBUG = True)
app.config.update(GRID_CALC_ROLE = 'SESSION_BACKEND')
app.secret_key = 'rly secret key!'

### MODELS ###
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

app.config.update(DATABASE_PATH = os.path.join(tempfile.gettempdir(), '_'.join([app.config['GRID_CALC_ROLE'], 'session'])))

engine = create_engine('sqlite:///{0}/{1}'.format(app.config['DATABASE_PATH'], 'session.db'), convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

from sqlite3 import dbapi2 as sqlite
from sqlalchemy.orm import sessionmaker, aliased, relationship
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

class UserSession(Base):
    __tablename__ = "usersession"
    __table_args__ = {'sqlite_autoincrement': True}

    id = Column(Integer(), primary_key = True, autoincrement = True)
    session_id = Column(String(64), unique = True)
    timestamp = Column(DateTime)
    user_id = Column(Integer())

    def __init__(self, uid):
        self.user_id = uid
        self.refresh()
    
    def __repr__(self):
        return ', '.join(map(lambda x: str(getattr(self, x)), filter(lambda x: not hasattr(x, '__call__'), dir(self))))

    def refresh(self):
        self.session_id = random_string(32)
        self.timestamp = datetime.utcnow()

    def session_expired(self):
        return (self.timestamp - datetime.utcnow()) >= timedelta(hours = 1)

def randomword(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

### VIEWS ###

@app.route('/register', methods=['POST'])
def registration():
    try:
        username = get_url_parameter('username')
        pw_hash = get_url_parameter('pw_hash')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    
    try:
        existing = jsr('get', bw['database'] + '/user/filter', {'username':username}).json()['result'][0]['id']
        return jsenc({'status':'failure', 'message':'Username taken'}), 422
    except:
        pass
        
    try:
        uid = jsr('post', bw['database'] + '/user', {'username':username, 'pw_hash':pw_hash}).json()['id']
        return jsenc({'status':'success', 'user_id':uid}), 200
    except:
        return jsenc({'status':'failure', 'message':'failed to register'}), 500       

@app.route('/login', methods=['GET'])
def login():
    try:
        username = get_url_parameter('username')
        pw_hash = get_url_parameter('pw_hash')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    try:
        uid = jsr('get', bw['database'] + '/user/filter', {'username':username, 'pw_hash':pw_hash}).json()['result'][0]['id']
        sid = UserSession.query.filter_by(user_id = uid).first()
        if sid:
            if not sid.session_expired():
                return jsenc({'status':'success', 'session_id':sid.session_id}), 200
            else:
                sid.refresh()
                db_session.commit()
                return jsenc({'status':'success', 'session_id':sid.session_id}), 200
        else:
            s = UserSession(uid)
            db_session.add(s)
            db_session.commit()
            return jsenc({'status':'success', 'session_id': s.session_id}), 200
    except:
        return jsenc({'status':'failure', 'message':'Unauthorized'}), 403

@app.route('/auth', methods=['GET'])
def auth():
    try:
        sesid = get_url_parameter('session_id')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    s = UserSession.query.filter_by(session_id = sesid).first()
    if s:
        if not s.session_expired():
            return jsenc({'status':'success', 'user_id': s.user_id}), 200
        else:
            return jsenc({'status':'failure', 'message':'Session expired'}), 403
    else:
        return jsenc({'status':'failure', 'message':'Unauthorized'}), 403
        
@app.route('/logout', methods=['POST'])
def logout():
    try:
        sesid = get_url_parameter('session_id')
    except:
        return jsenc({'status':'failure', 'message':'malformed syntax'}), 422
    s = UserSession.query.filter_by(session_id = sesid).first()
    if s:
        if not s.session_expired():
            db_session.delete(s)
            db_session.commit()
            return jsenc({'status':'success'}), 200
        else:
            return jsenc({'status':'failure', 'message':'Session expired'}), 403
    else:
        return jsenc({'status':'failure', 'message':'Unauthorized'}), 403
    
################################

if __name__ == '__main__':
    global port
    host = '0.0.0.0'
    beacon, port = parse_argv(sys.argv, '[nginx_proxy_port]')
    using_nginx_proxy = False
    if len(sys.argv) > 3:
        using_nginx_proxy = True
        nginx_proxy_port = int(sys.argv[3])
        print('Starting with settings: beacon:{0} self: {1}:{2} nginx_proxy_port: {3}'.format(beacon, host, port, nginx_proxy_port))
    else:
        print('Starting with settings: beacon:{0} self: {1}:{2}'.format(beacon, host, port))
    
    bw = BeaconWrapper(beacon, port if not using_nginx_proxy else nginx_proxy_port, 'services/session_backend', {'database'})
    bw.beacon_setter()
    bw.beacon_getter()
    
    if not os.path.exists(app.config['DATABASE_PATH']):
        os.makedirs(app.config['DATABASE_PATH'])
    init_db()
    
    platform_dependent_on_run(app.config['GRID_CALC_ROLE'])
    app.run(host = host, port = port)