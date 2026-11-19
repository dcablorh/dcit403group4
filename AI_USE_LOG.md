# AI-Use Log

Add one row every time you use an AI tool for lab work (see Lab Manual Section 4).
Copy the rows for each lab into that lab's report.

| Date | Lab | Tool | What I asked | What I used | What I changed or checked |
|---|---|---|---|---|---|
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Read the Lab 2 manual and the report template and set up the `lab02` folder | A starting structure for `tools.py`, `react_agent.py`, `baseline.py`, `test_parser.py` | Read every file line by line; wrote the tolerant-parser fallback, the corrective-Observation branches and the trace labels myself; ran `test_parser.py` (10/10) and the direct tool checks |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | "Why does my regex miss the Action line when both fields are on one line?" | The suggestion to search `Action:` and `Action Input:` independently as a fallback | Wrote the fallback regex myself and proved with `test_parser.py` that the manual regex returns `(None, None)` while mine returns `('calculator', '1200 - 1025')` |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | "Why does the agent sometimes answer without calling the calculator?" | The explanation of `stop=["Observation:"]` and hallucinated percepts | Added `stop=` to the call myself; confirmed every `Observation:` line in the traces is written by my code |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Why two of my runs failed with an empty reply and a dropped connection | The note that a reasoning model can spend a small `max_tokens` budget on reasoning, and that provider connections drop | Added retry-with-backoff for 429/connection errors myself and re-ran the affected questions |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Why the calculator received a paragraph instead of an expression | The explanation that `DOTALL` let the tool input run into the next steps of the transcript | Bounded the input at the next `Thought:/Action:/Observation:` myself; added two regression tests (12/12) |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | Why Groq kept returning `tool_use_failed` | That gpt-oss-20b emits native tool calls even when no tools are supplied | Confirmed it on 7/7 questions, tried a corrective instruction, then switched the lab model to `qwen3.8-27b` and re-ran the baseline and the suite |
| 19 Nov 2026 | Lab 2 | free-pi (coding agent) | How to stop the model finishing with mental arithmetic | The suggestion to reject that `finish` in the loop, not only in the prompt | Added the guardrail myself; watched it fire and kept the trace |
