
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from database import test_connection, get_engine

app = FastAPI(title="SecureLink API", version="0.1.0")


# Request models
class DeviceRegistration(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    device_name: str = Field(min_length=1, max_length=150)


class SecurityEvent(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)


# Home
@app.get("/")
def home():
    return {
        "message": "SecureLink API is running",
        "status": "success"
    }


# Health check
@app.get("/health")
def health():
    return {"status": "healthy"}


# Database health check
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


# Register a device
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


# Receive device heartbeat
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


# List registered devices
@app.get("/api/devices")
def list_devices():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT device_id, device_name, status,
                           last_heartbeat, created_at
                    FROM devices
                    ORDER BY created_at DESC
                """)
            )

            devices = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "status": "success",
            "count": len(devices),
            "devices": devices
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve devices."
        )

    finally:
        engine.dispose()


# Record a cybersecurity event
@app.post("/api/events")
def create_event(event: SecurityEvent):
    engine = get_engine()

    try:
        with engine.begin() as connection:
            # Confirm that the device is registered
            device = connection.execute(
                text("""
                    SELECT device_id
                    FROM devices
                    WHERE device_id = :device_id
                """),
                {"device_id": event.device_id}
            ).first()

            if device is None:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found. Register it first."
                )

            # Save the event in the database
            result = connection.execute(
                text("""
                    INSERT INTO events (
                        device_id,
                        event_type,
                        description
                    )
                    VALUES (
                        :device_id,
                        :event_type,
                        :description
                    )
                    RETURNING id
                """),
                {
                    "device_id": event.device_id,
                    "event_type": event.event_type,
                    "description": event.description
                }
            )

            event_id = result.scalar()

        return {
            "status": "success",
            "message": "Security event recorded",
            "event_id": event_id
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not record security event. Check the events table structure."
        )

    finally:
        engine.dispose()
