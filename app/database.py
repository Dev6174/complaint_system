# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Enforce foreign key constraints in SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Connection pool sizing: the default SQLAlchemy pool (5 + 10 overflow = 15
# max connections) was too small under concurrent load. Load testing showed
# requests queuing up waiting for a free connection once concurrency rose,
# inflating response times from ~10ms to several seconds. Increased here to
# comfortably handle expected concurrent traffic against Postgres.
pool_kwargs = {}
if not settings.DATABASE_URL.startswith("sqlite"):
    pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_pre_ping": True,  # avoids using dead connections after idle periods
    }

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **pool_kwargs)

# SQLite foreign key enforcement
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
