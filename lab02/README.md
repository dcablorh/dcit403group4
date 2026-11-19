# Lab 2: Architectures: A ReAct Agent From Scratch

**Topic:** Reactive, deliberative, BDI and hybrid architectures; the ReAct loop as a modern hybrid

**Style:** Standalone, code (no framework)

Instructions are in the DCIT 403 Laboratory Manual (version 2), Lab 2.

## Deliverables

- `tools.py`, `react_agent.py`, `concept_check.md`
- `evidence/baseline.md` and at least six traces

Put outputs, traces, logs and screenshots in `evidence/`. Answer `concept_check.md` before the Wednesday session. Steps marked Independent in the manual are done on your own between the Thursday and Wednesday labs.

---

## What I built this week

A ReAct agent for a fictional Makola Market trader: plain Python, no framework,
the model called through LiteLLM.

| File | What it does | Lab step |
|---|---|---|
| `check_env.py` | Confirms `LLM_MODEL` and the key (masked, never printed) and makes one small call. Run this first. | setup |
| `baseline.py` | The model alone, no tools: budget question ×3 plus two factual questions → `evidence/baseline.md` | 1 |
| `tools.py` | `calculator` (AST + operator table, never `eval`) and `wiki_lookup` (Wikipedia summary API); the tool descriptions that go into the prompt | 2 |
| `react_agent.py` | ReAct prompt, tolerant parser, loop with reactive error handling, `max_steps`, 429/connection retry, trace writer | 3, 4, 5 |
| `test_parser.py` | Twelve reply shapes, printing the manual's single regex beside the tolerant parser → `evidence/parser_tests.txt` | 3, 5 |
| `concept_check.md` | Part A answers | Part A |
| `report_draft.md` | Draft of the 2–3 page report (export to PDF as `DCIT403_Lab02_<StudentID>.pdf`) | report |

### Run it

```bash
cd lab02
python check_env.py --call                                      # environment ready?
python baseline.py                                              # step 1, no tools
python -c "from tools import calculator, wiki_lookup; print(calculator('4*185 + 3*95')); print(wiki_lookup('Makola Market')[:80])"
python -c "from tools import calculator; print(calculator(\"__import__('os')\"))"   # must print Error:
python react_agent.py --question "I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left?"
python react_agent.py --suite                                  # steps 4 and 5: six questions
python test_parser.py                                          # parser tests, no model call
```

`LLM_MODEL` comes from `.env` at the repository root. Traces are written to
`evidence/trace_<n>_<tag>.txt`. There is no fake-model mode: every trace in
`evidence/` comes from a real model call.

### Model note

This lab runs on `groq/qwen/qwen3.8-27b`, not the default `openai/gpt-oss-20b`.
gpt-oss-20b always answers ReAct questions with a native JSON tool call and
Groq rejects it because no tools were supplied:
`400 Tool choice is none, but model called a tool` (`tool_use_failed`). It hit
all seven questions in `evidence/attempt_gptoss_tool_use_failed.txt`. The text
protocol is Lab 2's whole point, so a model that follows it is required;
function calling proper is Lab 3.

### Error handling (Step 5)

| Failure | What the loop does |
|---|---|
| Reply has no `Action:` line | Sends back a corrective Observation with the exact required format; the step still counts |
| Unknown tool name | Sends back the list of valid actions |
| Tool returns an error string | The error text becomes the Observation; the loop continues |
| Model never calls `finish` | `max_steps` stops it and records `OUTCOME: max_steps` |
| HTTP 429 or a dropped connection | Waits 2, 4, 8, 16 s and retries, then `OUTCOME: model_error` |
| Provider rejects a native tool call (`tool_use_failed`) | Appends a corrective instruction and retries; `qwen3.8-27b` complies, `gpt-oss-20b` does not |
| Model tries to finish with arithmetic it did in its head | That `finish` is rejected once with a corrective Observation demanding a calculator call |
