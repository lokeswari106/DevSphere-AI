from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=3
)
Session = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with Session() as db:
        yield db
