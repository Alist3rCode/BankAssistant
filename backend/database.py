from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from config import settings

DATABASE_URL = f"sqlite:///{settings.db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    # WAL mode pour de meilleures performances concurrentes
    cursor.execute("PRAGMA journal_mode=WAL")
    # Intégrité référentielle
    cursor.execute("PRAGMA foreign_keys=ON")
    # Sync moins agressif pour les performances (risque minimal sur home server)
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from models.models import Base
    Base.metadata.create_all(bind=engine)
