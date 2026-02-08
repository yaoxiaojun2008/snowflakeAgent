# Summary: Calling Snowflake Internal Agent as a Tool

## Overall Procedure

1. **LangGraph Agent** receives user query
2. **Model (Claude-3.5-Sonnet)** decides to call `sales_analyst_tool`
3. **Tool** makes streaming API call to Snowflake SALES_AI agent
4. **Tool waits** for complete streaming response (up to 5 minutes)
5. **Tool filters and cleans** the response
6. **Tool returns** clean result to model
7. **Model** generates final response to user

---

## Key Technical Points

### 1. API Only Supports Streaming Mode
- Snowflake Agent API returns Server-Sent Events (SSE) format
- Must use `stream=True` in requests
- Non-streaming mode returns empty response (200 but no JSON)

### 2. Streaming Response Structure
The agent streams multiple types of content:
- **Status updates**: `[planning]`, `[executing_tools]`, `[reasoning_agent_stop]`
- **Reasoning text**: Explanations of what it's doing
- **Final answer**: The actual result (appears multiple times)
- **Duplicates**: Same content repeated throughout the stream

### 3. Tool Implementation
```python
response = requests.post(url, headers=headers, json=payload, stream=True, timeout=300)

for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data:'):
            json_str = decoded[5:].strip()
            data = json.loads(json_str)
            if 'text' in data:
                full_text += data.get('text', '')
```

---

## Last Modification: Filtering Logic

**Problem**: Stream contains noise (status messages, reasoning, duplicates)

**Solution**: Multi-layer filtering

### Step 1: Filter Out Status Messages
```python
# Skip lines starting with:
- '[planning]', '[executing_tools]', etc.
- 'I have', 'The user is asking', 'I should'
- Numbered lists: '1.', '2.', '3.'
```

### Step 2: Extract Clean Lines
```python
for line in lines:
    if (line_clean and 
        not line_clean.startswith('[') and 
        not line_clean.startswith('I have') and
        not line_clean.startswith('The user is asking') and
        not line_clean.startswith('I should') and
        not '1.' in line_clean[:10]):
        answer_lines.append(line_clean)
```

### Step 3: Deduplicate Sentences
```python
sentences = tool_result.split('. ')
seen = set()
unique_sentences = []
for sentence in sentences:
    sentence_clean = sentence.strip()
    # Only keep sentences > 20 chars and not seen before
    if sentence_clean and sentence_clean not in seen and len(sentence_clean) > 20:
        seen.add(sentence_clean)
        unique_sentences.append(sentence_clean)
```

### Step 4: Reconstruct Clean Result
```python
tool_result = '. '.join(unique_sentences)
```

---

## Key Configuration

- **Timeout**: 300 seconds (5 minutes) - allows agent time to query data and reason
- **Authorization**: `Bearer {PAT_TOKEN}` format
- **Endpoint**: `/agents/{AGENT_NAME}:run`
- **Payload**: Standard message format with role/content structure

---

## Result

**Before filtering**: 2000+ chars with reasoning, status, duplicates

**After filtering**: Clean answer like:
> "The product with the best sales in 2025 was Fitness Item 10 from the Fitness Wear category, with total sales of $1,153,446.40. This product had sales activity over 364 days between May 16, 2025 and August 14, 2025."

This clean result is what the outer model receives to formulate its final response.

---

## Implementation Files

- **Main Agent**: `Walter_agent_interAgent.py` - LangGraph agent with internal agent tool
- **Test Script**: `test_agent_api.py` - Demonstrates streaming behavior
- **Tool**: `sales_analyst_tool` - Wraps SALES_AI agent as a LangChain tool

## Architecture

```
User Query
    ↓
LangGraph Agent (Walter)
    ↓
Model (Claude-3.5-Sonnet via SQL)
    ↓
Tool Call Decision
    ↓
sales_analyst_tool
    ↓
Snowflake SALES_AI Agent (Streaming API)
    ↓
Filter & Clean Response
    ↓
Return to Model
    ↓
Final Response to User
```
