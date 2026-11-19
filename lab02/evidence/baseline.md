# Baseline: the model on its own, no tools

Model: `groq/qwen/qwen3.8-27b`  Temperature: 0.7  Total tokens: 463

| # | Question | Answer | Mark |
|---|---|---|---|
| 1 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | You will have GHS 15 left after purchasing the rice and oil. | arithmetic WRONG |
| 2 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | You will have GHS 205 left after purchasing the 4 bags of rice and 3 gallons of oil. | arithmetic WRONG |
| 3 | I have GHS 1,200. I want 4 bags of rice at GHS 185 each and 3 gallons of oil at GHS 95 each. How much will I have left? | Your total expenses for the rice and oil amount to GHS 1,135, leaving you with GHS 65. | arithmetic WRONG |
| 4 | What is the capital town of the Bono East Region of Ghana? | The capital town of the Bono East Region of Ghana is Kintampo. | check the fact by hand |
| 5 | In what year was the Ghana cedi redenominated (1 new cedi = 10,000 old cedis)? | The Ghana cedi was redenominated in 2007, with an exchange rate of 1 new cedi to 10,000 old cedis. | check the fact by hand |

## What this shows

The budget question is asked three times. Count the rows marked
'arithmetic WRONG': that is the baseline error rate that the ReAct
loop has to beat. The two factual questions show how confident a
wrong answer can sound; mark them by hand using a reliable source.
