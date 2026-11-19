import psycopg
from pgvector.psycopg import register_vector

from app.core.env import require_env


def connect(with_vectors: bool = True) -> psycopg.Connection:
    """Open a connection to Postgres (DATABASE_URL in .env).

    with_vectors=True teaches psycopg the pgvector type, so a vector column comes back as numbers.
    It needs the vector extension to exist, so setup_db connects with with_vectors=False first.
    """
    conn = psycopg.connect(require_env("DATABASE_URL"))
    if with_vectors:
        register_vector(conn)
    return conn
