from connexions_mcp import client_slack

slack = client_slack()
with slack:
    resultat = slack.call_tool_sync(
        tool_use_id="test-barriere",
        name="conversations_add_message",
        arguments={"channel_id": "#general", "payload": "test de barrière"},
    )
    print(resultat)
