
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from database import test_connection, get_engine

app = FastAPI(title="SecureLink API", version="0.1.0")


# -------------------- REQUEST MODELS --------------------

class DeviceRegistration(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    device_name: str = Field(min_length=1, max_length=150)


class SecurityEvent(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)


class SecurityAlert(BaseModel):
    device_id: str = Field(min_length=1, max_length=100)
    alert_type: str = Field(min_length=1, max_length=100)
    severity: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=500)


# -------------------- HOME --------------------

@app.get("/")
def home():
    return {
        "message": "SecureLink API is running",
        "status": "success"
    }


# -------------------- HEALTH CHECK --------------------

@app.get("/health")
def health():
    return {"status": "healthy"}


# -------------------- DATABASE HEALTH --------------------

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


# -------------------- REGISTER DEVICE --------------------

@app.post("/api/devices/register")
def register_device(device: DeviceRegistration):
    engine = get_engine()

    try:
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO devices (
                        device_id, device_name, status
                    )
                    VALUES (
                        :device_id, :device_name, 'offline'
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


# -------------------- DEVICE HEARTBEAT --------------------

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


# -------------------- LIST DEVICES --------------------

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


# -------------------- CREATE SECURITY EVENT --------------------

@app.post("/api/events")
def create_event(event: SecurityEvent):
    engine = get_engine()

    try:
        with engine.begin() as connection:
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

            result = connection.execute(
                text("""
                    INSERT INTO events (
                        device_id, event_type, description
                    )
                    VALUES (
                        :device_id, :event_type, :description
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
            detail="Could not record security event."
        )

    finally:
        engine.dispose()


# -------------------- LIST SECURITY EVENTS --------------------

@app.get("/api/events")
def list_events():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT id, device_id, event_type, description
                    FROM events
                    ORDER BY id DESC
                """)
            )

            events = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "status": "success",
            "count": len(events),
            "events": events
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve security events."
        )

    finally:
        engine.dispose()


# -------------------- CREATE SECURITY ALERT --------------------

@app.post("/api/alerts")
def create_alert(alert: SecurityAlert):
    engine = get_engine()

    try:
        with engine.begin() as connection:
            device = connection.execute(
                text("""
                    SELECT device_id
                    FROM devices
                    WHERE device_id = :device_id
                """),
                {"device_id": alert.device_id}
            ).first()

            if device is None:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found. Register it first."
                )

            result = connection.execute(
                text("""
                    INSERT INTO alerts (
                        device_id,
                        alert_type,
                        severity,
                        message,
                        is_resolved
                    )
                    VALUES (
                        :device_id,
                        :alert_type,
                        :severity,
                        :message,
                        FALSE
                    )
                    RETURNING id
                """),
                {
                    "device_id": alert.device_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message
                }
            )

            alert_id = result.scalar()

        return {
            "status": "success",
            "message": "Security alert created",
            "alert_id": alert_id
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not create security alert."
        )

    finally:
        engine.dispose()


# -------------------- LIST SECURITY ALERTS --------------------

@app.get("/api/alerts")
def list_alerts():
    engine = get_engine()

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT id, device_id, alert_type, severity,
                           message, is_resolved, created_at
                    FROM alerts
                    ORDER BY created_at DESC
                """)
            )

            alerts = [
                dict(row._mapping)
                for row in result
            ]

        return {
            "status": "success",
            "count": len(alerts),
            "alerts": alerts
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve security alerts."
        )

    finally:
        engine.dispose()
