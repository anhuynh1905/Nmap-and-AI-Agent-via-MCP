from fastmcp import FastMCP
import nmap3
import asyncio
import json

nmap = nmap3.Nmap()
app = FastMCP(name="MyNmapMCPServer")

@app.tool(
    name="fast_scan",
    description="Perform a fast scan on the target host",
)
async def fast_scan(target: str) -> str:
    scan_results = nmap.scan_top_ports(target)
    return json.dumps(scan_results)

@app.tool(
    name="os_detection",
    description="Detect the operating system of the target host",
)
async def os_detection(target: str) -> str:
    scan_results = nmap.os_detection(target)
    return json.dumps(scan_results)

@app.tool(
    name="service_version",
    description="Detect the service version of the target host",
)
async def service_version(target: str) -> str:
    scan_results = nmap.service_version(target)
    return json.dumps(scan_results)

@app.tool(
    name="full_scan",
    description="Perform a full scan on the target host",
)
async def full_scan(target: str) -> str:
    scan_results = nmap.nmap_version_detection(target)
    result = json.dumps(scan_results)
    print(result)
    return result

@app.tool(
    name="ping_scan",
    description="Perform a ping scan on the target host",
)
async def ping_scan(target: str) -> str:
    scan_results = nmap.ping_scan(target)
    return json.dumps(scan_results)

if __name__ == "__main__":
    app.run(
        transport="streamable-http",
        host="127.0.0.1",
        path="/nmap_mcp_server"
    )
