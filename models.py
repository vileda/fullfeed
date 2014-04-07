from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


engine = create_engine('sqlite:///:memory:', echo=True)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    feeds = relationship("Feed", order_by="Feed.id")


class Feed(Base):
    __tablename__ = 'feeds'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    rule = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User")


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)