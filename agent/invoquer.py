"""Invoque Sentinelle sur AgentCore Runtime, comme le fera la Lambda."""
import json
import os
import sys
import uuid

import boto3
from botocore.config import Config

# L'agent peut réfléchir plus d'une minute : on rallonge le délai de lecture (60 s par défaut)
client = boto3.client("bedrock-agentcore", region_name="eu-central-1",
                      config=Config(read_timeout=300, retries={"max_attempts": 1}))
question = sys.argv[1] if len(sys.argv) > 1 else "Une alarme signale des échecs de virement. Enquête."
session = f"manuel-{uuid.uuid4()}"
reponse = client.invoke_agent_runtime(
    agentRuntimeArn=os.environ["SENTINELLE_RUNTIME_ARN"],
    runtimeSessionId=session,
    payload=json.dumps({"prompt": question, "session_id": session}).encode(),
)
print(json.dumps(json.loads(reponse["response"].read()), indent=2, ensure_ascii=False))
