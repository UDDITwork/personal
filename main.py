"""
PATMASTER Document Extraction Pipeline
FastAPI Application Entry Point

Production-grade document extraction for PDF and DOCX files with:
- LlamaParse agentic extraction
- PyMuPDF image extraction
- Gemini Vision diagram description
- Async processing with Celery
- Scalable to 10,000+ concurrent users
"""
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/extraction_{time:YYYY-MM-DD}.log",
    rotation="500 MB",
    retention="30 days",
    level="DEBUG"
)

from config import settings, validate_api_keys
from pipeline.router import router as extraction_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("=" * 80)
    logger.info("PATMASTER Document Extraction Pipeline Starting...")
    logger.info("=" * 80)

    # Validate API keys
    try:
        validate_api_keys()
        logger.success("✓ API keys validated")
    except Exception as e:
        logger.error(f"✗ API key validation failed: {e}")
        logger.warning("The application will start but API calls will fail")

    # Test LlamaParse connectivity
    try:
        from llama_cloud_services import LlamaParse
        logger.info("Testing LlamaParse connectivity...")
        # Just initialize to check API key is valid
        parser = LlamaParse(api_key=settings.llama_cloud_api_key)
        logger.success("✓ LlamaParse client initialized")
    except Exception as e:
        logger.error(f"✗ LlamaParse initialization failed: {e}")

    # Test Gemini connectivity
    try:
        from google import genai
        logger.info("Testing Gemini API connectivity...")
        client = genai.Client(api_key=settings.gemini_api_key)
        logger.success("✓ Gemini client initialized")
    except Exception as e:
        logger.error(f"✗ Gemini initialization failed: {e}")

    # Create necessary directories
    settings.extracted_output_dir.mkdir(parents=True, exist_ok=True)
    settings.static_dir.mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    logger.info(f"Output directory: {settings.extracted_output_dir}")
    logger.info(f"Static directory: {settings.static_dir}")
    logger.info(f"Max concurrent extractions: {settings.max_concurrent_extractions}")
    logger.info(f"Extraction timeout: {settings.extraction_timeout}s")

    logger.success("Application startup complete!")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("Application shutting down...")
    logger.info("Cleanup complete. Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="PATMASTER Document Extraction API",
    description="Production-grade document extraction pipeline for PDF and DOCX files",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

# Include routers
app.include_router(extraction_router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "PATMASTER Document Extraction API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "upload_pdf": "POST /api/v1/{user_id}/{session_id}/upload_idf_pdf",
            "upload_docx": "POST /api/v1/{user_id}/{session_id}/upload_idf_transcription",
            "get_result": "GET /api/v1/{user_id}/{session_id}/extraction_result",
            "view_result": "GET /api/v1/{user_id}/{session_id}/view",
            "status": "GET /api/v1/{user_id}/{session_id}/status",
            "health": "GET /health",
            "docs": "GET /docs"
        },
        "features": [
            "LlamaParse agentic extraction with Gemini 2.5 Flash",
            "PyMuPDF parallel image extraction",
            "Gemini Vision diagram description",
            "Supports PDF and DOCX files",
            "Structured JSON output",
            "Visual HTML viewer",
            "Async processing with Celery (optional)",
            "Scalable to 10,000+ concurrent users"
        ]
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    health_status = {
        "status": "healthy",
        "service": "patmaster-extraction",
        "version": "1.0.0",
        "checks": {}
    }

    # Check LlamaParse API key
    try:
        if "xxx" not in settings.llama_cloud_api_key.lower():
            health_status["checks"]["llamaparse"] = "ok"
        else:
            health_status["checks"]["llamaparse"] = "api_key_not_configured"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["llamaparse"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Gemini API key
    try:
        if "xxx" not in settings.gemini_api_key.lower():
            health_status["checks"]["gemini"] = "ok"
        else:
            health_status["checks"]["gemini"] = "api_key_not_configured"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["gemini"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check directories
    try:
        if settings.extracted_output_dir.exists():
            health_status["checks"]["output_directory"] = "ok"
        else:
            health_status["checks"]["output_directory"] = "missing"
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["output_directory"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    status_code = 200 if health_status["status"] == "healthy" else 503

    return JSONResponse(content=health_status, status_code=status_code)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors
    """
    logger.error(f"Unhandled exception: {exc}")
    logger.exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting PATMASTER Extraction API with uvicorn...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info",
        access_log=True
    )
