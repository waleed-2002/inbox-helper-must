# inbox-helper-must

Local hiring inbox backend for CSV import, Groq triage, draft review, and approved CSV export.

```sh
uv venv --python 3.11 .venv
uv pip sync --python .venv/bin/python requirements.txt
env -u GROQ_LOG .venv/bin/python -m uvicorn hiring_inbox.api:app --host 127.0.0.1 --workers 1
```

Open the [local API reference](http://127.0.0.1:8000/docs). The service is intended for one trusted local operator. See the [Milestone 3 directive](docs/directive-v3.md) for CSV format, Groq configuration, review behavior, and test commands.
