Hudu Model Context Protocol (MCP) Server to use in ChatGPT Connectors

Hudu is a self-hosted IT documentation platform designed for managed service providers and internal IT teams. This Hudu MCP has two tools, 
- search tool: responsible for returning a list of relevant search results from your MCP server's data source, given a user's query.
- fetch tool: used to retrieve the full contents of a search result document or item

Once connected ChatGPT, will loop through these tools repeatedly to answer a query related to the Hudu database. 

The MCP Server is implemented with Server-Sent Events so the locally hosted server can be reached by ChatGPT remotely (as opposed to a locally hosted server using STDIO which is used by a locally hosted LLM like Claude Desktop).
