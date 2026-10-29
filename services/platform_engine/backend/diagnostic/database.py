"""Bound database connection waits independently of the GUI startup deadline."""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url


def database_engine(url: str):
    backend = make_url(url).get_backend_name()
    connect_args = {}
    if backend == "sqlite":
        connect_args["check_same_thread"] = False
    elif backend == "postgresql":
        connect_args["connect_timeout"] = max(1, min(30, int(
            os.getenv("AI_CAR_DB_CONNECT_TIMEOUT_S", "3")
        )))
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)
