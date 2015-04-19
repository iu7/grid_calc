from settings import *
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine(DATABASE_CONNECTION_STRING, convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

from sqlite3 import dbapi2 as sqlite
from sqlalchemy.orm import sessionmaker, aliased, relationship

from datetime import datetime, timedelta
import hashlib, string, random

### Models ###

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import *

def random_string(size):
    return ''.join([random.choice(string.ascii_letters) for i in range(size)])

class User(Base):
    __tablename__ = "user"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer(), primary_key = True)
    username = Column(String(100), unique=True)
    pw_hash = Column(String(256))
    mail = Column(String(200))
    phone = Column(String(11))
    
    sessions = relationship("UserSession", cascade="all, delete-orphan")
    posts = relationship("Post")
    comments = relationship("Comment")
    
    def __init__(self, username, pw_hash, phone, mail):
        self.username = username
        self.pw_hash = pw_hash
        self.mail = mail
        self.phone = phone

    def __repr__(self):
        return 'id: {0}, username: {1}, mail: {2}, phone: {3}'.format(self.id, self.username, self.mail, self.phone)
    
    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'password': self.pw_hash, 'mail': self.mail, 'phone': self.phone}

class UserSession(Base):
    __tablename__ = "usersession"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer(), primary_key = True)
    session_id = Column(String(32), unique = True)
    timestamp = Column(DateTime)
    user_id = Column(ForeignKey("user.id"), nullable=False)
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.refresh()
   
    def refresh(self):
        self.session_id = random_string(32)
        self.timestamp = datetime.utcnow()
   
    def session_expired(self):
        return (self.timestamp - datetime.utcnow()) >= timedelta(hours = 1)

class Post(Base):
    __tablename__ = "post"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer(), primary_key = True)
    caption = Column(String(100))
    text = Column(Text())
    author_id = Column(ForeignKey("user.id"), nullable=False)
    
    comments = relationship("Comment", cascade="all, delete-orphan")
    
    def __init__(self, user_id, caption, text):
        self.author_id = user_id
        self.caption = caption
        self.text = text
        
    def __repr__(self):
        return 'id: {0}, author: {1}, caption: {2}'.format(self.id, self.author_id, self.caption)

    def to_dict(self):
        return {'id': self.id, 'author_id': self.author_id, 'caption': self.caption, 'text': self.text}
    
    def to_dict_short(self):
        return {'id': self.id, 'author_id': self.author_id, 'caption': self.caption}

class Comment(Base):
    __tablename__ = "comment"
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer(), primary_key = True)
    text = Column(Text())
    author_id = Column(ForeignKey("user.id"), nullable=False)
    post_id = Column(ForeignKey("post.id"), nullable=False)
    deleted = Column(Boolean(), default = False)
    
    def __init__(self, user_id, post_id, text):
        self.author_id = user_id
        self.post_id = post_id
        self.text = text
        
    def __repr__(self):
        return 'id: {0}, author: {1}'.format(self.id, self.author_id)

    def to_dict(self):
        return {'id': self.id, 'author_id': self.author_id, 'post_id': self.post_id, 'text': self.text if not self.deleted else '', 'deleted': self.deleted}
        
    def delete(self):
        self.deleted = True

###

def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)