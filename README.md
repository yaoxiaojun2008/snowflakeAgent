# BUILD Agent Powered Workflows Using Snowflake Cortex AI and Managed MCP Servers

## Overview

We'll build a health research agent that uses MCP tools to query:
- PubMed for medical literature
- Clinical trials databases for trial information

We'll also show a powerful evaluation flow using AI Observability that you can use to improve your MCP tool descriptions.

Get started by opening the [notebook](./build-and-evaluate-langgraph-agents-with-mcp-tools.ipynb) and following the instructions there.

You can also follow along the hands on lab in this [video](https://www.snowflake.com/en/build/americas/agenda?agendaPath=session/1751697).

Walter: I modify the  the external agents and did not call MCP server's tools. External agents call internal agent.
Issues we had: 1.LOOP call in two nodes of Model_call and tools, we changed stream mode to non-stream mode, restrict internal agent don't show  messages of thinking precedure.
