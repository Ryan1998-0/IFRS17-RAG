import argparse
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from rag_demo.config import RagConfig
from rag_demo.knowledge_base import active_knowledge_base
from rag_demo.query import answer_question_v2


DEFAULT_MODEL = "ollama:qwen2.5:7b"


def render_home(
    answer_html: str = "",
    question: str = "",
    model: str = DEFAULT_MODEL,
    top_k: int = None,
) -> str:
    config = RagConfig.from_env()
    knowledge_base = active_knowledge_base()
    top_k = top_k or config.top_k
    escaped_question = html.escape(question)
    escaped_model = html.escape(model)
    escaped_profile = html.escape(knowledge_base.name)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RAG Agent Demo</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #202124;
      --muted: #5f6368;
      --line: #d8dee4;
      --panel: #ffffff;
      --page: #f6f8fa;
      --accent: #0f766e;
      --accent-2: #b42318;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--page);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }}
    .wrap {{
      width: min(1080px, calc(100vw - 32px));
      margin: 0 auto;
    }}
    .top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 0;
    }}
    h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }}
    .badge {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 10px;
      color: var(--muted);
      background: #fafafa;
      font-size: 13px;
      white-space: nowrap;
    }}
    main {{
      padding: 28px 0 40px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(280px, 380px) 1fr;
      gap: 20px;
      align-items: start;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    label {{
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      color: var(--muted);
    }}
    textarea {{
      width: 100%;
      min-height: 132px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: inherit;
      color: var(--ink);
      background: #ffffff;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      font: inherit;
      color: var(--ink);
      background: #ffffff;
    }}
    input:focus, select:focus {{
      outline: 2px solid rgba(15, 118, 110, 0.22);
      border-color: var(--accent);
    }}
    .field {{
      margin-top: 12px;
    }}
    textarea:focus {{
      outline: 2px solid rgba(15, 118, 110, 0.22);
      border-color: var(--accent);
    }}
    button {{
      width: 100%;
      margin-top: 12px;
      border: 0;
      border-radius: 6px;
      padding: 11px 14px;
      background: var(--accent);
      color: #ffffff;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 46px;
    }}
    button[disabled] {{
      cursor: wait;
      opacity: 0.82;
    }}
    .submit-spinner {{
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.45);
      border-top-color: #ffffff;
      border-radius: 50%;
      display: none;
      flex: 0 0 auto;
    }}
    .is-loading .submit-spinner {{
      display: inline-block;
      animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
    .samples {{
      display: grid;
      gap: 8px;
      margin-top: 14px;
    }}
    .sample {{
      display: block;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      background: #fafafa;
      color: var(--ink);
      text-align: left;
      font: inherit;
      cursor: pointer;
    }}
    pre {{
      min-height: 320px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 14px;
      line-height: 1.7;
    }}
    .empty {{
      color: var(--muted);
    }}
    .warn {{
      margin-top: 12px;
      color: var(--accent-2);
      font-size: 13px;
    }}
    @media (max-width: 760px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .top {{ align-items: flex-start; flex-direction: column; }}
      .badge {{ white-space: normal; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap top">
      <h1>RAG Agent Demo</h1>
      <div class="badge">Knowledge Base: {escaped_profile} / Model: {escaped_model}</div>
    </div>
  </header>
  <main class="wrap">
    <div class="grid">
      <section>
        <h2>提問</h2>
        <form method="post" action="/ask" id="ask-form">
          <label for="question">問題</label>
          <textarea id="question" name="question" autofocus>{escaped_question}</textarea>
          <div class="field">
            <label for="model">模型</label>
            <input id="model" name="model" list="model-options" value="{escaped_model}">
            <datalist id="model-options">
              <option value="ollama:qwen2.5:7b">
              <option value="ollama:llama3.1:8b">
              <option value="ollama:gemma3:4b">
              <option value="openai:gpt-5.5">
              <option value="anthropic:claude-opus-4-1-20250805">
            </datalist>
          </div>
          <div class="field">
            <label for="top_k">Context chunks top_k</label>
            <input id="top_k" name="top_k" type="number" min="1" max="10" value="{top_k}">
          </div>
          <button type="submit" id="submit-button" data-loading-text="處理中">
            <span class="submit-spinner" aria-hidden="true"></span>
            <span class="submit-label">送出問題</span>
          </button>
        </form>
        <div class="samples">
          <button class="sample" type="button">IFRS17 的目的是什麼？</button>
          <button class="sample" type="button">IFRS17 適用哪些合約？</button>
          <button class="sample" type="button">舊制 IFRS 4 和新制 IFRS 17 差在哪？</button>
        </div>
        <div class="warn">本機模型可能需要幾秒鐘；API 模型需要設定對應 API key。</div>
      </section>
      <section>
        <h2>回答</h2>
        <pre>{answer_html or '<span class="empty">尚未送出問題。</span>'}</pre>
      </section>
    </div>
  </main>
  <script>
    for (const sample of document.querySelectorAll(".sample")) {{
      sample.addEventListener("click", () => {{
        document.querySelector("#question").value = sample.textContent;
      }});
    }}
    const askForm = document.querySelector("#ask-form");
    const submitButton = document.querySelector("#submit-button");
    if (askForm && submitButton) {{
      askForm.addEventListener("submit", () => {{
        const label = submitButton.querySelector(".submit-label");
        submitButton.classList.add("is-loading");
        submitButton.disabled = true;
        submitButton.setAttribute("aria-busy", "true");
        if (label) {{
          label.textContent = submitButton.dataset.loadingText || "處理中";
        }}
      }});
    }}
  </script>
</body>
</html>"""


class RagRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if not is_home_path(self.path):
            self._send_not_found()
            return
        self._send_html(render_home())

    def do_POST(self) -> None:
        if self.path != "/ask":
            self._send_not_found()
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        question = parse_qs(body).get("question", [""])[0].strip()
        model = parse_qs(body).get("model", [DEFAULT_MODEL])[0].strip() or DEFAULT_MODEL
        top_k = _parse_int(parse_qs(body).get("top_k", [str(RagConfig.from_env().top_k)])[0], RagConfig.from_env().top_k)

        if question:
            answer = answer_question_v2(question, model=model, top_k=top_k)
            answer_html = html.escape(answer)
        else:
            answer_html = '<span class="empty">請先輸入問題。</span>'

        self._send_html(render_home(answer_html=answer_html, question=question, model=model, top_k=top_k))

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, content: str) -> None:
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_not_found(self) -> None:
        self.send_response(404)
        self.end_headers()


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), RagRequestHandler)
    print(f"RAG demo running at http://{host}:{port}")
    server.serve_forever()


def is_home_path(path: str) -> bool:
    return path in {"/", "/ask"}


def _parse_int(value: str, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local RAG web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
