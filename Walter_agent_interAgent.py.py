import os
import logging
import asyncio
import json
import requests
from snowflake.snowpark import Session
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START
from langgraph.graph import MessagesState
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from langchain_snowflake import ChatSnowflake
from langchain_core.tools import tool

logging.getLogger().setLevel(logging.CRITICAL)

SNOWFLAKE_PAT = "your PAT"
SNOWFLAKE_ACCOUNT = "EUGMZKF-PB41825"
SNOWFLAKE_USER  = "YAOXIAOJUN2008"
SNOWFLAKE_MCP_SERVER_URL = "https://EUGMZKF-PB41825.snowflakecomputing.com/api/v2/databases/HEALTH_DB/schemas/PUBLIC/mcp-servers/HEALTH_MCP_SERVER"

USER_QUERY = "Which product had the best sales among production sellers in year 2025?"
# USER_QUERY = "Show me the trend of sales by product category between June 2025 and August 2025?"

AGENT_URL = "https://EUGMZKF-PB41825.snowflakecomputing.com/api/v2/databases/SNOWFLAKE_INTELLIGENCE/schemas/AGENTS/agents/SALES_AI:run"



async def main():
    """Main async function to initialize MCP client, build agent, and run queries."""
    snowflake_connection_parameters = {
        "account": SNOWFLAKE_ACCOUNT,
        "user": SNOWFLAKE_USER,
        "token": SNOWFLAKE_PAT,
        "authenticator": "PROGRAMMATIC_ACCESS_TOKEN",
        "warehouse": "DASH_WH_SI",
        "database": "DASH_DB_SI",
        "schema": "RETAIL",
    }

    snowpark_session = Session.builder.configs(
        snowflake_connection_parameters
    ).create()


    try:

        @tool
        def sales_analyst_tool(query: str) -> str:
            """Useful for product sales, best sellers, and 2025 revenue data."""
            print(f"\n🔧 [TOOL CALL] sales_analyst_tool invoked")
            print(f"   Input query: {query}")
            
            # Add instruction for concise response
            modified_query = f"{query}\n\nPlease provide only the final answer in a brief, concise summary."
            
            # Call the SALES_AI agent using REST API (non-streaming mode)
            url = "https://EUGMZKF-PB41825.snowflakecomputing.com/api/v2/databases/SNOWFLAKE_INTELLIGENCE/schemas/AGENTS/agents/SALES_AI:run"
            
            headers = {
                "Authorization": f"Bearer {SNOWFLAKE_PAT}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": modified_query}]}
                ],
                "stream": False  # Key: disable streaming in payload
            }
            
            print(f"   Calling URL: {url}")
            print(f"   Mode: Non-streaming (stream=False in payload)")
            print(f"   Timeout: 300 seconds (5 minutes)")
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=300)
                print(f"   Response status: {response.status_code}")
               
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response data: {data}")
                    print(f"   Response JSON keys: {list(data.keys())}")
                    
                    # Extract text from response structure
                    # The response has keys: ['role', 'content', 'metadata']
                    # Content is a list of items with type and text
                    contents = data.get('content', [])
                    
                    if not contents:
                        # Fallback: try nested message structure
                        contents = data.get('message', {}).get('content', [])
                    
                    text_outputs = [item['text'] for item in contents if item.get('type') == 'text']
                    
                    print(f"   Found {len(text_outputs)} text items in response")
                    
                    if text_outputs:
                        # Join all text outputs
                        full_text = " ".join(text_outputs).strip()
                        print(f"   Raw text length: {len(full_text)} chars")
                        
                        # Apply filtering to remove reasoning/status messages
                        lines = full_text.split('\n')
                        answer_lines = []
                        
                        # Patterns to skip (reasoning/status messages)
                        skip_patterns = [
                            '[',  # Status messages
                            'I have',
                            'I should',
                            'The user is asking',
                            'This is a',
                            'This requires',
                            'I will',
                            'I need to',
                            'Let me',
                            'First,',
                            'Second,',
                            'Third,',
                        ]
                        
                        for line in lines:
                            line_clean = line.strip()
                            
                            if not line_clean:
                                continue
                            
                            # Skip if line starts with any skip pattern
                            should_skip = False
                            for pattern in skip_patterns:
                                if line_clean.startswith(pattern):
                                    should_skip = True
                                    break
                            
                            # Skip numbered lists
                            if len(line_clean) >= 2 and line_clean[0].isdigit() and line_clean[1] == '.':
                                should_skip = True
                            
                            if not should_skip:
                                answer_lines.append(line_clean)
                        
                        # Join and deduplicate
                        tool_result = ' '.join(answer_lines)
                        
                        # Deduplicate sentences
                        sentences = []
                        for part in tool_result.replace('.\n', '. ').split('. '):
                            sentences.append(part.strip())
                        
                        seen = set()
                        unique_sentences = []
                        for sentence in sentences:
                            sentence_clean = sentence.strip()
                            sentence_normalized = ' '.join(sentence_clean.lower().split())
                            
                            if (sentence_clean and 
                                sentence_normalized not in seen and 
                                len(sentence_clean) > 20):
                                seen.add(sentence_normalized)
                                unique_sentences.append(sentence_clean)
                        
                        tool_result = '. '.join(unique_sentences)
                        if tool_result and not tool_result.endswith('.'):
                            tool_result += '.'
                        
                        print(f"   ✅ Tool output: {tool_result[:2000]}...")
                        return tool_result if tool_result else full_text
                    else:
                        error_msg = "The analyst tool ran successfully but returned no text data."
                        print(f"   ⚠️ {error_msg}")
                        return error_msg
                else:
                    error_msg = f"Error: API returned status {response.status_code}"
                    print(f"   ❌ {error_msg}")
                    return error_msg
                    
            except requests.exceptions.Timeout:
                error_msg = "Tool call timed out after 300 seconds (5 minutes)"
                print(f"   ⏱️ {error_msg}")
                return error_msg
            except Exception as e:
                error_msg = f"Request failed: {str(e)}"
                print(f"   ❌ {error_msg}")
                return error_msg
        
        tools = [sales_analyst_tool]
        

        
        # Create SQL-based model wrapper
        print(f"\n=======Initializing SQL-based Chat Model=======")
        
        class SQLBasedCortexModel:
            """Wrapper for Snowflake Cortex AI using SQL instead of REST API."""
            
            def __init__(self, session, model_name="mistral-large"):
                self.session = session
                self.model_name = model_name
                self.tools = []
            
            def bind_tools(self, tools):
                """Bind tools to the model."""
                self.tools = tools
                return self
            
            def invoke(self, messages):
                """Invoke the model with messages using SQL (synchronous)."""
                print(f"\n🤖 [MODEL CALL] SQLBasedCortexModel.invoke called")
                print(f"   Model: {self.model_name}")
                print(f"   Number of messages: {len(messages)}")
                
                # Convert messages to a prompt string
                prompt_parts = []
                for i, msg in enumerate(messages):
                    if hasattr(msg, 'content'):
                        if hasattr(msg, 'type'):
                            if msg.type == 'human':
                                prompt_parts.append(f"User: {msg.content}")
                                print(f"   Message {i}: [human] {msg.content[:100]}...")
                            elif msg.type == 'ai':
                                prompt_parts.append(f"Assistant: {msg.content}")
                                print(f"   Message {i}: [ai] {msg.content[:100]}...")
                            elif msg.type == 'tool':
                                prompt_parts.append(f"Tool Result: {msg.content}")
                                print(f"   Message {i}: [tool] {msg.content[:100]}...")
                        else:
                            prompt_parts.append(str(msg.content))
                            print(f"   Message {i}: {str(msg.content)[:100]}...")
                
                prompt = "\n".join(prompt_parts)
                
                # Add tool information to prompt if tools are available
                if self.tools:
                    tool_descriptions = []
                    for t in self.tools:
                        tool_descriptions.append(f"- {t.name}: {t.description}")
                    
                    tools_text = "\n".join(tool_descriptions)
                    prompt = f"""You are a helpful assistant with access to these tools:

{tools_text}

If you need to use a tool to answer the question, respond ONLY with:
TOOL_CALL: <tool_name>
QUERY: <the query to pass to the tool>

Otherwise, provide a direct answer.

{prompt}
"""
                    print(f"   Tools available: {[t.name for t in self.tools]}")
                
                # Call Cortex via SQL
                try:
                    # Escape single quotes in prompt
                    escaped_prompt = prompt.replace("'", "''")
                    
                    sql_query = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        '{self.model_name}',
                        '{escaped_prompt}'
                    ) as response
                    """
                    
                    print(f"   Calling Snowflake Cortex...")
                    result = self.session.sql(sql_query).collect()
                    
                    if result:
                        response_text = result[0]['RESPONSE']
                        print(f"   ✅ Model response: {response_text[:200]}...")
                        
                        # Check if model wants to use a tool
                        if "TOOL_CALL:" in response_text and "QUERY:" in response_text:
                            # Extract tool name and query
                            lines = response_text.split('\n')
                            tool_name = None
                            tool_query = None
                            
                            for line in lines:
                                if line.startswith("TOOL_CALL:"):
                                    tool_name = line.replace("TOOL_CALL:", "").strip()
                                elif line.startswith("QUERY:"):
                                    tool_query = line.replace("QUERY:", "").strip()
                            
                            if tool_name and tool_query:
                                print(f"   🔧 Model requesting tool call: {tool_name}")
                                print(f"   🔧 Tool query: {tool_query}")
                                # Find the matching tool
                                from langchain_core.messages import AIMessage
                                return AIMessage(
                                    content=f"I'll use the {tool_name} tool to answer your question.",
                                    tool_calls=[{
                                        "name": tool_name,
                                        "args": {"query": tool_query},
                                        "id": "call_1"
                                    }]
                                )
                        
                        # Return regular response
                        print(f"   💬 Returning regular response (no tool call)")
                        from langchain_core.messages import AIMessage
                        return AIMessage(content=response_text)
                    else:
                        print(f"   ⚠️ No response from model")
                        from langchain_core.messages import AIMessage
                        return AIMessage(content="No response from model")
                        
                except Exception as e:
                    error_msg = str(e)
                    print(f"   ❌ Model error: {error_msg}")
                    from langchain_core.messages import AIMessage
                    if "Trial accounts are not allowed" in error_msg:
                        return AIMessage(content=f"Error: Trial account limitation. Please upgrade to a paid account.")
                    else:
                        return AIMessage(content=f"Error calling model via SQL: {error_msg}")
        
        model = SQLBasedCortexModel(snowpark_session, model_name="claude-3-5-sonnet")
        print(f"Model: {model.model_name} (via SQL)")
        
        # Build the LangGraph Agent
        print(f"\n=======Building LangGraph Agent=======")
        
        model_with_tools = model.bind_tools(tools)

        async def call_model(state: MessagesState):
            # synchronous invoke inside the async node
            response = model_with_tools.invoke(state["messages"]) 
            return {"messages": [response]}

        
        # Create the StateGraph
        builder = StateGraph(MessagesState)
        builder.add_node(call_model)
        builder.add_node(ToolNode(tools))
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model",
            tools_condition,
        )
        builder.add_edge("tools", "call_model")
        graph = builder.compile()
        
        print("Agent graph built successfully!")
        
        # Test the agent with a query
        print(f"\n=======Testing Agent=======")
        test_query = USER_QUERY
        print(f"Query: {test_query}")
        
        response = None
        try:
            response = await graph.ainvoke({"messages": [test_query]})
            print(f"\nResponse: {response['messages'][-1].content}")
        except Exception as e:
            print(f"Error during agent invocation: {e}")
        finally:
            if response:
                print(f"\nFull message count: {len(response['messages'])}")
    
    finally:
        snowpark_session.close()
        print("\n=======Session Closed=======")


if __name__ == "__main__":
    asyncio.run(main())
