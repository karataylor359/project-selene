import json
import networkx as nx
from openai import OpenAI
import os

# ----------------------- GLOBALS -----------------------
dependencies_map = {}
supplies_map = {}
log_timeline = []
comms_timeline = []
log_dependencies = {}
log_supplies = {}

# Read `/rover/output/map.json`
with open("/rover/output/map.json", "r") as f:
    data = json.load(f)
    dependencies_map = data["dependencies_map"]
    supplies_map = data["supplies_map"]
    log_timeline = data["log_timeline"]
    comms_timeline = data["comms_timeline"]
    log_dependencies = data["log_dependencies"]
    log_supplies = data["log_supplies"]

# ----------------------- DEPENDENCY/SUPPLY ANALYSIS -----------------------
# Build COMPLETE dependency graph (chained dependencies)
# build COMPLETE supplies graph (chained supplies)
# SPOF analysis
# Check that dependencies and supplies match (use LLM)

### Make transitive, with edges for ALL dependencies, not just direct ones
G = nx.DiGraph()
for pod, deps in dependencies_map.items():
    for dep in deps:
        G.add_edge(
            pod,
            dep["pod_id"],
            resource=dep["resource"],
            criticality=dep["criticality"]
        )
transitive = nx.transitive_closure(G)

# Build COMPLETE dependency graph with chained dependencies
complete_dependencies = {}
for pod in G.nodes:
    complete_dependencies[pod] = list(
        transitive.successors(pod)
    )

# Build COMPLETE supplies graph with chained supplies
complete_supplies = {}
G_supplies = nx.DiGraph()
for pod, deps in dependencies_map.items():
    for dep in deps:
        G_supplies.add_edge(
            pod,
            dep["pod_id"],
            resource=dep["resource"],
            criticality=dep["criticality"]
        )
transitive_supplies = nx.transitive_closure(G_supplies)

for pod in G_supplies.nodes:
    complete_supplies[pod] = list(
        transitive_supplies.successors(pod)
    )


### SPOF: Simulating single failures to find single point of failure:
spof = {}
for failed_pod in G.nodes:
    affected = nx.ancestors(transitive, failed_pod)
    spof[failed_pod] = {
        "num_affected": len(affected), # how many pods affected if failed_pod fails
        "pods_affected": affected
    }

# SPOF continued, finding impact of a failed pod
impact = {}
for pod in G.nodes:
    impact[pod] = len(
        nx.ancestors(transitive, pod)
    )
sorted_impact = dict(sorted(impact.items(), key=lambda impact: impact[1], reverse=True))


# ----------------------- LOGS & COMMS ANALYSIS -----------------------
# Sort the logs and comms into timeline, chronologically based on "timestamp"
sorted_logs = sorted(log_timeline, key=lambda d: d["timestamp"])
sorted_comms = sorted(comms_timeline, key=lambda d: d["timestamp"])

# LLM to build story and find discrepancies within the timeline
# Cross compare with dependency and supply graphs
# Cross compare between each other

# ----------------------- LLM REQUEST -----------------------
client = OpenAI(api_key=os.environ["LLM_API_KEY"])

request_data = {
    "spof": spof,
    "direct_dependencies_map_with_info": dependencies_map, # contains resource & criticality & notes
    "direct_supplies_map_with_info": supplies_map, # contains resource
    "complete_dependencies_map": complete_dependencies,
    "complete_supplies_map": complete_supplies,
    "sorted_impact": sorted_impact,
    "log_timeline": log_timeline,
    "comms_timeline": comms_timeline,
    "log_dependencies": log_dependencies,
    "log_supplies": log_supplies
}

response = client.responses.create(
    model="gpt-5.4-mini",
    input=[
        {
            "role": "system",
            "content": (
                "Analyze the colony for systemic risks, looking beyond surface-level status."
                "Produce a textual analysis report with your findings formatted for a .md file."
                )
        },
        {
            "role": "user",
            "content": f"""
                Analyze the colony and write up a report discussing the issues found.

                Look for:
                1. Single points of failure. Which pods are most depended upon? For the top depended upon pod, build a story of what will happen to the other pods in the system
                if that pod fails.
                2. Find any inconsistencies between the complete chained supplies and dependency graphs (complete_supplies_map and complete_dependencies_map), i.e. Identify all inconsistencies where a pod depends on a resource that is not supplied by any pod it depends on. 
                Write up the list of pods with missing resources, and for each, show the missing resources, taking into account criticality for risk level. Resource information can be found in direct_dependencies_map_with_info and direct_supplies_map_with_info
                3. Build a story from the logs and comms timelines, what does this reveal about how the colony's infrastructure evolved over time, specifically what risks were introduced as the colony changed over time.
                4. Find any inconsistencies between the logs timeline and the comms timeline, and any inconsistencies between the supplies/dependencies graphs and the logs/comms timelines,
                does this reveal any hidden single points of failure or risk issues in the colony? What resources are lost in this point of failure?
                5. Find any inconsistencies between the log_dependencies (dependencies explained in the logs) and dependencies_map (actual reported dependencies), see if the logs reveal outdated reported dependencies or other inconsistencies
                6. Find any inconsistencies between the log_supplies and supplies_map
                
                Then, recommend some actionable steps to fix these issues in the system, and write each recommendation in only 1-2 sentences.

                Here is the colony data: {request_data}
                spof shows for a pod that fails, how many other pods fail and what are they
                complete_dependencies contains depender_pod_id: [list of chained dependencies, all pods it depends on]
                sorted_impact gives the nuumber of pods that depend on each pod
                """
        }
    ]
)

output_analysis = response.output_text
with open("/rover/output/report.md", "w") as f:
    json.dump(output_analysis, f)

print(output_analysis)