# Campus Facts — Accra Digital Campus (ADC)

The bot in `campus_bot.py` does not know anything about this campus except what
is inside the two blocks below. It never browses, never calls a tool and never
remembers anything from a previous run. That is the point of step 4: the facts
block is the agent's *built-in knowledge*, and the bot is only as right as the
block is current.

Everything here is **fictional** (invented campus, invented phone numbers) so it
can be committed. The two blocks are marked with HTML comments so `campus_bot.py`
can read them without guessing which text is which:

- `CURRENT` — version 2026-11-25, the block the bot uses by default.
- `STALE` — version 2025-01-15, kept on purpose so the bot can be run against
  an out-of-date block (`--facts-version stale`). Two offices moved and one
  price changed between the two versions; see the changelog at the end.

Term: Semester 1 of the 2026/27 academic year.

<!-- BEGIN CURRENT -->
## Offices and where they are

| Office | Location | Hours | Phone |
|---|---|---|---|
| Examinations Office | Block C, Room C12 | Mon–Fri 08:30–16:30 | 030 200 0112 |
| Fees Office (cashier) | Block A, Ground floor, Room A04 | Mon–Fri 09:00–15:30 | 030 200 0100 |
| ICT Help Desk | Block B, Room B07 | Mon–Fri 08:00–17:00, Sat 09:00–13:00 | 030 200 0145 |
| Student Affairs | Block C, Room C03 | Mon–Fri 08:30–16:00 | 030 200 0120 |
| Registrar | Block A, Room A11 | Mon–Fri 09:00–16:00 | 030 200 0105 |
| Transcripts and Certificates | Block A, Room A12 | Mon–Fri 09:30–15:00 | 030 200 0106 |
| Department of Computer Science office | Block B, Room B11 | Mon–Fri 08:30–16:30 | 030 200 0150 |
| Health Centre | Block E, Room E01 | 24 hours; walk-in clinic 08:00–20:00 | 030 200 0199 |
| Security post (main gate) | Main gate, north entrance | 24 hours | 030 200 0190 |
| Library | Block D, floors 1–3 | Mon–Sat 07:30–22:00, Sun 14:00–20:00 | 030 200 0170 |

## Fees (Semester 1, 2026/27)

- Regular undergraduate, Ghanaian: GHS 2,450.00 per semester.
- Regular undergraduate, international: GHS 5,100.00 per semester.
- Postgraduate (MSc/MPhil): GHS 3,900.00 per semester.
- Late registration surcharge: GHS 150.00, charged after the registration deadline.
- Re-sit fee: GHS 120.00 per paper.
- Payment channels: the Fees Office cashier, any ADC partner bank branch
  (quote your student ID), or mobile money to the campus short code 1448 with
  your student ID as the reference. Card payment is **not** accepted.
- Fee deadline for Semester 1: 30 November 2026. After that date a GHS 150.00
  late surcharge applies.

## Key dates, Semester 1 2026/27

- Registration deadline (all students): 18 September 2026.
- Mid-semester quizzes: 19–23 October 2026.
- Examination timetable published: 27 November 2026, on the notice board and
  the student portal.
- End-of-semester examinations: 7–18 December 2026.
- Results published: 16 January 2027.
- Semester 2 fees deadline: 26 February 2027.
- Next graduation ceremony: 20 March 2027.

## Student services

- **Wi-Fi**: SSID `ADC-STUDENT`, password `adc2026`. Use your student email to
  sign in to the captive portal. Guests use `ADC-GUEST` (no password, 2 hours).
- **Printing and photocopying**: Library, ground floor, Room D-G2. GHS 0.50 per
  black-and-white page, GHS 1.50 per colour page. Pay with campus credit loaded
  at the library counter; cash is not accepted at the printer.
- **Student ID cards**: made at Student Affairs (Block C, Room C03). Bring your
  admission letter and one passport photograph. First card is free; a
  replacement costs GHS 40.00 and takes three working days.
- **Counselling**: Student Affairs, by appointment, free and confidential.
- **Shuttle**: main gate to the city terminus every 30 minutes from 06:30 to
  20:30, GHS 5.00 cash.
