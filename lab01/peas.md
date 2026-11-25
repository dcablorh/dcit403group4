# PEAS descriptions

PEAS is the checklist from the classical part of the course: before you write
any code, name the **P**erformance measure, the **E**nvironment, the **A**ctuators
and the **S**ensors. If a row is vague, the agent will be vague in the same place.
The last section lists the environment's *properties*, because those decide which
agent architecture is even sensible.

---

## 1. Self-checkout machine at a supermarket (concept-check Q1)

| | |
|---|---|
| **Performance measure** | Value of goods paid for before leaving; number of items correctly billed; false theft alarms per 100 customers; average checkout time per customer; customer abandonments; losses from mis-scanned items |
| **Environment** | The till lane: the goods and their barcodes, the bagging area and its weight scale, the customer, the card/mobile-money network, the store's price database, the attendant on duty |
| **Actuators** | Screen prompts and menus, the scanner laser, the speaker (beeps and spoken prompts), adding lines and prices to the bill, the card/mobile-money payment request, the printer, locking the lane / flashing the "wait for attendant" light |
| **Sensors** | Barcode scanner, weight scale under the bagging area, card reader and PIN pad, touch screen, coin/cash acceptor where fitted, the age-verification flag for restricted goods, the attendant's override key |

Reading the table back is the useful part. The performance measure contains
**two** things that pull against each other: "no unpaid item leaves" wants the
scale to shout at every discrepancy, "fast checkout" wants it to stay quiet.
That tension, not the hardware, is the design problem — and it is why a
supermarket still puts a human in the loop for restricted items.

## 2. Campus Info Bot (`campus_bot.py`)

| | |
|---|---|
| **Performance measure** | Correct answer rate on the questions in `tests.md`; answers that are *grounded* in `facts.md` (no invented rooms, prices or names); refusal when the facts do not cover the question; length of the answer (a student wants one line, not five); tokens per answer, because they cost money and time |
| **Environment** | A chat window with one student at a time, plus the facts block that ships with the program. No network, no database, no clock, no other agents |
| **Actuators** | Text sent back to the chat window (the only thing it can change) |
| **Sensors** | The text of the student's latest message, and the earlier turns still in the message list, and — read once at start-up — `facts.md` |

Two honest notes. First, the bot's *percepts* are only text; it cannot see the
campus, so a question like "is the queue at the Fees Office long?" has no
percept to answer from, only an instruction to refuse. Second, the facts block
is technically an actuator-free input, so it belongs on the sensor line: it is
knowledge the agent starts with, and it arrives through no action of its own.

## 3. Pharmacy stock agent (Lab 3, for continuity)

| | |
|---|---|
| **Performance measure** | Stock records that match the shelf; sales that are refused rather than wrongly recorded; no sale of an expired batch; number of agent steps per question; the pharmacist's trust in the numbers |
| **Environment** | `data/pharmacy_stock.csv`, the pharmacist asking questions, the customer at the counter. Partly open: the physical shelf is not observed, only the file |
| **Actuators** | `record_sale` (rewrites the CSV), the reply text; nothing else. All the write-side safety checks live here |
| **Sensors** | `check_stock`, `search_items`, `list_expiring` (all read-only), and the question text |

The reason this one is worth writing down is that the actuators are not
symmetric with the sensors: three of the four tools can only look, one can
change a file for good. Lab 1's bot has no such split (it can only talk), which
is exactly why its mistakes are cheap and Lab 3's are not.

---

## Environment properties

Same three agents, four questions each. "Chat" = the Campus Info Bot.

| Property | Self-checkout | Chat | Pharmacy agent |
|---|---|---|---|
| Fully observable? | No — the customer's pockets and the shelf are outside the sensors | No — only what the student types; the campus is unobserved | No — the file is observed, the shelf is not |
| Deterministic? | No — a barcode can be creased, a customer can move an item, the network can time out | No — the same question can get two different answers (measured: 3 runs at temperature 0.7 gave 3 different answers, `diagnostic/report.md` §3) | Mostly — the CSV is deterministic, the model's choice of tool is not |
| Episodic or sequential? | Sequential — an item scanned now decides whether the weight check later is satisfied | Sequential — turn 3 means nothing without turns 1 and 2 (`tests.md` question 9) | Sequential — the sale in q5 changes the stock the next question sees |
| Static or dynamic? | Dynamic — prices and stock change while the customer stands there | Static while a question is being answered; the facts block goes stale between *runs*, which is the trap in `tests.md` question 12 | Dynamic — another cashier can write the CSV between the check and the sale, which is why `record_sale` locks and re-reads |
| Discrete or continuous? | Mixed — barcodes and prices are discrete, weight and time are continuous | Discrete — tokens and words | Discrete — integer quantities and prices in pesewas |
| Single or multi-agent? | Multi-agent — customer, attendant, and other lanes competing for the attendant | Single-agent — one model, one user | Multi-agent — the pharmacist, the customer, and another cashier writing the same file |

### What the classification buys you

- Chat is **sequential + unobservable + non-deterministic**, so the only sane
  design is "keep the message list, and make the agent refuse rather than guess".
  That is what `campus_bot.py` does.
- The pharmacy agent has a **dynamic** environment with a second writer, so a
  check-then-write in `record_sale` without a lock would be a race. The lock in
  Lab 3 is not decoration; it is the classification turned into code.
- The self-checkout is **multi-agent with a shared resource** (the attendant),
  so its performance measure has to include how often it calls for help.
- None of the three is fully observable, so none of them may assume that "not
  mentioned" means "does not exist". That single line is why the bot is built to
  say *I do not have that information* instead of filling the gap.
