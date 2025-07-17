from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
import os
from decouple import config

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routers import cards, decks, users, auth
from app.api import simple_chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check required environment variables
    required_env_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "CLAUDE_API_KEY"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not config(var, default=""):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    print("✅ All required environment variables are set")
    print("🚀 Pokemon Deck Builder API starting up...")
    
    # Test database connection
    try:
        from app.database.supabase_client import get_supabase_client
        client = await get_supabase_client()
        print("✅ Supabase connection established")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    # Test Claude API
    try:
        from app.utils.claude_client import get_claude_client
        claude_client = await get_claude_client()
        print("✅ Claude API client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Claude API: {e}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    print("🛑 Pokemon Deck Builder API shutting down...")


app = FastAPI(
    title="Pokemon Deck Builder API",
    description="A REST API for building and managing Pokemon card decks with conversational AI",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])
app.include_router(decks.router, prefix="/decks", tags=["decks"])
app.include_router(simple_chat.router, prefix="/api", tags=["simple-chat"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Pokemon Deck Builder API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "pokemon_chat": "/decks/pokemon-chat",
            "simple_chat": "/api/simple-chat",
            "card_search": "/cards/search",
            "card_filters": "/cards/filters"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with service status"""
    try:
        # Check database connection
        from app.database.supabase_client import get_supabase_client
        await get_supabase_client()
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "services": {
            "database": db_status,
            "api": "healthy"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)