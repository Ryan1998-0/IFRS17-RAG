def build_general_answer_prompt(question: str) -> str:
    return f"""使用者問題無法在資料中搜尋到相關來源。

請改用一般常識回答，但必須明確標示這不是根據 knowledge base 的答案。
請使用繁體中文回答，不要使用簡體字。
回答應該簡潔，避免假裝知道公司內部規定。

輸出格式：
無法在資料中搜尋到，以下改用一般常識回答：
...

使用者問題：
{question}
"""
