# Shared State Module
# This module holds global state that is shared across all routers

from pathlib import Path

# Project root for path resolution in routers
PROJECT_ROOT = Path(__file__).parent.parent

# === Lazy-loaded dependencies ===
# These will be initialized when first accessed or during api.py lifespan

# Global state - shared across routers
active_loops = {}

# MCP instance - will be started in api.py lifespan
_multi_mcp = None

def get_multi_mcp():
    """Get the MultiMCP instance, creating it if needed."""
    global _multi_mcp
    if _multi_mcp is None:
        from mcp_servers.multi_mcp import MultiMCP
        _multi_mcp = MultiMCP()
    return _multi_mcp

# Global settings state
settings = {}
