import nmap3
import json
nmap = nmap3.Nmap()

results = nmap.nmap_version_detection("vulnweb.com", args="--script vulners -A -T4")
result = json.dumps(results)
print(results)