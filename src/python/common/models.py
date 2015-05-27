from datetime import datetime, timedelta
from dateutil import parser as dt_parser
import hashlib, string, random

### Models ###

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import BYTEA

table_name_d = {}
mtm_table_name_d = {}

### Common methods ###

def fill_object(self, field_d, **kwargs):
    for k, v in kwargs.items():
        if k in field_d:
            setattr(self, k, v)
        else:
            raise Exception('{0}: extra parameter <{1}> in __init__!').format(self.__name__, k)

### User methods ###
def user_init(self, **kwargs):
    if len(kwargs) < 4:
        raise Exception('User: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)

### UserSesson methods ###

def usersession_init(self, **kwargs):
    if len(kwargs) < 1:
        raise Exception('UserSession: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)
    self.refresh()

def usersession_refresh(self):
    self.session_id = random_string(32)
    self.timestamp = datetime.utcnow()

### Trait methods ###

def trait_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('Trait: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)

### Agent methods ###

def agent_init(self, **kwargs):
    fill_object(self, self.metainf.col_type_d, **kwargs)

### Task methods ###

def task_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('Task: not enough parameters')
    self.max_time = 3600 #seconds
    fill_object(self, self.metainf.col_type_d, **kwargs)

### Subtask methods ###

def subtask_init(self, **kwargs):
    if len(kwargs) < 3:
        raise Exception('Subtask: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)
    self.dateplaced = datetime.utcnow()

### MTM ###

def mtm_traitagent_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('MTMTraitAgent: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)

def mtm_traittask_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('MTMTraitTask: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)

###

def init_models(Base):
    ### User ###

    Base.to_dict = lambda self: {f:getattr(self, f) for f in self.metainf.col_type_d.keys()}

    User = type('User', (Base,), dict(\
        __tablename__ = "user",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'      : int,\
                'username': str,\
                'pw_hash' : str,\
                'mail'    : str,\
                'phone'   : str\
            },\
            col_type_parsers = {},\
            filename_fields = [],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        username = Column(String(100), unique=True),\
        pw_hash = Column(String(256)),\
        mail = Column(String(200)),\
        phone = Column(String(11)),\
\
        __init__ = user_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    ### UserSession ###

    UserSession = type('UserSession', (Base,), dict(\
        __tablename__ = "usersession",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'id'        : int,\
                'session_id': str,\
                'timestamp' : datetime,\
                'user_id'   : int\
            },\
            col_type_parsers = {\
                'timestamp' : dt_parser.parse\
            },\
            filename_fields = [],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        session_id = Column(String(32), unique = True),\
        timestamp = Column(DateTime),\
        user_id = Column(Integer()),\
\
        __init__ = usersession_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()]),\
\
        refresh = usersession_refresh,\
        session_expired = lambda self :(self.timestamp - datetime.utcnow()) >= timedelta(hours = 1)\
    ))

    ### Agent ###

    Agent = type('Agent', (Base,), dict(\
        __tablename__ = "agent",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'id' : int,\
            },\
            col_type_parsers = {},\
            filename_fields = [],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
\
        __init__ = agent_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    ### Task ###

    Task = type('Task', (Base,), dict(\
        __tablename__ = "task",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'           : int,\
                'max_time'     : int,\
                'archive_name' : str,\
            },\
            col_type_parsers = {},\
            filename_fields = ['archive_name'],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        max_time = Column(Integer()),\
        archive_name = Column(String(200), nullable = False),\
\
        __init__ = task_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    ### Trait ###

    Trait = type('Trait', (Base,), dict(\
        __tablename__ = "trait",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'id'      : int,\
                'name'    : str,\
                'version' : str\
            },\
            col_type_parsers = {},\
            filename_fields = [],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        name = Column(String(200), nullable = False),\
        version = Column(String(200)),\
\
        __table_args__ = (UniqueConstraint('name', 'version', name='_uc_name_version'),),\
\
        __init__ = trait_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    ### Subtask ###

    Subtask = type('Subtask', (Base,), dict(\
        __tablename__ = "subtask",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'           : int,\
                'agent_id'     : int,\
                'task_id'      : int,\
                'archive_name' : str,\
                'status'       : str,\
                'dateplaced'   : datetime
            },\
            col_type_parsers = {\
                'dateplaced'   : dt_parser.parse,\
            },\
            filename_fields = ['archive_name'],\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        agent_id = Column(Integer()),\
        task_id = Column(Integer()),\
        archive_name = Column(String(200), nullable = False),\
        status = Column(String(200)),\
        dateplaced = Column(DateTime),\
\
        __init__ = subtask_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    ### MTM ###

    mtmTraitAgent = type('mtmTraitAgent', (Base,), dict(\
        __tablename__ = "mtm_traitagent",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'trait_id' : int,\
                'agent_id' : int\
            },\
            col_type_parsers = {},\
            filename_fields = [],\
            pk_field = None,\
        )),\
\
        trait_id = Column(Integer(), primary_key = True),\
        agent_id = Column(Integer(), primary_key = True),\
\
        __init__ = mtm_traitagent_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    mtmTraitTask = type('mtmTraitTask', (Base,), dict(\
        __tablename__ = "mtm_traittask",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'trait_id' : int,\
                'task_id'  : int\
            },\
            col_type_parsers = {},\
            filename_fields = [],\
            pk_field = None,\
        )),\
\
        trait_id = Column(Integer(), primary_key = True),\
        task_id = Column(Integer(), primary_key = True),\
\
        __init__ = mtm_traittask_init,\
        __repr__ = lambda self :', '.join(['{0}: {1}'.format(f, getattr(self, f)) for f in col_type_d.keys()])\
    ))

    table_name_d.update({\
        'subtask'        : Subtask,\
        'task'           : Task,\
        'agent'          : Agent,\
        'trait'          : Trait,\
        'user'           : User,\
        'usersession'    : UserSession,\
        'mtm_traitagent' : mtmTraitAgent,\
        'mtm_traittask'  : mtmTraitTask\
    })

    mtm_table_name_d.update({\
        'mtm_traitagent' : (),\
        'mtm_traittask'  : ()\
    })

###