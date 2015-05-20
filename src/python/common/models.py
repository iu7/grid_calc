from datetime import datetime, timedelta
from dateutil import parser as dt_parser
import hashlib, string, random

### Models ###

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy.orm import relationship, backref

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

table_name_d = {}
mtm_table_name_d = {}

### User methods ###
def user_init(self, **kwargs):
    if len(kwargs) < 4:
        raise Exception('User: not enough parameters')
    self.username = kwargs['username']
    self.pw_hash = kwargs['pw_hash']
    self.mail = kwargs['mail']
    self.phone = kwargs['phone']

### UserSesson methods ###

def usersession_init(self, **kwargs):
    if len(kwargs) < 1:
        raise Exception('UserSession: not enough parameters')
    self.user_id = kwargs['user_id']
    self.refresh()

def usersession_refresh(self):
    self.session_id = random_string(32)
    self.timestamp = datetime.utcnow()

### Trait methods ###

def trait_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('Trait: not enough parameters')
    self.name = kwargs['name']
    self.version = kwargs['version']

### Agent methods ###

def agent_init(self, **kwargs):
    pass

### Task methods ###

def task_init(self, **kwargs):
    if len(kwargs) < 2:
        raise Exception('Task: not enough parameters')
    self.max_time = 3600 #seconds
    self.start_script = kwargs['start_script']
    self.result_files = kwargs['result_files']

### Subtask methods ###

def subtask_init(self, **kwargs):
    if len(kwargs) < 4:
        raise Exception('Subtask: not enough parameters')
    self.task_id = kwargs['task_id']
    self.agent_id = kwargs['agent_id']
    self.status = kwargs['status']
    self.result_archive = kwargs['result_archive']

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
        user_id = Column(ForeignKey("user.id"), nullable=False),\
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
                'id'        : int,\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
\
        subtasks = relationship("Subtask"),\
        #mtm_ta = relationship("mtmTraitAgent", cascade="all, delete-orphan"),\
\
        __init__ = agent_init,\
\
        __repr__ = lambda self : 'id: {0}'.format(self.id),\
\
        to_dict = lambda self : {'id' : self.id},\
    ))

    ### MTM ###

    mtmTraitAgent = Table('mtm_traitagent', Base.metadata,\
        Column('trait_id', Integer, ForeignKey("trait.id"), nullable = False),\
        Column('agent_id', Integer, ForeignKey("agent.id"), nullable = False)\
    )

    mtmTraitTask = Table('mtm_traittask', Base.metadata,\
        Column('trait_id', Integer, ForeignKey("trait.id"), nullable = False),\
        Column('task_id', Integer, ForeignKey("task.id"), nullable = False)\
    )

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
            pk_field = 'id',\
            relationship_lst = ['agent_id', 'task_id'],\
            relationship_by_pk = lambda pk, trait: trait.agents if pk == 'agent_id' else trait.tasks,\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        name = Column(String(200), nullable = False),\
        version = Column(String(200)),\
\
        agents = relationship("Agent", secondary=mtmTraitAgent, backref='traits'),\
        tasks = relationship("Task", secondary=mtmTraitTask, backref='traits'),\
\
        __init__ = trait_init,\
\
        __repr__ = lambda self :'id: {0}, name: {1}, version: {2}'.format(self.id, self.name, self.version),\
\
        to_dict = lambda self :{'id' : self.id, 'name' : self.name, 'version' : self.version},\
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
                'result_files' : str\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        max_time = Column(Integer()),\
        start_script = Column(String(200)),\
        result_files = Column(String(4096)),\
\
        subtasks = relationship("Subtask", cascade="all, delete-orphan"),\
        #mtm_tt = relationship("mtmTraitTask", cascade="all, delete-orphan"),\
\
        __init__ = task_init,\
\
        __repr__ = lambda self :'id: {0}, max_time: {1}, start_script: {2}, result_files: {3}'.format(self.id, self.max_time, self.start_script, self.result_files),\
\
        to_dict = lambda self :{'id': self.id, 'max_time': self.max_time, 'start_script': self.start_script, 'result_files': self.result_files}\
    ))

    ### Subtask ###

    Subtask = type('Subtask', (Base,), dict(\
        __tablename__ = "subtask",\
\
        metainf = type ('metainf', (), dict(\
            col_type_d = {\
                'id'             : int,\
                'agent_id'       : int,\
                'task_id'        : int,\
                'status'         : int,\
                'result_archive' : str\
            },\
            col_type_parsers = {},\
            pk_field = 'id',\
        )),\
\
        id = Column(Integer(), primary_key = True, autoincrement = True),\
        agent_id = Column(ForeignKey("agent.id")),\
        task_id = Column(ForeignKey("task.id"), nullable=False),\
        status = Column(Integer(), nullable = False),\
        result_archive = Column(String(200)),\
\
        __init__ = subtask_init,\
\
        __repr__ = lambda self :'id: {0}, task_id: {1}, agent_id: {2}, status: {3}, result_archive: {4}'.format(self.id, self.task_id, self.agent_id, self.status, self.result_archive),\
\
        to_dict = lambda self :{'id': self.id, 'task_id': self.task_id, 'agent_id': self.agent_id, 'status': self.status, 'result_archive': self.result_archive}\
    ))

    table_name_d.update({\
        'subtask'      : Subtask,\
        'task'         : Task,\
        'agent'        : Agent,\
        'trait'        : Trait,\
        'user'         : User,\
        'usersession'      : UserSession
    })

    mtm_table_name_d.update({\
        'mtm_traitagent': ({'trait_id' : Trait}, {'agent_id' : Agent}, mtmTraitAgent),\
        'mtm_traittask' : ({'trait_id' : Trait}, {'task_id': Task}, mtmTraitTask)\
    })

###