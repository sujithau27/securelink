from fastapi import FastAPI

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