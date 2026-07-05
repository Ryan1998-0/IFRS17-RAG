# IFRS17 Agentic RAG Demo

Static GitHub Pages demo for the IFRS17 profile.

- No paid LLM API.
- The static page still works without any backend.
- Primary ranking uses browser-side lexical retrieval and conservative alias expansion.
- Graph results are shown as an exploratory sidecar because the IFRS17 graph benchmark showed hub-entity pollution.

Open locally:

```bash
python3 -m http.server 4173 --directory docs
```

Then visit:

```text
http://127.0.0.1:4173/ifrs17-demo/
```

## Public demo

```text
https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/
```

This repository includes only the static browser-side demo. The local Ollama Agent backend is intentionally kept outside this public demo project.
