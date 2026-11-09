"""Connexions MCP de Sentinelle : mcp-ops-atlas (HTTP), GitHub et Slack (conteneurs en stdio)."""
import os

from mcp import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

IMAGE_GITHUB = "ghcr.io/github/github-mcp-server:latest"
IMAGE_SLACK = "ghcr.io/korotovsky/slack-mcp-server:latest"


def _secret(nom: str) -> str:
    """Lit un secret dans l'environnement, avec un message clair s'il manque."""
    valeur = os.environ.get(nom)
    if not valeur:
        raise RuntimeError(f"Variable {nom} absente : lance 'set -a; source ~/.sentinelle.env; set +a'")
    return valeur


def _env(**variables: str) -> dict:
    """Environnement minimal du sous-processus : PATH et HOME, plus les seules variables dont il a besoin."""
    return {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], **variables}


def client_ops() -> MCPClient:
    """Ton serveur mcp-ops-atlas, joint en HTTP (il doit déjà tourner)."""
    url = os.getenv("MCP_OPS_URL", "http://127.0.0.1:8000/mcp")
    return MCPClient(lambda: streamable_http_client(url))


def client_github() -> MCPClient:
    """Serveur MCP officiel de GitHub, lancé en conteneur, limité aux outils d'issues."""
    params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm",
              "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
              "-e", "GITHUB_TOOLSETS",
              IMAGE_GITHUB],
        env=_env(GITHUB_PERSONAL_ACCESS_TOKEN=_secret("GITHUB_PERSONAL_ACCESS_TOKEN"),
                 GITHUB_TOOLSETS="issues"),
    )
    return MCPClient(lambda: stdio_client(params))


def client_slack() -> MCPClient:
    """Serveur MCP Slack, lancé en conteneur : un seul outil, publication limitée à #incidents."""
    params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm",
              "-e", "SLACK_MCP_XOXB_TOKEN",
              "-e", "SLACK_MCP_ADD_MESSAGE_TOOL",
              "-e", "SLACK_MCP_ENABLED_TOOLS",
              IMAGE_SLACK, "--transport", "stdio"],
        env=_env(SLACK_MCP_XOXB_TOKEN=_secret("SLACK_BOT_TOKEN"),
                 # Barrière 1 : publication autorisée UNIQUEMENT dans le canal #incidents
                 SLACK_MCP_ADD_MESSAGE_TOOL=_secret("SLACK_INCIDENTS_CHANNEL_ID"),
                 # Barrière 2 : seul cet outil est exposé à l'agent
                 SLACK_MCP_ENABLED_TOOLS="conversations_add_message"),
    )
    return MCPClient(lambda: stdio_client(params))
