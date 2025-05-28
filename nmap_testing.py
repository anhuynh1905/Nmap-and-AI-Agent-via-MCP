import nmap3
import json
import asyncio
from mcp_client import MCPClient

async def main():
    #print("Running Nmap scan...\n")
    #await nmap_run()
    
    client = MCPClient()
    try:
        await client.connect_to_server()
        response = await client.process_query("Perform a fast scan on the target host")
        print("\n" + response)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())