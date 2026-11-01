import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User
from backend.app.routes.auth import get_password_hash, router as auth_router
from backend.app.routes.hazards import router as hazards_router
from backend.app.routes.robots import router as robots_router
from backend.app.routes.stats import router as stats_router
from backend.app.mqtt_client import mqtt_subscriber
from backend.app.websocket_manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    # Seed default admin user
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default administrator account: admin / admin123")
    finally:
        db.close()

    # Start MQTT background subscriber
    loop = asyncio.get_running_loop()
    mqtt_subscriber.start(loop)

    yield

    # Shutdown
    logger.info("Shutting down backend and stopping MQTT client...")
    mqtt_subscriber.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static uploads directory for hazard snapshots
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(hazards_router, prefix=settings.API_V1_STR)
app.include_router(robots_router, prefix=settings.API_V1_STR)
app.include_router(stats_router, prefix=settings.API_V1_STR)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "mqtt_connected": mqtt_subscriber.is_connected
    }

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; receive ping / text messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket unexpected error: {e}")
        ws_manager.disconnect(websocket)
