# statsy

A small AI agent that answers questions about a CSV file (`grades.csv`) by calling tools. It runs fully on your own computer with a local model (Ollama), so no API key is needed.

The model decides when to use a tool. The code runs the tool and gives the result back to the model, which then writes the answer.

## Tools

| Tool | What it does |
|---|---|
| `load_csv_summary` | Returns the column names, the row count, and which columns are numeric |
| `calculate_stat` | Returns the mean, median, standard deviation (sample), min or max of a numeric column |

Both tools use only Python's built-in `csv` and `statistics` modules (no pandas).

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/download), installed and running
- The model: `ollama pull llama3.2:3b`

## Setup

```bash
git clone https://github.com/FatimaAl22/statsy.git
cd statsy
python -m venv venv
source venv/Scripts/activate      # Git Bash on Windows
# venv\Scripts\Activate.ps1       # PowerShell on Windows
pip install -r requirements.txt
```

## Run

Web chat page:

```bash
streamlit run app.py
```

It opens at http://localhost:8501.

Terminal chat:

```bash
python agent.py
```

Type `quit` to exit. The first reply is slow because the model has to load into memory.

## Example questions

- What columns are in my data?
- How many rows are there?
- What is the average math score?
- What is the median of science?
- What is the maximum of hours_studied?

## Project files

| File | Purpose |
|---|---|
| `agent.py` | The agent loop: calls the model, runs tool requests, handles errors |
| `tools.py` | The two tool functions and their descriptions for the model |
| `app.py` | The Streamlit chat page |
| `grades.csv` | Sample data (40 students: math, science, hours studied) |
| `requirements.txt` | Python packages |

## Known limits

- It uses a small local model (`llama3.2:3b`) on CPU, so replies can be slow.
- Small models make mistakes. It may guess a wrong column name (it usually retries and fixes it), call a data tool for a general question, or invent an argument. The code catches these errors and sends a clear message back to the model.
- The system message and tool descriptions mention `grades.csv`, so it is built for this file. Supporting any uploaded CSV is a planned improvement.
- A larger model or an API model would call tools more reliably. The code uses an OpenAI-style client, so switching means changing the URL, key and model name in `agent.py`.
