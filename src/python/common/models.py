from datetime import datetime, timedelta
from dateutil import parser as dt_parser
import hashlib, string, random

### Models ###

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import BYTEA

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

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
    if len(kwargs) < 4:
        raise Exception('Subtask: not enough parameters')
    fill_object(self, self.metainf.col_type_d, **kwargs)

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
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        username = Column(String(100), unique=True),\
        pw_hash = Column(String(256)),\
        mail = Column(String(200)),\
        phone = Column(String(11)),\
\
        sessions = relationship("UserSession", cascade="all, delete-orphan"),\
\
        __init__ = user_init,\
\
        __repr__ = lambda self :'id: {0}, username: {1}, mail: {2}, phone: {3}'.format(self.id, self.username, self.mail, self.phone),\
\
        to_dict = lambda self :{'id': self.id, 'username': self.username, 'password': self.pw_hash, 'mail': self.mail, 'phone': self.phone}\
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
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        session_id = Column(String(32), unique = True),\
        timestamp = Column(DateTime),\
        user_id = Column(ForeignKey("user.id")),\
\
        __init__ = usersession_init,\
\
        __repr__ = lambda self :'id: {0}, user_id: {1}, sesson_id: {2}, timestamp: {3}'.format(self.id, self.user_id, self.session_id, self.timestamp),\
\
        refresh = usersession_refresh,\
\
        session_expired = lambda self :(self.timestamp - datetime.utcnow()) >= timedelta(hours = 1),\
\
        to_dict = lambda self :{'id' : self.id, 'session_id' : self.session_id, 'timestamp' : self.timestamp, 'user_id' : self.user_id},\
    ))

    ### Agent ###

    Agent = type('Agent', (Base,), dict(\
        __tablename__ = "agent",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'id'           : int,\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
\
        subtasks = relationship("Subtask"),\
        mtmTraits = relationship("mtmTraitAgent"),\
\
        __init__ = agent_init,\
\
        __repr__ = lambda self : 'id: {0}'.format(self.id),\
\
        to_dict = lambda self : {'id' : self.id},\
    ))

    ### Task ###

    Task = type('Task', (Base,), dict(\
        __tablename__ = "task",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'           : int,\
                'max_time'     : int,\
                'start_script' : str,\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        max_time = Column(Integer()),\
        start_script = Column(String(200)),\
\
        subtasks = relationship("Subtask", cascade="all, delete-orphan"),\
        mtmTraits = relationship("mtmTraitTask"),\
\
        __init__ = task_init,\
\
        __repr__ = lambda self :'id: {0}, max_time: {1}, start_script: {2}, result_files: {3}'.format(self.id, self.max_time, self.start_script, self.result_files),\
\
        to_dict = lambda self :{'id': self.id, 'max_time': self.max_time, 'start_script': self.start_script, 'result_files': self.result_files}\
    ))

    ### Trait ###

    Trait = type('Trait', (Base,), dict(\
        __tablename__ = "trait",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'id'        : int,\
                'name'      : str,\
                'version'   : str\
            },\
            col_type_parsers = {},\
            pk_field = 'id'\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        name = Column(String(200), nullable = False),\
        version = Column(String(200)),\
\
        mtmAgents = relationship("mtmTraitAgent"),\
        mtmTasks = relationship("mtmTraitTask"),\
\
        __init__ = trait_init,\
\
        __repr__ = lambda self :'id: {0}, name: {1}, version: {2}'.format(self.id, self.name, self.version),\
\
        to_dict = lambda self :{'id' : self.id, 'name' : self.name, 'version' : self.version},\
    ))

    ### Subtask ###

    Subtask = type('Subtask', (Base,), dict(\
        __tablename__ = "subtask",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'                : int,\
                'agent_id'          : int,\
                'task_id'           : int,\
                'result_archive'    : str,\
                'status'            : int,\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        agent_id = Column(ForeignKey("agent.id")),\
        task_id = Column(ForeignKey("task.id")),\
        result_archive = Column(BYTEA),\
        status = Column(Integer(), nullable = False),\
\
        __init__ = subtask_init,\
\
        __repr__ = lambda self :'id: {0}, task_id: {1}, agent_id: {2}, status: {3}'.format(self.id, self.task_id, self.agent_id, self.status),\
\
        to_dict = lambda self :{'id': self.id, 'task_id': self.task_id, 'agent_id': self.agent_id, 'status': self.status, 'result_archive': self.result_archive}\
    ))

    ### MTM ###

    mtmTraitAgent = type('mtmTraitAgent', (Base,), dict(\
        __tablename__ = "mtm_traitagent",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'trait_id'  : int,\
                'agent_id'  : int\
            },\
            col_type_parsers = {},\
            pk_field = None,\
        )),\
\
        trait_id = Column(ForeignKey('trait.id'), primary_key = True),\
        agent_id = Column(ForeignKey('agent.id'), primary_key = True),\
\
        traits = relationship("Trait"),\
        agents = relationship("Agent"),\
\
        __init__ = mtm_traitagent_init,\
\
        __repr__ = lambda self :'trait_id: {1}, agent_id: {2}'.format(self.trait_id, self.agent_id),\
\
        to_dict = lambda self :{'trait_id' : self.trait_id, 'agent_id' : self.agent_id},\
    ))

    mtmTraitTask = type('mtmTraitTask', (Base,), dict(\
        __tablename__ = "mtm_traittask",\
\
        metainf = type('metainf', (), dict(\
            col_type_d = {\
                'trait_id'  : int,\
                'task_id'   : int\
            },\
            col_type_parsers = {},\
            pk_field = None,\
        )),\
\
        trait_id = Column(ForeignKey('trait.id'), primary_key = True),\
        task_id = Column(ForeignKey('task.id'), primary_key = True),\
\
        __init__ = mtm_traittask_init,\
\
        __repr__ = lambda self :'trait_id: {1}, task_id: {2}'.format(self.trait_id, self.task_id),\
\
        to_dict = lambda self :{'trait_id' : self.trait_id, 'task_id' : self.task_id},\
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