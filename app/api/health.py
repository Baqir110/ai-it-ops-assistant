import socket
import time
from fastapi import APIRouter

router = APIRouter(prefix="/services", tags=["Service Checks"])


@router.get("/{name}")
def check_service_health(name: str, host: str, port: int):
    start = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=3.0)
        sock.close()
        latency = round((time.time() - start) * 1000, 2)
        return {"service": name, "status": "healthy", "latency_ms": latency}
    except Exception as e:
        return {"service": name, "status": "unhealthy", "error": str(e)}
