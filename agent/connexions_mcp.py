"""Connexions MCP de Sentinelle : mcp-ops-atlas (HTTP), GitHub et Slack (conteneurs en stdio)."""
import os

from mcp import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

IMAGE_GITHUB = "ghcr.io/github/github-mcp-server:latest"
IMAGE_SLACK = "ghcr.io/korotovsky/slack-mcp-server:latest"


def _secret(nom: str) -> str:
    valeur = os.environ.get(nom)
    if not valeur:
        raise RuntimeError(f"Variable {nom} absente : lance 'set -a; source ~/.sentinelle.env; set +a'")
    return valeur


def _env(**secrets: str) -> dict:
    """Environnement minimal du sous-processus : PATH et HOME, plus les seuls secrets dont il a besoin."""
    return {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], **secrets}


def client_ops() -> MCPClient:
    url = os.getenv("MCP_OPS_URL", "http://127.0.0.1:8000/mcp")
    return MCPClient(lambda: streamable_http_client(url))


def client_github() -> MCPClient:
    params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm",
              "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "-e", "GITHUB_TOOLSETS",
              IMAGE_GITHUB],
        env=_env(GITHUB_PERSONAL_ACCESS_TOKEN=_secret("GITHUB_PERSONAL_ACCESS_TOKEN"),
                 GITHUB_TOOLSETS="issues"),
    )
    return MCPClient(lambda: stdio_client(params))


def client_slack() -> MCPClient:
    params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm",
              "-e", "SLACK_MCP_XOXB_TOKEN", "-e", "SLACK_MCP_ADD_MESSAGE_TOOL",
              IMAGE_SLACK, "--transport", "stdio"],
        env=_env(SLACK_MCP_XOXB_TOKEN=_secret("SLACK_BOT_TOKEN"),
                 # publication autorisée UNIQUEMENT dans le canal #incidents
                 SLACK_MCP_ADD_MESSAGE_TOOL=_secret("SLACK_INCIDENTS_CHANNEL_ID")),
    )
    return MCPClient(lambda: stdio_client(params))
