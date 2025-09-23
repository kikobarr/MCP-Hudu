from fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP(name="Calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

if __name__ == "__main__":
    print("Running server with Streamable HTTP transport")
    mcp.run(transport="streamable-http", host="localhost", port=3001, path="/mcp")

    # run(self, transport: Transport | None = None, show_banner: bool = True, **transport_kwargs: Any) -> None

