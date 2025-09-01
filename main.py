# from fastmcp import FastMCP

# mcp = FastMCP("hudu-server")

# # define tools, including Deep Research-style `search` and `fetch`
# mcp.run(transport="streamable-http")  # serves SSE endpoint

import os
from dotenv import load_dotenv
import requests
import json 

# Load variables from .env
load_dotenv()

# Read API key from environment
api_key = os.getenv("HUDU_API_KEY")

url = "https://calpolyhumboldt.huducloud.com/api/v1/companies"
headers = {"x-api-key": api_key}

response = requests.get(url, headers=headers)

print(response.status_code)
print(response.json()) 

print(json.dumps(response.json(), indent=4))