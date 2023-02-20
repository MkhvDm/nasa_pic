from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, Table, Text, and_, create_engine,
                        exists, select, update)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql import func, select

from bot import DB_URL

# Configure a Session class.
Session = sessionmaker()

# Create an engine which the Session will use for connections.
engine = create_engine(DB_URL)

# Create a configured Session class.
Session.configure(bind=engine)

# Create a Session
session = Session()

# Create a base for the models to build upon.
Base = declarative_base()

metadata = MetaData()
users = Table('users', metadata, 
    Column('user_id', Integer(), primary_key=True),
    Column('first_name', String(256), nullable=False),
    Column('last_name', String(256)),
    Column('username', String(256)),
    Column('is_bot', Boolean())
)
favs = Table('favs', metadata, 
    Column('id', Integer(), primary_key=True, autoincrement=True),
    Column('user_id', ForeignKey("users.user_id")),
    Column('pic_date', String(256), nullable=False)
)
metadata.create_all(engine)

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    username = Column(String)
    is_bot = Column(Boolean)

    def __init__(self, user):
        self.user_id = user.id
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.username = user.username

    def exists(self):
        return session.query(exists().where(
            User.user_id == self.user_id)).scalar()

    def get_fav(self):
        query = select(Favorite).where(Favorite.user_id==self.user_id).order_by(Favorite.id.desc())
        return session.execute(query).fetchone()

    def commit(self):
        session.add(self)
        session.commit()

    def __repr__(self):
        return "<User (user_id='%i', first_name='%s', username='%s')>" % (
            self.user_id, self.first_name, self.username
        )


class Favorite(Base):
    __tablename__ = "favs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    pic_date = Column(String, nullable=False)

    def __init__(self, user_id: int, date: str):
        self.user_id = user_id
        self.pic_date = date

    def exists(self):
        return session.query(
            exists().where(
                and_(
                    Favorite.user_id == self.user_id,
                    Favorite.pic_date == self.pic_date
                )
            )).scalar()
               
    def commit(self):
        session.add(self)
        session.commit()

    def __repr__(self):
        return "<Fav (user_id='%i', pic_date='%s'>" % (
            self.user_id, self.pic_date
        )
