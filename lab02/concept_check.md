# Lab 2: Architectures: A ReAct Agent From Scratch: Concept Check

Answer in your own words before the Wednesday session (independent work). Your answers feed Section 2 of your lab report (Concept and classical root).

## Q1. Classify a thermostat, a chess engine and a ReAct agent as reactive, deliberative or hybrid, with one reason each.

_Your answer:_

| System | Class | Reason |
|---|---|---|
| Thermostat | Reactive | One condition-action rule on the current percept ("if temperature < 18 °C, heat"). No model of the house, no goal beyond the set point, no memory of earlier readings. |
| Chess engine | Deliberative | It builds a model of future positions (a game tree) and evaluates them several plies ahead before moving. Slower, but it plans. |
| ReAct agent | Hybrid | It reacts to the newest Observation (a "no page found" changes the next step immediately) while its Thought lines plan across steps. It also keeps the conversation as beliefs, which makes it BDI-like. |

## Q2. In the trace above, which lines are percepts, and which are actions?

_Your answer:_

- **Percepts:** the user's question, and every `Observation:` line returned by the environment — `Observation: 1025`, then `Observation: 175`.
- **Actions:** every `Action:` line — `calculator` with input `4*185 + 3*95`, `calculator` with input `1200 - 1025`, and `finish` with the final answer.
- The `Thought:` lines are neither: they are internal deliberation, invisible to the environment. And the model does not actually act — it only *names* the tool; my Python code executes `calculator(...)`, so the real actuator is the code.

## Q3. Why do we pass `stop=["Observation:"]` when calling the model?

_Your answer:_

Because a model that has seen many ReAct examples will continue the pattern and write its own `Observation:` line. That is a hallucinated percept: the agent would then answer from a number that was never computed, and the trace would look correct while the arithmetic never ran. Stopping generation at the literal string `Observation:` guarantees that the only Observation lines in the conversation are the ones my code wrote after actually executing the tool. It forces the model to be a requester of the tool rather than a simulator of it.

## Q4. Map the trace above to the BDI terms belief, desire and intention.

_Your answer:_

- **Beliefs:** what the agent currently holds true — the question (GHS 1,200; 4 bags at 185; 3 gallons at 95) and the observations it has received (`1025`, then `175`). The beliefs live in the `messages` list and are updated on every tool result; the second Thought is only possible because "1025" is now believed.
- **Desire:** the goal — "tell the trader how much money is left". A desire is not yet a plan, just a preferred state of the world.
- **Intention:** the committed plan, "compute the total cost first, then subtract it from the budget". The first Thought states it and the first Action executes one step of it. After the observation the intention is continued (second calculator call) and then discharged by `Action: finish`, which is the BDI cycle: perceive → update beliefs → choose intentions → execute one step → repeat.
