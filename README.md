# Hudu MCP Connector (Prototype)

Prototype MCP Connector for Hudu that was built for ChatGPT Connectors (now called Apps). Hudu is an IT documentation platform used by Cal Poly Humboldt University's IT Services department.

The Hudu MCP Server is implemented with Server-Sent Events so the locally hosted server can be reached by ChatGPT remotely (as opposed to a locally hosted server using STDIO which is used by a locally hosted LLM like Claude Desktop).

This Hudu MCP has two tools:
- search tool: responsible for returning a list of relevant search results from your MCP server's data source, given a user's query.
- fetch tool: used to retrieve the full contents of a search result document or item

## Quick Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the MCP server and open MCP Inspector

Make sure the virtual environment is activated and you are in the folder that has the server Python file.

```bash
python hudu_server.py
```

```bash
uv run python hudu_server.py
```

```bash
npx @modelcontextprotocol/inspector python hudu_server.py
```

### 3. Expose the server with ngrok

Create an account with ngrok then get your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken

```bash
ngrok config add-authtoken $YOUR_AUTHTOKEN
ngrok http 8000 --host-header=rewrite
```

Copy the HTTPS URL shown by ngrok next to “Forwarding”, for example:

```
https://4df08bcff9f0.ngrok-free.app
```

Add `/mcp` to the end:

```
https://4df08bcff9f0.ngrok-free.app/mcp
```

### 4. Add it to ChatGPT as a Custom Connector

In ChatGPT: Settings → Connectors → Custom connectors → Add 

Paste the tunneled MCP URL (must include /mcp)

Enable the connector and use it in a chat.

## Lessons Learned

### Tiny Tips

ChatGPT Connectors only allow two tools: search and fetch. 

There are several transport types for MCP. 

Use MCP Inspector to inspect the output. 

### Using FastMCP via FastMCP or MCP 

FastMCP is a framework that makes it much easier to create MCP servers and MCP tools. There are two ways to access FastMCP, through the official MCP Python SDK or through the FastMCP library directly. 

`from fastmcp import FastMCP`

vs 

`from mcp.server.fastmcp import FastMCP`

Both use FastMCP, but mcp is a more conservative organization so they use a later version of FastMCP which doesn't have all the commands available. 

For example, at the time I was working on this project, the mcp.run() command took different parameters and the command to start MCP Inspector was be different. 


### Double Wrapping Tool Output
Issue I spent the most time on: My tool output was being double wrapped. 

For both search and fetch, the MCP tool must return:
- A content array
- With exactly one item
- Where:
    - type is "text"
    - text is a string
    - That string contains valid JSON

Example: 
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"results\": [...]}"
    }
  ]
}
```
When I inspected the tool output in MCP Inspector, it matched this output. However, the FastMCP framework expected a raw Python payload and wrapped it for me so it was getting double wrapped and the OpenAI MCP host was seeing a misshapen payload. 

See hudu_server.py for the code that ends up double wrapping (buggy):

```python
    payload = {"results": results}
    
    search_tool_response = {
        "content": [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
        ]
    }

    return search_tool_response
```

versus the corrected version in hudu_v3_server.py which lets the framework do the wrapping: 

```python

results: List[Dict[str, Any]] = []

if item["id"] and item["title"] and item["url"]:
            results.append(item)

return {"results": results}

```

## Troubleshooting

Double check in server.py:
- run() command is set to Streamable HTTP 
- port is the same as in the ngrok command

