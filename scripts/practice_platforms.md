# SQL & Python Practice Platforms

> **Note:** Use these for daily practice alongside NotebookLM study. **Don't add as sources.** They are interactive query/coding tools, not reading material — NotebookLM can't usefully index them.

## SQL — problem sets & challenges

- [LeetCode — Database](https://leetcode.com/problemset/database/) — classic SQL interview problems, easy → hard
- [HackerRank — SQL](https://www.hackerrank.com/domains/sql) — basic to advanced SQL challenges
- [DataLemur](https://datalemur.com/) — SQL interview questions from FAANG + analytics companies
- [StrataScratch](https://www.stratascratch.com/) — real interview SQL questions from Amazon, Google, Meta, etc.
- [Namaste SQL — Coding Problems](https://www.namastesql.com/coding-problems) — Ankit Bansal's curated SQL problem set
- [DataFord](https://www.dataford.io/) — Shubham's data engineering practice platform

## SQL — tutorials & learning

- [SQLZoo](https://sqlzoo.net/) — interactive SQL tutorial with inline query runner
- [DataCamp — SQL track](https://www.datacamp.com/courses/tech:sql) — guided SQL courses
- [Kaggle Learn — SQL](https://www.kaggle.com/learn/intro-to-sql) — intro + advanced SQL micro-courses on BigQuery

## SQL — query playgrounds (online execution)

- [SQL Fiddle](http://sqlfiddle.com/) — multi-DB online sandbox (MySQL, PostgreSQL, SQLite, MS SQL, Oracle)
- [DB-Fiddle](https://www.db-fiddle.com/) — modern fork; PostgreSQL / MySQL / SQLite with schema + query share links

## SQL — gamified / interactive

- [SQL Murder Mystery](https://mystery.knightlab.com/) — solve a fictional murder by writing SQL queries (Knight Lab, Northwestern)

## Statistics & Python practice

- [HackerRank — 10 Days of Statistics](https://www.hackerrank.com/domains/tutorials/10-days-of-statistics) — bite-sized stats problems with auto-graded answers

## Why these are excluded from NotebookLM

NotebookLM indexes **text content** for grounded Q&A. Interactive platforms either:
- Require auth / login walls → indexing fails
- Render content via JS at runtime → scraper sees an empty shell
- Are tools (query runners), not reading material → no useful text to summarize

For reading material (concept explanations, tutorials, articles), use [scripts/sources.yaml](sources.yaml) → `bulk_load.py`.

## Daily-practice suggestion

| Day | Platform | Focus |
|---|---|---|
| Mon | LeetCode Database | 2 medium problems |
| Tue | StrataScratch | 1 real interview question |
| Wed | HackerRank SQL | Window functions / advanced |
| Thu | DataLemur | FAANG-style question |
| Fri | Namaste SQL / DataFord | Domain-specific (analytics, DE) |
| Sat | DB-Fiddle | Build + share a schema for a concept you reviewed |
| Sun | Kaggle SQL | One micro-course lesson |
