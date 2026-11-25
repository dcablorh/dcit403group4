# Lab 3: Percepts and Actions as Tools: Function Calling and MCP

**Topic:** Function calling and the Model Context Protocol (MCP)

**Style:** Standalone, code

Instructions are in the DCIT 403 Laboratory Manual (version 2), Lab 3.

## Deliverables

- `server.py` with at least four tools, `client_agent.py`, `concept_check.md`
- `evidence/tool_calls.jsonl` and a screenshot of the MCP Inspector
- `evidence/react_via_mcp.txt` (Wednesday)

Put outputs, traces, logs and screenshots in `evidence/`. Answer `concept_check.md` before the Wednesday session. Steps marked Independent in the manual are done on your own between the Thursday and Wednesday labs.

## Data

`data/pharmacy_stock.csv` is regenerated relative to today by `python scripts/refresh_dates.py` (run from the repository root), so "items expiring within 60 days" always returns results.

**Note on MCP versions.** The manual's code uses `from mcp.server.fastmcp import FastMCP` (mcp 1.x). `requirements.txt` keeps `mcp` below version 2, where this was renamed. If you see `No module named 'mcp.server.fastmcp'`, run `pip install "mcp>=1.9,<2"`.

---

## What I built this week

| File | What it does | Lab step |
|---|---|---|
| `function_calling.py` | One plain `check_stock(item, strength)` + JSON schema passed in `tools=`; prints `message.tool_calls`, runs the function and sends the result back as a `tool` message. No MCP. | 1 |
| `server.py` | FastMCP server `pharmacy-stock`. Read tools (percepts): `check_stock`, `search_items`, `list_expiring`. Write tool (actuator): `record_sale`. | 2, 4 |
| `client_agent.py` | Starts `server.py` over stdio, discovers the tools with `list_tools()`, builds the schemas for LiteLLM, and runs every call through `session.call_tool`. Never imports a tool. Logs every call to `evidence/tool_calls.jsonl`. | 3, 5 |
| `react_via_mcp.py` | Lab 2's ReAct agent with its tool list taken from the MCP server instead of `lab02/tools.py`. Reuses Lab 2's parser; `Action Input` becomes a JSON object. | Wednesday |
| `concept_check.md` | Part A answers | Part A |

### Which tools are percepts and which are actions

| Tool | Kind | Why it matters |
|---|---|---|
| `check_stock` | percept | read-only; a wrong answer costs one step |
| `search_items` | percept | read-only; the only tool that matches words split across name/strength/form |
| `list_expiring` | percept | read-only; returns `days_left`, negative if already expired |
| `record_sale` | **action** | rewrites the CSV. Validates every argument, refuses non-positive quantities, ambiguous items, expired batches and oversales, and holds a write lock so two sales cannot read-modify-write at once |

### Run it

```bash
cd lab03
python function_calling.py --question "Do we have amoxicillin 500mg?"     # step 1
python client_agent.py --question "Do we have amoxicillin 500mg?"         # steps 3
python client_agent.py --suite                                            # steps 5: six questions
python react_via_mcp.py --question "Do we have amoxicillin 500mg?"        # Wednesday
npx @modelcontextprotocol/inspector python server.py                      # step 2, browser UI
```

The installed Inspector (v2.13) starts on `http://127.0.0.1:6274` and lists the
server as a card; flip its switch to connect, then open the Tools tab. Its CLI
mode is what produced `evidence/inspector_tools_list.txt`:
`npx @modelcontextprotocol/inspector --cli "python server.py" --method tools/list`.

`LLM_MODEL` and `GROQ_API_KEY` come from `.env` at the repository root. Groq's
free tier limits input tokens per minute, so the runners pause between
questions and retry a 429 (5, 10, 20, 30 s) instead of losing the run.

### Evidence

| File | From |
|---|---|
| `evidence/function_calling.txt` | step 1, three questions, `tool_calls` printed |
| `evidence/client_agent_suite.txt` | step 5, the six questions end to end |
| `evidence/tool_calls.jsonl` | one JSON line per tool call: timestamp (UTC), question id, tool, arguments, result summary, duration in ms, ok |
| `evidence/client_agent_run.txt` | a single-question run of `client_agent.py`, kept because it shows the full step-1 → step-2 transcript and the final answer |
| `evidence/inspector_tools_list.txt` | MCP Inspector in CLI mode: `tools/list`, `tools/call check_stock`, `tools/call list_expiring` |
| `evidence/tool_call_wrong_args_before_fix.txt` | the earlier run that made the wrong call described below |
| `evidence/react_via_mcp.txt` | Wednesday: Lab 2's agent with MCP-discovered tools |
| `evidence/mcp_inspector.png` | the Inspector web UI connected to `pharmacy-stock`: Tools (4) with `check_stock` selected and its schema on screen (Inspector v2.13.0) |

### Six-question run (step 5)

The first six lines of the log are the suite, one question each. All four tools
were exercised: `check_stock` (q1, q4), `list_expiring` (q2), `search_items`
(q3), `record_sale` (q5 sale, q6 oversale).

- q5: 3 packs of amoxicillin 500mg sold → 40 → **37** in the CSV, GHS 105.00.
- q6: 500 packs of paracetamol 500mg refused: *"Only 150 packs ... are in stock,
  not 500"*; the CSV was not touched.

The **seventh** line is a later single-question run
(`evidence/client_agent_run.txt`, question id 1 again) made to check the
`check_stock` answer after the fixes. It is appended to the same file because the
logger always appends; the suite itself is the first six lines.

### One wrong tool call, and the fix

In the earlier run the model asked for "paracetamol syrup" and put the form in
the strength argument: `check_stock(item="paracetamol syrup")`, then
`search_items(query="paracetamol syrup")` — both returned no rows, because the
old `search_items` matched the whole query string against one field at a time.

Two changes fixed it:

1. The `check_stock` docstring now says `item` is the medicine name only and
   that form words belong in `search_items`. The description is part of the
   prompt, so this steers the arguments.
2. `search_items` now splits the query into words and requires each word to
   appear somewhere in name + strength + form, so "paracetamol syrup" matches
   `Paracetamol 120mg/5ml syrup (100ml)`.

In the final run q3 was a single correct `search_items({"query": "paracetamol
syrup"})` call. The before/after transcripts are in `evidence/`.

### What had to change for the Lab 2 agent (Wednesday)

- The tool list and the argument names now come from `list_tools()`; the prompt
  is built from the MCP descriptions instead of a hand-written string.
- `Action Input` must be a JSON object (`{"item": "amoxicillin"}`), because MCP
  tools take named arguments rather than one free-text string. The parser from
  Lab 2 is unchanged; the JSON is decoded after parsing.
- The loop still writes every `Observation:` line itself, but the value comes
  from `session.call_tool`, i.e. from another process.
