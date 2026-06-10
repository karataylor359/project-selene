import json
import httpx
from pprint import pprint
from openai import OpenAI
import os
import json

# ----------------------- GLOBALS -----------------------
client = OpenAI(api_key=os.environ["LLM_API_KEY"])
PORTS = {
     "artemis": 3002,
    "helios": 3001,
    "hydroponics": 3003,
    "aquifer": 3004,
    "zephyr": 3005,
    "prometheus": 3006,
    "medica": 3007,
    "terminus": 3008,
    "nexus": 3009,
    "forge": 3010,
    "vault": 3011,
    "sentinel": 3012,
}

# skip status endpoint because always nominal
ENDPOINTS = ["dependencies", "supplies", "logs", "comms"]

# ----------------------- FINDINGS -----------------------
pods_found = set() # names of pods discovered
dependencies_map = {} # pod: [pods that this DIRECTLY depends on], chained dependencies explored in reporting.py
supplies_map = {} # pod: [pods that this DIRECTLY supplies], chained supplies explored in reporting.py
log_timeline = [] # Will sort chronologically in reporting. use LLM to compute timeline of major events described in logs, and find discrepancies in the timeline, across pods.
comms_timeline = [] # Will sort chronologically in reporting. use LLM to compute timeline of major events described in comms, if comms exist
log_dependencies = {} # pod: [pods that this DIRECTLY depends on, ACCORDING TO LOGS]
log_supplies = {} # pod: [pods that this DIRECTLY supplies, ACCORDING TO LOGS]


# ----------------------- DISCOVERY PHASE HELPERS -----------------------
# Helper function, calls LLM to get dependencies mentioned in logs
def get_log_dependencies(logs):
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract structured dependencies from logs."
                    "Return ONLY valid JSON. No explanation. No extra text."
                    "Only include a dependency if there is explicit textual evidence. If uncertain, omit it."
                    )
            },
            {
                "role": "user",
                "content": f"""
                    Each log entry contains the pod that generated the log in the field pod_id.
                    Treat pod_id as the source pod.
                    Extract ALL implied infrastructure dependencies from these logs.

                    A dependency exists if a pod:
                    - relies on another pod for a resource
                    - receives failures, services, or coordination from another pod
                    - mentions another pod as required for operations

                    Return ONLY valid JSON in this format:
                    {{
                        "pod_id": "the pod that generated the log",
                        [
                            {{
                                "depends_on_pod_id": "<dependency_pod_id>",
                                "resource": "<what is being received>",
                                "evidence": "<exact or near exact log reference>"
                            }}
                        ]
                    }}
                   
                    Here are the logs for all the pods: {logs}
                    """
            }
        ]
    )
    return json.loads(response.output_text)

# Helper function, calls LLM to get supplies mentioned in logs
def get_log_supplies(logs):
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=[
            {
                "role": "system",
                "content": (
                    "You extract structured supplies from logs."
                    "Return ONLY valid JSON. No explanation. No extra text."
                    "Only include a supply if there is explicit textual evidence. If uncertain, omit it."
                    )
            },
            {
                "role": "user",
                "content": f"""
                    Each log entry contains the pod that generated the log in the field pod_id.
                    Treat pod_id as the source pod.

                    Your task is to extract IMPLIED SUPPLY RELATIONSHIPS between pods based ONLY on log evidence.

                    A supply relationship exists when a pod:
                    - provides a resource or service to another pod
                    - fulfills requests, transfers, deliveries, or support actions
                    - is explicitly or clearly acting as a provider in a dependency chain

                    IMPORTANT RULES:
                    - Only include relationships directly supported by log evidence
                    - Do NOT guess or infer without textual support
                    - If uncertain, omit the relationship
                    - Treat “supplies” as directional: provider → receiver
                    
                    Return ONLY valid JSON in this format:
                    {{
                        "pod_id": "the pod that generated the log",
                        [
                            {{
                                "supplies": "<the receiving pod>",
                                "resource": "<what is being supplied>",
                                "evidence": "<exact or near exact log reference>"
                                }}
                        ]
                    }}
                        
                    ]
                    Here are the logs for all the pods: {logs}
                    """
            }
        ]
    )
    return json.loads(response.output_text)

# ----------------------- DISCOVERY PHASE -----------------------

# Scan all pods, starting at Artemis gateway
for pod_id, port in PORTS.items():
    pods_found.add(pod_id)

    for endpoint in ENDPOINTS:
        url = f"http://{pod_id}:{port}/{endpoint}"

        try:
            response = httpx.get(url)

            if response.status_code == 404:
                continue
            else:
                data = response.json()
                
                # Add to maps
                if endpoint == "dependencies":
                    dependencies_map[pod_id] = data[endpoint]
                elif endpoint == "supplies":
                    supplies_map[pod_id] = data[endpoint]
                elif endpoint == "logs":
                    # Add {"pod_id": pod_id} to each log
                    named_logs = data[endpoint]
                    
                    # Add all logs to full timeline list
                    for log in named_logs:
                        log["pod_id"] = pod_id

                    # Add to full log_timeline
                    log_timeline.extend(named_logs)
                elif endpoint == "comms":
                    comms_timeline.extend(data["messages"])


        except Exception as e:
            print("ERROR: ", e)
            pass

# Make dependencies map using LLM, based on logs
log_dependencies = get_log_dependencies(log_timeline)

# Make supplies map using LLM, based on logs
log_supplies = get_log_supplies(log_timeline)

# Debugging...
# print(f"We found {len(pods_found)} pods, named: {pods_found}")
# pprint(dependencies_map)
# pprint(supplies_map)
# pprint(log_timeline)
# pprint(comms_timeline)
# print("\nLOG DEPENDENCIES: ")
# pprint(log_dependencies)
# print("\nLOG SUPPLIES: ")
# pprint(log_supplies)


# Write final map to output/map.json
final_map = {
    "pods_found": list(pods_found),
    "dependencies_map": dependencies_map,
    "supplies_map": supplies_map,
    "log_timeline": log_timeline,
    "comms_timeline": comms_timeline,
    "log_dependencies": log_dependencies,
    "log_supplies": log_supplies
}

with open("/rover/output/map.json", "w") as f:
    json.dump(final_map, f, indent=4)