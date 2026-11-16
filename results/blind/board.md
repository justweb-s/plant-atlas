# Blind test board: free search / RAG / Plant Atlas

48 questions of `data/cq/blind/` (never used to change the system), written from the documents alone. ✓ right · ✗ wrong · ? "I don't know" · a number = partly right.

| | Right | "I don't know" | Wrong | Mean |
|---|---|---|---|---|
| Free search (model + folder of documents) | 44/48 | 0 | 4 | 0.92 |
| RAG (passages by similarity) | 34/48 | 7 | 7 | 0.71 |
| Plant Atlas (fact store, reading on demand, judge) | 41/48 | 3 | 4 | 0.88 |
| Plant Atlas, panel (every reader answers, agreement or one judge) | 41/48 | 3 | 4 | 0.87 |

## By group of questions (right / total)

| | BLIND-LAW | BLIND-PLANT |
|---|---|---|
| Free search (model + folder of documents) | 24/24 | 20/24 |
| RAG (passages by similarity) | 18/24 | 16/24 |
| Plant Atlas (fact store, reading on demand, judge) | 22/24 | 19/24 |
| Plant Atlas, panel (every reader answers, agreement or one judge) | 21/24 | 20/24 |
