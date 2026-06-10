# ASSIGNMENT WRITE UP

## Design decisions and architecture:
mapping.py contains the raw code for crawl and data parsing and restructuring for LLM analysis.
reporting.py contains some further data analysis and the main code for the LLM request to further analyze the data and generate the report.

### mapping.py
The final goal of mapping.py was to end up with map.json containing the following data structures:
- dependencies_map: a dictionary mapping a depender pod to a list of all pods it directly depends on, retrieved from the "/dependencies" endpoint
- supplies_map: a dictionary mapping a pod to a list of all pods it directly supplies, retrieved from the "/supplies" endpoint
- log_timeline: a list of all logs from all pods, from the "/logs" endpoint
- comms_timeline: a list of all comms from all pods, from the "/comms" endpoint
- log_dependencies: a dictionary of dependencies found from logs NOT dependencies (i.e. these are dependencies found in the logs that were not updated in dependencies endpoint, so we can start to find inconsistencies and risk points in the system). Used an LLM to parse through the textual log evidence and determine supplies. 
- log_supplies: a dictionary of supply pods found from logs NOT supplies endpoint (similar to log_dependencies). Used an LLM to parse through the textual log evidence and determine supplies.

### reporting.py
In reporting.py, I wanted to use these data structures in the following ways to gain information:
- For dependencies_map and supplies_map, create a mapping of chained dependencies and supplies to see ALL pods that a given pod depends on/supplies, not just direct dependencies/supplies. This would help to gain a more complete picture of how the pods work together. Compare these two maps to look for instances where a pod listed another pod as a dependency but didn't supply the other. I also ran a single point of failure analysis, to see if the system is distributed enough to withstand single failures or if there is a point of weakness in the system.
- For log_timeline and comms_timeline, order these chronologically to build a story and look for times when risks are introduced to the system. Additionally, cross-compare these two to see if pods miscommunicated and potentially introduced a risk.
- Cross-compare log_dependencies with the dependencies_map and chained dependencies to find inconsistencies (are there dependencies described in the logs but not updated in the actual dependency endpoint? This could reveal inconsistences in each pod's data and revela points of risk.) I ran a similar analysis cross-comparing log_supplies with the supplies_map and chained supplies.

### Decisions in both
In mapping.py, I decided just to parse through 4 of each pod's endpoints: dependencies, supplies, logs, and comms, since all of the information I wanted to analyze could be accessed from these endpoints. 

I used an LLM to parse through textual evidence (such as the logs and comms) and turn it into dictionaries, e.g. the log_dependencies and log_supplies, to allow for easier cross-comparison. 

In reporting.py, I did some quick analysis before giving information to the LLM, i.e. in the single point of failure analysis, finding out how many pods depended on each pod to measure the risk of a single pod failing. I then used this data to tell the LLM to specifically track what would happen if a high-risk pod failed (how it would affect the other pods, what resources would be lost, how likely this is to happen given the stated risk-level in the dependencies/supplies map).


## What my agent found
My agent found that Aquifer, then Helios and Terminus were the most depended upon pods, i.e. if one of these fails, the entire system is at risk of collapse. My agent discovered a failure story for Aquifer, describing the chain reaction of which pods would lose which resources, leading to system-wide collapse.

Then, we found inconsistences between dependency and supply graphs, i.e. cases where a pod depended on another pod for a resource, but that pod did not list the first as a pod to supply resource to. Some of these include Zephyr not being in the list of pods that Terminus supplies, despite depending on Terminus. In addition, Prometheus depends on Terminus and Zephyr but is not supplied by those. Medica depends on Hydroponics, Helios, and Terminus but is not suppled by those. We found that this poses a risk to the medical production chain formed by Medica and Prometheus, as it is very dependent upon Hydroponics and Zephyr. Another risky point is the Vault pod, where our backups are stored, as this was decomissioned -- the logs and comms reveal that the water backup is gone, which poses a risk. 

The report reveals that there are a surprising number of inconsistences between the logs and the dependencies and supplies maps. The main revelation is that the dependency map is quite outdated (changes made in the logs are not reflected in the graph) -- dependencies chains in the logs show that resources have been rerouted through the pods, and critically, the Vault backups have been removed, proving that in the likely scenario of a pod failing, such as Aquifer, Helios, or Terminus, the system would not have backups in place to keep the colonies afloat. A notable supply inconsistency is that logs show Artemis supplies Terminus, but this is not reflected in the supply map.

## What I'd do with more time
My agent was able to analyze many detailed points of risk, such as individual inconsistences between the dependency and supply maps. If I had more time, I would dive deeper and have the LLM paint a broader picture of what this would mean for the system as a whole, (i.e. finding other cascading failure paths like the Aquifer one.) We found that the water backup in Vault was decomissioned, so by tracing the water resources specifically, I'd figure out how this could affect the system as a whole and measure what level of risk this poses. While my agent identified some initial ways to fix the system (e.g. backing up the water supply for Aquifer), these seem to be immediate short-term solutions -- it would also be interesting to further analyze the root causes of these failures (was it miscommunication in the logs? Outdated information in the dependency/supply endpoints?) and figure out how to fix them, and build new systems to prevent this from happening in the future (perhaps building some automated system to check through logs and update endpoints as needed, or a system to analyze risk-level when introducing new pods and dependency/supply chains for resources and recommend/warn against actions). 


In looking through the report, I see some of my chosen analysis methods didn't reveal any risks, e.g. there were no inconsistences found between the logs and the comms. This is still useful information! But I would like to keep honing in and re-prompting in other ways to narrow down more points of error in the system. Specifically, I'd look deeper into the Helios, Aquifer, Terminus risk triangle to find some root causes and map out how Helios and Terminus failures would cascade. I would also trace the resources more carefully -- most of my analysis came from looking at which pod named another pod as a dependency/supplier, without considering what resources were being used. This made it a bit more difficult for my agent to explicitly say what the issue was in these mismatch cases. Perhaps there are some errors in where the pods get their resources from (for example, a potential error saying a pod gets its water resources from Helios), or if a pod is getting the same resources from different pods and analyze whether this is redundant OR if this actually leads to a more reliable, distributed system. 

In summary, my agent generated quite a long report, so I would refine my data analysis, remove analysis methods that didn't yield risks, dive deeper into the errors revealed by the first pass of the agent.