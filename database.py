from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, and_, create_engine, exists, select, Date)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func, select

from datetime import datetime
from bot import DB_URL

Session = sessionmaker()
engine = create_engine(DB_URL)
Session.configure(bind=engine)
session = Session()
Base = declarative_base()

metadata = Base.metadata


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
    def get_all(cls, limit: int):
        query = select(cls).limit(limit)
        return session.execute(query).fetchall()

    def get_last_fav(self):
        query = select(Favorite).where(Favorite.user_id==self.user_id).order_by(Favorite.added_date.desc())
        return session.execute(query).fetchone()
    
    def get_all_favs(self):
        query = select(Favorite).where(Favorite.user_id==self.user_id).order_by(Favorite.added_date.desc())
        return session.execute(query).fetchall()

    def get_fav_by_pic_date(self, date: datetime.date):
        query = select(Favorite).where(
            and_(
                Favorite.user_id == self.user_id,
                Favorite.pic_date == date
            )
        )
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
        return self.pic_date > operand.pic_date

    def __lt__(self, operand):
        if not isinstance(operand, Favorite):
            raise TypeError(
                f'Неверный тип данных для сранвения: {type(operand)} is not a Favorite.'
            )
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
    def get_all(cls, limit: int):
        query = select(cls).limit(limit)
        return session.execute(query).fetchall()
               
    def commit(self):
        session.add(self)
        session.commit()

    def __repr__(self):
        return "<Fav (user_id='%i', pic='%s', added='%s'>" % (
            self.user_id, self.pic_date, self.added_date
        )
