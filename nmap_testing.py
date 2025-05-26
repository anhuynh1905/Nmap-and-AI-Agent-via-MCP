import nmap3
import json
import asyncio
from fastmcp import Client

async def nmap_run():
    nmap = nmap3.Nmap()
    results = nmap.nmap_version_detection("baomoi.com", args="--script vulners -A -T4")
    result = json.dumps(results)
    print(results)

async def mcpclient():
    client = Client("http://127.0.0.1:8000/nmap_mcp_server")
    async with client:
        result = await client.call_tool("full_scan", {"target": "baomoi.com"})
        # Handle TextContent object by extracting its text content
        if hasattr(result, 'content') and result.content:
            return result.content[0].text if result.content else str(result)
        return str(result)

async def main():
    #print("Running Nmap scan...\n")
    #await nmap_run()
    
    print("Running MCP client...\n")
    result = await mcpclient()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())