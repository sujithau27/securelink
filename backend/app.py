
from fastapi import FastAPI, HTTPException
from database import test_connection

app = FastAPI(title="SecureLink API")


@app.get("/")
def home():
    return {
        "message": "SecureLink API is running",
        "status": "success"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/db-health")
def database_health():
    try:
        test_connection()
        return {
            "status": "success",
            "message": "Database connection successful"
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check server logs."
        )
