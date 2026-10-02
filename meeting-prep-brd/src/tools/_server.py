"""The MCP server class, under either SDK major version."""
try:                                   # mcp 2.x
    from mcp.server.mcpserver import MCPServer
except ImportError:                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

__all__ = ["MCPServer"]
