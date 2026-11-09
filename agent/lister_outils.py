from connexions_mcp import client_github, client_ops, client_slack

for nom, fabrique in [("mcp-ops-atlas", client_ops), ("github", client_github), ("slack", client_slack)]:
    try:
        client = fabrique()
        with client:
            outils = client.list_tools_sync()
            print(f"\n{nom} : {len(outils)} outils")
            for outil in outils:
                print("  -", outil.tool_name)
    except Exception as exc:
        print(f"\n{nom} : INJOIGNABLE ({type(exc).__name__}: {exc})")
