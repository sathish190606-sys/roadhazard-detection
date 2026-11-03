import os
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

logger = logging.getLogger(__name__)

def normalize_database_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy drivers."""
    if url.startswith("oracle://"):
        return url.replace("oracle://", "oracle+oracledb://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and not ("+" in url.split("://")[0]):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

db_url = normalize_database_url(settings.DATABASE_URL)

connect_args: Dict[str, Any] = {}
engine_kwargs: Dict[str, Any] = {
    "pool_pre_ping": True,
}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
elif "oracle" in db_url:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 3600
elif "postgres" in db_url:
    connect_args["connect_timeout"] = 15
    connect_args["keepalives"] = 1
    connect_args["keepalives_idle"] = 30
    connect_args["keepalives_interval"] = 10
    connect_args["keepalives_count"] = 5
    engine_kwargs["connect_args"] = connect_args
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_oracle() -> bool:
    return "oracle" in engine.dialect.name.lower()

def is_postgres() -> bool:
    return "postgres" in engine.dialect.name.lower()

def is_sqlite() -> bool:
    return "sqlite" in engine.dialect.name.lower()

def call_stored_procedure(proc_name: str, params: Optional[List[Any]] = None) -> Any:
    """Call a PL/SQL or PL/pgSQL stored procedure using the raw DBAPI connection cursor."""
    with engine.raw_connection() as raw_conn:
        cursor = raw_conn.cursor()
        try:
            if is_oracle():
                result = cursor.callproc(proc_name, params or [])
                raw_conn.commit()
                return result
            else:
                param_list = params or []
                placeholders = ", ".join(["%s"] * len(param_list)) if not is_sqlite() else ", ".join(["?"] * len(param_list))
                cursor.execute(f"CALL {proc_name}({placeholders})", param_list)
                raw_conn.commit()
                return None
        finally:
            cursor.close()
