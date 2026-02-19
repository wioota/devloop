"""FastAPI HTTP server for agent marketplace registry.

Provides REST API endpoints for searching, retrieving, and managing
agents in the marketplace.
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Query, Body, Request  # type: ignore[import-not-found]
    from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore[import-not-found]

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .api import RegistryAPI
from .registry_client import create_registry_client

logger = logging.getLogger(__name__)


class RegistryHTTPServer:
    """FastAPI HTTP server for marketplace registry."""

    def __init__(
        self,
        registry_dir: Path,
        remote_urls: Optional[List[str]] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        cors_origins: Optional[List[str]] = None,
    ):
        """Initialize HTTP server."""
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI is required for HTTP server. "
                "Install with: pip install fastapi uvicorn"
            )

        self.host = host
        self.port = port
        self.registry_dir = registry_dir

        # Create registry client
        self.client = create_registry_client(registry_dir, remote_urls)
        self.api = RegistryAPI(self.client)

        # Create FastAPI app
        self.app = FastAPI(
            title="Agent Marketplace Registry API",
            description="REST API for devloop agent marketplace",
            version="1.0.0",
        )

        # Add CORS if origins specified
        if cors_origins:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add custom exception handler for HTTPException
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(
            request: Request, exc: HTTPException
        ) -> JSONResponse:
            """Handle HTTPException with consistent response format."""
            return JSONResponse(
                status_code=exc.status_code,
                content={"success": False, "error": exc.detail},
            )

        # Setup routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup API routes."""

        @self.app.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            response = self.api.health_check()
            if not response.success:
                raise HTTPException(status_code=503, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/agents/search")
        async def search_agents(
            q: str = Query("", description="Search query"),
            categories: List[str] = Query(None, description="Categories to filter"),
            min_rating: float = Query(
                0.0, ge=0.0, le=5.0, description="Minimum rating"
            ),
            search_remote: bool = Query(True, description="Search remote registries"),
            limit: int = Query(50, ge=1, le=200, description="Max results"),
            offset: int = Query(0, ge=0, description="Result offset"),
        ) -> Dict[str, Any]:
            """Search for agents."""
            response = self.api.search_agents(
                query=q,
                categories=categories,
                min_rating=min_rating,
                search_remote=search_remote,
                max_results=limit,
                offset=offset,
            )
            if not response.success:
                raise HTTPException(status_code=400, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/agents/popular")
        async def get_popular_agents(
            limit: int = Query(10, ge=1, le=100, description="Max results"),
        ) -> Dict[str, Any]:
            """Get popular agents."""
            response = self.api.get_popular_agents(limit=limit)
            if not response.success:
                raise HTTPException(status_code=500, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/agents/trusted")
        async def get_trusted_agents() -> Dict[str, Any]:
            """Get trusted agents."""
            response = self.api.get_trusted_agents()
            if not response.success:
                raise HTTPException(status_code=500, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/agents/{agent_name}")
        async def get_agent(
            agent_name: str,
            version: Optional[str] = Query(None, description="Specific version"),
            search_remote: bool = Query(True, description="Search remote registries"),
        ) -> Dict[str, Any]:
            """Get a specific agent."""
            response = self.api.get_agent(
                name=agent_name,
                version=version,
                search_remote=search_remote,
            )
            if not response.success:
                raise HTTPException(status_code=404, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/agents")
        async def list_agents(
            category: Optional[str] = Query(None, description="Filter by category"),
            include_deprecated: bool = Query(
                False, description="Include deprecated agents"
            ),
            sort: str = Query(
                "rating", pattern="^(rating|downloads|name)$", description="Sort field"
            ),
            limit: int = Query(100, ge=1, le=500, description="Max results"),
            offset: int = Query(0, ge=0, description="Result offset"),
        ) -> Dict[str, Any]:
            """List agents."""
            response = self.api.list_agents(
                category=category,
                include_deprecated=include_deprecated,
                sort_by=sort,
                max_results=limit,
                offset=offset,
            )
            if not response.success:
                raise HTTPException(status_code=400, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/categories")
        async def get_categories() -> Dict[str, Any]:
            """Get available categories."""
            response = self.api.get_categories()
            if not response.success:
                raise HTTPException(status_code=500, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/categories/{category_name}")
        async def get_agents_by_category(
            category_name: str,
            search_remote: bool = Query(True, description="Search remote registries"),
            limit: int = Query(50, ge=1, le=200, description="Max results"),
        ) -> Dict[str, Any]:
            """Get agents in a category."""
            response = self.api.get_agents_by_category(
                category=category_name,
                search_remote=search_remote,
                max_results=limit,
            )
            if not response.success:
                raise HTTPException(status_code=400, detail=response.error)
            return response.to_dict()

        @self.app.post("/api/v1/agents")
        async def register_agent(
            metadata: Dict[str, Any] = Body(..., description="Agent metadata"),
        ) -> Dict[str, Any]:
            """Register a new agent."""
            response = self.api.register_agent(metadata)
            if not response.success:
                raise HTTPException(status_code=400, detail=response.error)
            return response.to_dict()

        @self.app.post("/api/v1/agents/{agent_name}/rate")
        async def rate_agent(
            agent_name: str,
            rating: float = Body(..., ge=1.0, le=5.0, description="Rating (1-5)"),
        ) -> Dict[str, Any]:
            """Rate an agent."""
            response = self.api.rate_agent(agent_name, rating)
            if not response.success:
                raise HTTPException(status_code=400, detail=response.error)
            return response.to_dict()

        @self.app.post("/api/v1/agents/{agent_name}/download")
        async def download_agent(agent_name: str) -> Dict[str, Any]:
            """Record a download for an agent."""
            response = self.api.download_agent(agent_name)
            if not response.success:
                raise HTTPException(status_code=404, detail=response.error)
            return response.to_dict()

        @self.app.post("/api/v1/agents/{agent_name}/deprecate")
        async def deprecate_agent(
            agent_name: str,
            message: str = Body(..., description="Deprecation message"),
        ) -> Dict[str, Any]:
            """Deprecate an agent."""
            response = self.api.deprecate_agent(agent_name, message)
            if not response.success:
                raise HTTPException(status_code=404, detail=response.error)
            return response.to_dict()

        @self.app.delete("/api/v1/agents/{agent_name}")
        async def remove_agent(agent_name: str) -> Dict[str, Any]:
            """Remove an agent from registry."""
            response = self.api.remove_agent(agent_name)
            if not response.success:
                raise HTTPException(status_code=404, detail=response.error)
            return response.to_dict()

        @self.app.get("/api/v1/stats")
        async def get_stats() -> Dict[str, Any]:
            """Get registry statistics."""
            response = self.api.get_stats()
            if not response.success:
                raise HTTPException(status_code=500, detail=response.error)
            return response.to_dict()

    def run(self, reload: bool = False) -> None:
        """Run the server."""
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "uvicorn is required to run the server. "
                "Install with: pip install uvicorn"
            )

        logger.info(f"Starting registry API server on {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            reload=reload,
            log_level="info",
        )


def create_http_server(
    registry_dir: Path,
    remote_urls: Optional[List[str]] = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    cors_origins: Optional[List[str]] = None,
) -> RegistryHTTPServer:
    """Create and configure HTTP server."""
    return RegistryHTTPServer(
        registry_dir=registry_dir,
        remote_urls=remote_urls,
        host=host,
        port=port,
        cors_origins=cors_origins,
    )
