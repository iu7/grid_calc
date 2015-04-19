from datetime import datetime, timedelta
from dateutil import parser as dt_parser
import hashlib, string, random

### Models ###

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

class User(Base):
    class metainf:
        col_type_d = {\
            'id'      : int,\
            'username': str,\
            'pw_hash' : str,\
            'mail'    : str,\
            'phone'   : str\
        }
        col_type_parsers = {}
        pk_field = 'id'

    id = Column(Integer(), primary_key = True)
    username = Column(String(100), unique=True)
    pw_hash = Column(String(256))
    mail = Column(String(200))
    phone = Column(String(11))
    
    sessions = relationship("UserSession", cascade="all, delete-orphan")
    posts = relationship("Post")
    comments = relationship("Comment")

    def __init__(self, **kwargs):
        if len(kwargs) < 4:
            raise Exception('User: not enough parameters')
        self.username = kwargs['username']
        self.pw_hash = kwargs['pw_hash']
        self.mail = kwargs['mail']
        self.phone = kwargs['phone']

    def __repr__(self):
        return 'id: {0}, username: {1}, mail: {2}, phone: {3}'.format(self.id, self.username, self.mail, self.phone)    

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'password': self.pw_hash, 'mail': self.mail, 'phone': self.phone}

class UserSession(Base):
    class metainf:
        col_type_d = {\
            'id'        : int,\
            'session_id': str,\
            'timestamp' : datetime,\
            'user_id'   : int\
        }
        col_type_parsers = {\
            'timestamp' : dt_parser.parse\
        }
        pk_field = 'id'

    id = Column(Integer(), primary_key = True)
    session_id = Column(String(32), unique = True)
    timestamp = Column(DateTime)
    user_id = Column(ForeignKey("user.id"), nullable=False)
    
    def __init__(self, **kwargs):
        if len(kwargs) < 1:
            raise Exception('UserSession: not enough parameters')
        self.user_id = kwargs['user_id']
        self.refresh()
   
    def refresh(self):
        self.session_id = random_string(32)
        self.timestamp = datetime.utcnow()
   
    def session_expired(self):
        return (self.timestamp - datetime.utcnow()) >= timedelta(hours = 1)

###