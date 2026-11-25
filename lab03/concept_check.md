# Lab 3: Percepts and Actions as Tools: Function Calling and MCP: Concept Check

Answer in your own words before the Wednesday session (independent work). Your answers feed Section 2 of your lab report (Concept and classical root).

## Q1. List one advantage and one disadvantage of native function calling compared with the Lab 2 text protocol.

**Advantage.** The API enforces the shape of the call. In Lab 2 the model had to
write `Action: ...` and `Action Input: ...` and any drift (both fields on one
line, a paragraph instead of an expression, an invented `Observation:`) became a
parser bug I had to paper over; here the tool name and the arguments arrive as a
validated `tool_calls` field, so there is no text to parse and the arguments are
checked against the JSON schema before my code runs.

**Disadvantage.** I hand control of the format to the provider. The call only
works if the model and the endpoint support tool calling — in Lab 2
`gpt-oss-20b` kept emitting native tool calls that Groq rejected with
`tool_use_failed` when no tools were supplied, and here the reverse can happen
when a model is poor at schemas. A text protocol, being just tokens, works with
any model; native calling also hides the model's reasoning, because the reply
comes back as an opaque `tool_calls` object rather than a readable transcript.

## Q2. In MCP, what is the difference between a tool and a resource? Give a pharmacy example of each.

A **tool** is a function the model may *call*: it has a name, a description and
an input schema, and it may change something. A **resource** is data the client
may *read* by URI: it is addressed, not executed, and it has no side effects.

In my server, `check_stock(item, strength)` and `record_sale(item, strength, qty)`
are tools — the model decides when to call them and record_sale changes the CSV.
A resource would be the stock list itself, for example
`pharmacy://stock/expiring-60-days` or `pharmacy://stock/amoxicillin-500mg`,
which a host could attach to the conversation as context without the model
choosing to call anything. (I have not implemented the resource; it is the
stretch task.)

## Q3. Why should `record_sale` check the quantity even though the system prompt already says "never oversell"?

Because the prompt is advice to a stochastic model, not an invariant of the
system. The model can pass `qty=500` for a medicine with 150 packs in stock
(and mine did, in question 6 of the six-question run), it can be confused by a
long conversation, and in a hostile case a user can talk it into trying. The
check also covers cases the prompt cannot see: stock changed by another
cashier between the model reading it and the sale being recorded, a negative or
non-integer quantity, an ambiguous item that matches two strengths, or an
expired batch. So `record_sale` re-validates every argument, takes a write lock
and re-reads the CSV before it writes, then refuses with a message the model can
relay. My run shows both sides: the sale of 3 packs reduced the row from 40 to
37, and the 500-pack attempt returned `Refused: oversale...` and left the file
unchanged. Enforcement belongs in the actuator, where the effect happens.

## Q4. Which messages in the worked example are percepts?

Only **message 3**, the `tool` message carrying the stock rows. It is the result
of running `check_stock` in the environment and it is the only thing the agent
learns by sensing. Message 1 is the user's question (input, not a percept),
message 2 is the model's decision (an action: the `tool_calls` field), and
message 4 is the model's reply, which is generated from the percept rather than
observed. In Lab 2 the same percept appeared as the `Observation:` line, which
my code wrote; the difference is only the protocol.
