"""The MCP server class, and the error a tool raises to tell its caller why
(any other exception reaches the caller only as "Error executing tool")."""
try:                                   # mcp 2.x
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer
    from mcp.server.fastmcp.exceptions import ToolError

__all__ = ["MCPServer", "ToolError"]