- **Lost property**: Security post, main gate.
- **Cafeteria**: Block F, 07:00–19:00, Monday to Saturday. Closed on Sundays.
- **Hostel enquiries**: Student Affairs, Block C, Room C03. Hostel places for
  continuing students are allocated in August.
- **Examination complaints and remark requests**: Examinations Office, Block C,
  Room C12, within 10 working days of the result being published.
- **Industrial attachment letters**: Department of Computer Science office,
  Block B, Room B11.
- **Official transcript request**: Transcripts and Certificates, Block A,
  Room A12. Bring the application form, your student ID and GHS 100.00. Ready in
  five working days.

## What this campus does NOT publish

The facts block contains no names of staff or students, no Vice-Chancellor, no
hall of residence assignment rules, no course outlines and no exam questions.
Questions about those cannot be answered from the block.
<!-- END CURRENT -->

<!-- BEGIN STALE -->
## Offices and where they are

| Office | Location | Hours | Phone |
|---|---|---|---|
| Examinations Office | Block C, Room C12 | Mon–Fri 08:30–16:30 | 030 200 0112 |
| Fees Office (cashier) | Block A, Ground floor, Room A04 | Mon–Fri 09:00–15:30 | 030 200 0100 |
| ICT Help Desk | Block B, Room B02 | Mon–Fri 08:00–17:00, Sat 09:00–13:00 | 030 200 0145 |
| Student Affairs | Block C, Room C03 | Mon–Fri 08:30–16:00 | 030 200 0120 |
| Registrar | Block A, Room A11 | Mon–Fri 09:00–16:00 | 030 200 0105 |
| Transcripts and Certificates | Block A, Room A03 | Mon–Fri 09:30–15:00 | 030 200 0106 |
| Department of Computer Science office | Block B, Room B11 | Mon–Fri 08:30–16:30 | 030 200 0150 |
| Health Centre | Block E, Room E01 | 24 hours; walk-in clinic 08:00–20:00 | 030 200 0199 |
| Security post (main gate) | Main gate, north entrance | 24 hours | 030 200 0190 |
| Library | Block D, floors 1–3 | Mon–Sat 07:30–22:00, Sun 14:00–20:00 | 030 200 0170 |

## Fees (Semester 1, 2025/26)

- Regular undergraduate, Ghanaian: GHS 2,100.00 per semester.
- Regular undergraduate, international: GHS 4,600.00 per semester.
- Postgraduate (MSc/MPhil): GHS 3,500.00 per semester.
- Late registration surcharge: GHS 120.00, charged after the registration deadline.
- Re-sit fee: GHS 120.00 per paper.
- Payment channels: the Fees Office cashier only.
- Fee deadline for Semester 1: 30 November 2025.

## Student services

- **Wi-Fi**: SSID `ADC-STUDENT`, password `adc2025`.
- **Printing and photocopying**: Library, ground floor, Room D-G2. GHS 0.40 per
  page, paid in cash at the counter.
- **Student ID cards**: made at Student Affairs (Block C, Room C03).
- **Official transcript request**: Transcripts and Certificates, Block A,
  Room A03.
<!-- END STALE -->

## Changelog

| Version | Date | What changed |
|---|---|---|
| 2025-01-15 | January 2025 | The block as it was in the 2025/26 academic year: transcripts in **A03**, ICT Help Desk in **B02**, fees GHS 2,100.00, Wi-Fi password `adc2025`, printing paid in cash. |
| 2026-11-25 | November 2026 | Transcripts moved to **A12**; ICT Help Desk moved to **B07**; Ghanaian undergraduate fees raised to GHS 2,450.00; Wi-Fi password now `adc2026`; printing now needs campus credit; mobile-money and bank payment added, card still not accepted; new key dates for Semester 1 2026/27. |

The old block is kept because Lab 1 asks whether a wrong answer caused by an
out-of-date facts block means the agent was irrational. Running the same question
against the two blocks is the experiment that answers it.
