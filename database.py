from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        MetaData, String, Table, Text, and_, create_engine,
                        exists, select, update, Date)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import PrimaryKeyConstraint
from sqlalchemy.sql import func, select

from datetime import datetime
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


# metadata = MetaData()
metadata = Base.metadata
# users = Table('users', metadata,
#     Column('id', Integer(), primary_key=True, autoincrement=True),
#     Column('user_id', Integer(), unique=True),
#     Column('first_name', String(256), nullable=False),
#     Column('last_name', String(256)),
#     Column('username', String(256)),
#     Column('is_bot', Boolean()),
#     Column('is_admin', Boolean(), default=False),
#     Column('is_leave', Boolean(), default=False),
# )
# favs = Table('favs', metadata, 
#     Column('id', Integer(), primary_key=True, autoincrement=True),
#     Column('user_id', ForeignKey("users.user_id")),
#     Column('pic_date', Date(), nullable=False),
#     Column(
#         'added_date', 
#         DateTime(timezone=True), 
#         nullable=False, 
#         server_default=func.now()
#     )
# )
# metadata.create_all(engine)

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String)
    username = Column(String)
    is_bot = Column(Boolean)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_leave = Column(Boolean, nullable=False, default=False)

    def __init__(self, user, is_admin=False):
        self.user_id = user.id
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.username = user.username
        self.is_admin = is_admin
        self.is_leave = False

    def exists(self):
        return session.query(exists().where(
            User.user_id == self.user_id)).scalar()

    @classmethod
    def get_all(cls):
        query = select(cls)
        return session.execute(query).fetchall()

    def get_last_fav(self):
        query = select(Favorite).where(Favorite.user_id==self.user_id).order_by(Favorite.id.desc())
        return session.execute(query).fetchone()
    
    def get_all_favs(self):
        query = select(Favorite).where(Favorite.user_id==self.user_id).order_by(Favorite.id.desc())
        return session.execute(query).fetchall()

    def get_neighbour_favs(self, date: str):
        """Get prev and next fav pic for User."""
        
        pass

    def commit(self):
        session.add(self)
        session.commit()

    def __repr__(self):
        return "<User (user_id='%i', first_name='%s', username='%s')>" % (
            self.user_id, self.first_name, self.username
        )


class Favorite(Base):
    __tablename__ = "favs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    pic_date = Column(Date, nullable=False)
    added_date = Column(DateTime, nullable=False, server_default=func.now())

    def __init__(self, user_id: int, date: datetime.date):
        self.user_id = user_id
        self.pic_date = date

    def __gt__(self, operand):
        if not isinstance(operand, Favorite):
            raise TypeError(
                f'Неверный тип данных для сранвения: {type(operand)} is not a Favorite.'
            )
        # a = datetime.strptime(self.pic_date, '%Y-%m-%d')
        # print(f'Date(self): {a}')
        # b = datetime.strptime(operand.pic_date, '%Y-%m-%d')
        # print(f'Date(operand): {b}')
        # return a > b
        return self.pic_date > operand.pic_date

    def __lt__(self, operand):
        if not isinstance(operand, Favorite):
            raise TypeError(
                f'Неверный тип данных для сранвения: {type(operand)} is not a Favorite.'
            )
        # a = Date(datetime.strptime(self.pic_date, '%Y-%m-%d'))
        # print(f'Date(self): {a}')
        # b = Date(datetime.strptime(operand.pic_date, '%Y-%m-%d'))
        # print(f'Date(operand): {b}')
        # return a < b
        return self.pic_date < operand.pic_date

    def exists(self):
        return session.query(
            exists().where(
                and_(
                    Favorite.user_id == self.user_id,
                    Favorite.pic_date == self.pic_date
                )
            )).scalar()
    
    @classmethod
    def get_all(cls):
        query = select(cls)
        return session.execute(query).fetchall()
               
    def commit(self):
        session.add(self)
        session.commit()

    def __repr__(self):
        return "<Fav (user_id='%i', pic_date='%s'>" % (
            self.user_id, self.pic_date
        )
