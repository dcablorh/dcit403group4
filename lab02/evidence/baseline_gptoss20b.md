# Baseline: the model on its own, no tools

Model: `groq/openai/gpt-oss-20b`  Temperature: 0.7  Total tokens: 1206

| # | Question | Answer | Mark |
|---|---|---|---|
| 1 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | You'll spend 4 × 185 = GHS 740 on rice and 3 × 95 = GHS 285 on oil, for a total of GHS 1,025. That leaves you with GHS 175 from your original GHS 1,200. | arithmetic correct |
| 2 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | You'll spend 4 × GHS 185 = GHS 740 on rice and 3 × GHS 95 = GHS 285 on oil, totaling GHS 1,025. From GHS 1,200 that leaves you with GHS 175. | arithmetic correct |
| 3 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | You'll spend 740 GHS on rice and 285 GHS on oil, totaling 1,025 GHS. Subtracting that from your 1,200 GHS leaves you with 175 GHS. | arithmetic correct |
| 4 | What is the capital town of the Bono East Region of Ghana? | The capital town of Ghana's Bono East Region is **Techiman**. | check the fact by hand |
| 5 | In what year was the Ghana cedi redenominated (1 new cedi = 10,000 old cedis)? | The Ghana cedi was redenominated in 2007, when 1 new cedi replaced 10,000 old cedis. | check the fact by hand |

## What this shows

The budget question is asked three times. Count the rows marked
'arithmetic WRONG': that is the baseline error rate that the ReAct
loop has to beat. The two factual questions show how confident a
wrong answer can sound; mark them by hand using a reliable source.
