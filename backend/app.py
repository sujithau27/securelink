
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from database import test_connection, get_engine

app = FastAPI(title="SecureLink API")


class DeviceRegistration(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    device_name: str = Field(min_length=1, max_length=150)


@app.get("/")
def home():
    return {
        "message": "SecureLink API is running",
        "status": "success"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


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


@app.post("/api/devices/register")
def register_device(device: DeviceRegistration):
    engine = get_engine()
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO devices (
                        device_id,
                        device_name,
                        status
                    )
                    VALUES (
                        :device_id,
                        :device_name,
                        'offline'
                    )
                    ON CONFLICT (device_id)
                    DO UPDATE SET
                        device_name = EXCLUDED.device_name
                """),
                {
                    "device_id": device.device_id,
                    "device_name": device.device_name
                }
            )

        return {
            "status": "success",
            "message": "Device registered successfully",
            "device_id": device.device_id
        }
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Device registration failed."
        )
    finally:
        engine.dispose()


@app.post("/api/devices/heartbeat")
def device_heartbeat(device: DeviceRegistration):
    engine = get_engine()
    try:
        with engine.begin() as connection:
            result = connection.execute(
                text("""
                    UPDATE devices
                    SET status = 'online',
                        last_heartbeat = CURRENT_TIMESTAMP
                    WHERE device_id = :device_id
                """),
                {"device_id": device.device_id}
            )

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found. Register it first."
                )

        return {
            "status": "success",
            "message": "Device heartbeat received",
            "device_id": device.device_id
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Heartbeat update failed."
        )
    finally:
        engine.dispose()
