"""
FastAPI main application.

This is the entry point for the Routilux monitoring and flow builder API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routilux.api.routes import breakpoints, debug, flows, jobs, monitor, websocket

app = FastAPI(
    title="Routilux API",
    description="Monitoring, debugging, and flow builder API for Routilux",
    version="0.10.0",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(flows.router, prefix="/api", tags=["flows"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(breakpoints.router, prefix="/api", tags=["breakpoints"])
app.include_router(debug.router, prefix="/api", tags=["debug"])
app.include_router(monitor.router, prefix="/api", tags=["monitor"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Routilux API",
        "version": "0.10.0",
        "description": "Monitoring, debugging, and flow builder API",
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import os

    import uvicorn

    # Default configuration
    # Disable reload in test environment
    reload = os.getenv("ROUTILUX_API_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "routilux.api.main:app",
        host="0.0.0.0",
        port=20555,
        reload=reload,  # Enable auto-reload in development
    )
