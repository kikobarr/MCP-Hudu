import os
import json
import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, quote
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

def _hudu_request(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    base = os.environ["HUDU_BASE_URL"].rstrip("/") + "/"
    url = urljoin(base, path.lstrip("/"))
    headers = {"x-api-key": os.environ["HUDU_API_KEY"]}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def _results_from_assets(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert Hudu assets payload into MCP search results:
    [{ id, title, url }]
    """
    assets = payload.get("assets", []) if isinstance(payload, dict) else []
    results: List[Dict[str, str]] = []
    for a in assets:
        # Prefer slug as a compact/stable id; fall back to numeric id.
        rid = str(a.get("slug") or a.get("id"))
        name = a.get("name") or a.get("title") or a.get("display_name") or "Untitled"
        url = a.get("url")  # Hudu returns canonical asset URL
        # Optionally enrich titles with email/title field if present
        primary_mail = a.get("primary_mail")
        title_field = None
        for f in a.get("fields", []) or []:
            if f.get("label") == "Title" and f.get("value"):
                title_field = f["value"]
                break
        if primary_mail and title_field:
            title = f"{name} — {title_field} ({primary_mail})"
        elif title_field:
            title = f"{name} — {title_field}"
        elif primary_mail:
            title = f"{name} ({primary_mail})"
        else:
            title = name
        # Only include results that have a URL
        if rid and url:
            results.append({"id": rid, "title": title, "url": url})
    return results

def _text_content(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrap JSON payload as a single MCP content item of type 'text' whose text is a JSON-encoded string.
    """
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False),
            }
        ]
    }

# ---------- MCP tools ----------

@mcp.tool
def search(query: str, page: int = 1, page_size: Optional[int] = None) -> Dict[str, Any]:
    """
    MCP 'search' tool: Given a query string, return one content item:
      type: "text"
      text: JSON-encoded string: {"results":[{"id","title","url"}, ...]}
    """
    if not query or not query.strip():
        # Return an empty results array in the required content format
        return _text_content({"results": []})

    ps = page_size or int(os.getenv("HUDU_DEFAULT_PAGE_SIZE", "50"))
    try:
        data = _hudu_request(
            "/api/v1/assets",
            {"page": page, "page_size": ps, "search": query},
        )
        results = _results_from_assets(data)
        return _text_content({"results": results})
    except requests.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        return _text_content({"results": [], "error": {"status": status, "message": "Hudu API request failed"}})
    except Exception as e:
        return _text_content({"results": [], "error": {"message": str(e)}})

@mcp.tool
def fetch(url: str) -> Dict[str, Any]:
    """
    MCP 'fetch' tool: Return a single content item pointing at the given URL.
    Hosts commonly accept 'resource' content items and will fetch/process them.
    """
    if not url or not url.strip():
        return _text_content({"error": {"message": "url must be non-empty"}})

    # Provide a resource reference so the host can retrieve the content.
    # (Keeping this minimal and spec-friendly; no server-side scraping required.)
    return {
        "content": [
            {
                "type": "resource",
                "uri": url,
                # Optional hint; many hosts sniff type anyway.
                "mimeType": "text/html"
            }
        ]
    }

# ---------- Health check & ASGI ----------

@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

app = mcp.http_app()

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))