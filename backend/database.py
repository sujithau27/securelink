import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_engine():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured")

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def test_connection():
    engine = get_engine()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("Database connection successful!")
        print("Result:", result.scalar())
    engine.dispose()


if __name__ == "__main__":
    test_connection()