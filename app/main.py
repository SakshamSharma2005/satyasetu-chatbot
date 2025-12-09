from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import auth, chat, universities, knowledge
import logging

# Configure logging (updated for deployment)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RAG-based bilingual chatbot for educational document forgery detection",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Satyasetu Chatbot API...")
    
    # Connect to MongoDB
    from app.core.mongodb import connect_to_mongodb
    await connect_to_mongodb()
    logger.info("MongoDB connected")
    
    # Ensure data directory exists for SQLite (legacy)
    from app.core.init_db import ensure_data_directory
    ensure_data_directory()
    logger.info("Data directories initialized")
    
    # Initialize SQLite database tables (legacy)
    init_db()
    logger.info("Database initialized")
    logger.info(f"API documentation available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Satyasetu Chatbot API...")
    from app.core.mongodb import close_mongodb_connection
    await close_mongodb_connection()
    logger.info("MongoDB connection closed")


# Health check endpoint
@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "message": "Welcome to Satyasetu Chatbot API"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(universities.router)
app.include_router(knowledge.router)

# MongoDB routers
from app.api import auth_mongo, chat_mongo, student
app.include_router(auth_mongo.router)
app.include_router(chat_mongo.router)
app.include_router(student.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
