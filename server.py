import os, requests
from typing import Any, Dict, Optional, List
from urllib.parse import urljoin
from fastmcp import FastMCP
from starlette.responses import PlainTextResponse
from starlette.requests import Request

from dotenv import load_dotenv
load_dotenv()

# API Tester
# api_key = os.getenv("HUDU_API_KEY")

# # url = "https://calpolyhumboldt.huducloud.com/api/v1/companies"
# # url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=ACAC-S33381"s
# # url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?page=1&page_size=10"
# # url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?name=Emily R Oparowski"
# url = "https://calpolyhumboldt.huducloud.com/api/v1/assets?page=1&page_size=100&search=Emily"

# headers = {"x-api-key": api_key}
# response = requests.get(url, headers=headers)
# print(response.status_code)
# print(json.dumps(response.json(), indent=4))


mcp = FastMCP("Hudu Search MCP")

def _hudu_request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    base = os.environ["HUDU_BASE_URL"].rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    headers = {"x-api-key": os.environ["HUDU_API_KEY"]}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def _simplify(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload if isinstance(payload, list) else payload.get("data") or payload.get("assets") or []
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append({
            "id": it.get("id"),
            "name": it.get("name") or it.get("title") or it.get("display_name"),
            "type": it.get("type") or it.get("asset_type"),
            "company_id": it.get("company_id"),
            "slug": it.get("slug"),
            "updated_at": it.get("updated_at") or it.get("updatedAt"),
        })
    return {"count": len(out), "items": out, "raw": payload}

@mcp.tool
def search_hudu_assets(query: str, page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
    """Search Hudu assets by keyword (maps to /api/v1/assets?search=...)."""
    if not query or not query.strip():
        raise ValueError("query must be non-empty")
    ps = page_size or int(os.getenv("HUDU_DEFAULT_PAGE_SIZE", "100"))
    payload = _hudu_request("/api/v1/assets", {"page": page, "page_size": ps, "search": query})
    return _simplify(payload)

# Health check (Fly will hit this)
@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# ASGI app for uvicorn / Fly
app = mcp.http_app()

if __name__ == "__main__":
    # Local dev run on Streamable HTTP (endpoint will be http://localhost:8000/mcp/)
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
