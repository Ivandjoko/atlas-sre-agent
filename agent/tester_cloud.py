import os

from mcp.client.sse import sse_client
from strands.tools.mcp import MCPClient


def entete(jeton: str, **extra) -> dict:
    return {"Authorization": f"Bearer {jeton}", **extra}


clients = {
    "mcp-ops-atlas": MCPClient(url=os.environ["MCP_OPS_URL"], headers=entete(os.environ["MCP_OPS_TOKEN"])),
    "github": MCPClient(url="https://api.githubcopilot.com/mcp/",
                        headers=entete(os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"], **{"X-MCP-Toolsets": "issues"})),
    # Le serveur Slack n'expose que l'ancien transport SSE, sur /sse
    "slack": MCPClient(lambda: sse_client(os.environ["SLACK_MCP_URL"], headers=entete(os.environ["SLACK_MCP_API_KEY"]))),
}
for nom, client in clients.items():
    try:
        with client:
            print(nom, ":", [o.tool_name for o in client.list_tools_sync()])
    except Exception as exc:
        print(nom, ": INJOIGNABLE", type(exc).__name__, str(exc)[:200])
