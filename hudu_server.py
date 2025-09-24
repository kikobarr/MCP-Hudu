#!/usr/bin/env python3
"""
Hudu MCP Server (search + fetch) for ChatGPT Connectors

- search(query: str): calls Hudu /api/v1/assets?search=...&page=&page_size=...
- fetch(id: str): returns a single asset by id via /api/v1/assets?id=...
- Returns tiny search results (id, title, url + snippet/metadata) and full blob on fetch.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# ------------------
# Config
# ------------------
HUDU_BASE_URL = os.getenv("HUDU_BASE_URL", "").rstrip("/")
HUDU_API_KEY = os.getenv("HUDU_API_KEY", "")
HUDU_DEFAULT_PAGE_SIZE = int(os.getenv("HUDU_DEFAULT_PAGE_SIZE", "15")) 
HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "15"))

if not HUDU_BASE_URL:
    raise RuntimeError("Set HUDU_BASE_URL environment variable")
if not HUDU_API_KEY:
    raise RuntimeError("Set HUDU_API_KEY environment variable")

# ------------------
# Logging
# ------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("hudu-mcp")
log.setLevel(logging.DEBUG)

# ------------------
# MCP Server
# ------------------
INSTRUCTIONS = (
    "This MCP server exposes Hudu assets for ChatGPT Connectors. "
    "Use `search` to list candidate assets (tiny results with snippets), "
    "then `fetch` to retrieve the full document only for selected ids."
)
mcp = FastMCP(name="Hudu MCP", instructions=INSTRUCTIONS)


# ------------------
# Search Tool
# ------------------

@mcp.tool()
async def search(query: str) -> Dict[str, Any]:
    """
    Search based on query.
    MUST return exactly one content item containing a JSON-encoded string:
    {
      "content": [
        {
          "type": "text",
          "text": "{\"results\":[{...},{...}]}"
        }
      ]
    }
    """
    # VERY important. ChatGPT will query with a string and that needs to be removed for the API call
    print(f"[DEBUG] Before cleanup: {query}")
    query = query.replace('"', '').replace("'", '')
    print(f"[DEBUG] After cleanup: {query}")

    page = 1
    page_size = int(HUDU_DEFAULT_PAGE_SIZE)

    # Build endpoint
    API_ROOT = HUDU_BASE_URL.rstrip("/") + "/api/v1"
    endpoint = f"{API_ROOT}/assets"
    headers = {"x-api-key": HUDU_API_KEY}
    params = {"search": query, "page": page, "page_size": page_size}

    async with httpx.AsyncClient() as client:
        r = await client.get(endpoint, params=params, headers=headers, timeout=HTTP_TIMEOUT_S)

    data = r.json()
    # Hudu can return either {"assets":[...]} or {"data":[...]} depending on endpoint/version
    assets = data.get("assets") or data.get("data") or []
    if not isinstance(assets, list):
        log.debug("Unexpected payload: %s", data)
        assets = []

    results: List[Dict[str, Any]] = []

    for a in assets:
        rid = str(a.get("id") or "")
        title = (a.get("name") or "").strip() 
        url = (a.get("url") or "").strip()

        # snippet: short, readable preview
        snippet_parts = []
        if a.get("asset_type"):
            snippet_parts.append(str(a["asset_type"]))
        if a.get("company_name"):
            snippet_parts.append(str(a["company_name"]))
        if a.get("primary_mail"):
            snippet_parts.append(str(a["primary_mail"]))
        snippet = " • ".join([s for s in snippet_parts if s])[:220]
        if len(snippet) == 220:
            snippet = snippet[:-1] + "…"

        # metadata: include small, useful fields depending on the asset type
        # meta: Dict[str, Any] = {}
        # for k in ("asset_type", "primary_mail", "object_type", "created_at", "updated_at"):
        #     v = a.get(k)
        #     if v is not None and v != "":
        #         meta[k] = v

        item = {
            "id": rid,
            "title": title,
            "url": url,
            "snippet": snippet,
        }
        # if meta:
        #     item["metadata"] = meta  # only include when non-empty

        if item["id"] and item["title"] and item["url"]:
            results.append(item)

    log.info("search(%r) -> %d results (page=%s size=%s)", query, len(results), page, page_size)

    # EXACT output shape: one content item, text = JSON string with {"results":[...]}
    payload = {"results": results}
    
    return {
        "content": [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
        ]
    }


# ------------------
# Fetch Tool
# ------------------

@mcp.tool()
async def fetch(id: str) -> Dict[str, Any]:
    """
    Retrieve the full asset by ID (single item), suitable for detailed reasoning/citation.
    Must return: id, title, text (full JSON as text), url, metadata.
    """
    sid = (id or "").strip()
    if not sid:
        raise ValueError("id is required")
    
    # API call should look like: https://calpolyhumboldt.huducloud.com/api/v1/assets?search=Warren
    # Build endpoint
    API_ROOT = HUDU_BASE_URL if "/api/" in HUDU_BASE_URL else HUDU_BASE_URL.rstrip("/") + "/api/v1"
    endpoint = f"{API_ROOT}/assets"
    headers = {"x-api-key": HUDU_API_KEY}
    params = {"id": sid}

    log.info("Endpoint check: %s", f"{HUDU_BASE_URL.rstrip('/')}/assets")

    async with httpx.AsyncClient() as client:
        r = await client.get(endpoint, params=params, headers=headers, timeout=HTTP_TIMEOUT_S)

    if r.status_code != 200:
        log.warning("Hudu /assets?id=%r -> %s %s", sid, r.status_code, r.text[:300])
        raise RuntimeError(f"Hudu API /assets failed ({r.status_code})")

    data = r.json()
    assets = data.get("assets") or data.get("data") or []
    if not assets:
        raise ValueError(f"Asset id '{sid}' not found")

    a = assets[0]
    rid = str(a.get("id"))
    title = a.get("name") or f"{(a.get('asset_type') or 'Asset')} {rid}"

    url = a.get("url") or ""
    if not url:
        slug = a.get("slug")
        if slug:
            base = HUDU_BASE_URL.split("/api/")[0].rstrip("/")
            url = f"{base}/a/{slug}"

    metadata: Dict[str, Any] = {}
    if a.get("asset_type"): metadata["asset_type"] = a.get("asset_type")
    if a.get("company_name"): metadata["company_name"] = a.get("company_name")
    if a.get("primary_mail"): metadata["primary_mail"] = a.get("primary_mail")
    if a.get("primary_model"): metadata["primary_model"] = a.get("primary_model")

    # The 'text' field of the *document object* should itself be a JSON string of the full asset
    doc = {
        "id": rid,
        "title": title,
        "text": json.dumps(a, ensure_ascii=False, indent=2),
        "url": url,
        "metadata": metadata or None,
    }

    # --- Build tool response (unchanged) ---
    tool_response = {
        "content": [
            {
                "type": "text",
                "text": json.dumps(doc, ensure_ascii=False)  # doc = {id,title,text,url,metadata}
            }
        ]
    }

        # --- Dump exactly what the Connector will get ---
    try:
        item = tool_response["content"][0]
        raw_text = item["text"]  # JSON-encoded string of the *document object*

        # Choose a dump dir you can easily find; override with env if needed.
        dump_dir = os.getenv("FETCH_DUMP_DIR", os.path.abspath("./_fetch_dumps"))
        os.makedirs(dump_dir, exist_ok=True)

        raw_path = os.path.join(dump_dir, f"fetch_{rid}_tool_response.txt")
        pretty_path = os.path.join(dump_dir, f"fetch_{rid}_document.json")

        # 1) The exact string the tool returns (spec-critical)
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_text)

        # 2) Parsed inner document (for eyeballing)
        inner_doc = json.loads(raw_text)
        with open(pretty_path, "w", encoding="utf-8") as f:
            json.dump(inner_doc, f, ensure_ascii=False, indent=2)

        # Read-back sanity checks so you can see they exist
        with open(raw_path, "r", encoding="utf-8") as f:
            sz = len(f.read())
        log.info("fetch(%s) wrote: %s (%d bytes), %s", rid, raw_path, sz, pretty_path)

    except Exception as e:
        log.exception("fetch(%s) dump failed: %s", rid, e)

    return tool_response


# ------------------
# Entrypoint
# ------------------
def main() -> None:
    log.info("Starting Hudu MCP (base=%s)", HUDU_BASE_URL)
    # NOTE: MCP/Connectors expect your tools to follow the shapes in the docs:
    # - search returns { "results": [{ id, title, url, ...}] }
    # - fetch returns { id, title, text, url, metadata }:contentReference[oaicite:5]{index=5}
    # Hudu /assets supports full-text `search`, plus `page`/`page_size` and `id` filter:contentReference[oaicite:6]{index=6}
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), path="/mcp")

if __name__ == "__main__":
    try:
        asyncio.run(asyncio.to_thread(main))
    except RuntimeError:
        # in some runtimes, nested event loops aren't allowed—fallback
        main()
