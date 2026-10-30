# Contracts

The seams between the agents. Each contract is owned by one agent, the only one that edits it.

| File | Between | Owned by |
|---|---|---|
| TODO | TODO | TODO |

They start as v0 sketches written by the planning conversation, and the agent that owns each makes v1 first thing. Each contract starts with a version line, `Version: v1, Mon Jan 5, 14:20`, its time taken from the clock.

To change a contract you don't own, write a request in your status file and send the agent that owns it a heads-up. When you change your own: bump the version line, note it in your status file, tell the agents that use it, and keep the old shape working until they've moved.
