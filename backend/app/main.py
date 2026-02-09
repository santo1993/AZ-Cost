"""
Main FastAPI Application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
import traceback

from .config import get_settings
from .api.routers import resources, savings, export, costs, scans
from .utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="Azure Cost Dashboard API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global Exception Handler for debugging
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    error_msg = "".join(traceback.format_exception(None, exc, exc.__traceback__))
    logger.error(f"Unhandled Exception: {error_msg}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "traceback": error_msg}
    )

# CORS Rules - Allow access from configured origins (localhost, IP addresses, domain names)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info(f"CORS enabled for origins: {settings.cors_origins_list}")

# Middleware for Logger and Correlation ID
@app.middleware("http")
async def log_requests(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    logger.info(f"Start Request: {request.method} {request.url.path} correlation_id={correlation_id}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"End Request: {response.status_code} took {process_time:.3f}s correlation_id={correlation_id}"
        )
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        logger.error(f"Request failed: {e} correlation_id={correlation_id}")
        raise

# Health Check
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Include Routers
app.include_router(resources.router, prefix="/api", tags=["Resources"])
app.include_router(savings.router, prefix="/api", tags=["Savings"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(costs.router, prefix="/api", tags=["Costs"])
app.include_router(scans.router, prefix="/api", tags=["Scans"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.backend_host, port=settings.backend_port)
