import asyncio

from mcp import Client


async def main() -> None:
    async with Client("http://127.0.0.1:8000/mcp") as client:
        outils = await client.list_tools()
        for outil in outils.tools:
            print("OUTIL :", outil.name, "→ schéma :", outil.input_schema)
        resultat = await client.call_tool("lire_logs_erreurs", {"service": "api-virements", "minutes": 30})
        print("RÉSULTAT :", resultat.structured_content)


asyncio.run(main())
