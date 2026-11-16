# Blind test board: free search / RAG / Plant Atlas

40 questions of `data/cq/blind/` (never used to change the system), written from the documents alone. ✓ right · ✗ wrong · ? "I don't know" · a number = partly right.

| | Right | Wrongly said "I don't know" | Wrong answer | Mean |
|---|---|---|---|---|
| Free search (model + folder of documents) | 36/40 | 0 | 4 | 0.91 |
| Fact store alone, no search | 14/40 | 23 | 3 | 0.36 |
| Fact store alone, after learning from the development questions | 17/40 | 19 | 4 | 0.45 |
| Plant Atlas (search agent handed the fact store; rules in code; quote check) | 39/40 | 1 | 0 | 0.97 |
| Plant Atlas, after learning from the development questions | 40/40 | 0 | 0 | 1.00 |

## By group of questions (right / total)

| | other passages | passages the development questions cite |
|---|---|---|
| Free search (model + folder of documents) | 19/20 | 17/20 |
| Fact store alone, no search | 9/20 | 5/20 |
| Fact store alone, after learning from the development questions | 10/20 | 7/20 |
| Plant Atlas (search agent handed the fact store; rules in code; quote check) | 19/20 | 20/20 |
| Plant Atlas, after learning from the development questions | 20/20 | 20/20 |
