#!/usr/bin/env python3
"""
Level 4: Claude API Review CLI
標準入力または指定ファイルの内容を、Anthropic Claude API に渡して批判的セカンドオピニオンを取得します。
依存パッケージ不要（Python標準ライブラリのみで動作）。
"""

import sys
import os
import json
import urllib.request
import urllib.error

SYSTEM_PROMPT = """あなたは極めて厳格で客観的なシニアアーキテクト兼セキュリティレビュアーです。
提出されたコード・設計書の「潜在的欠陥」「境界値の漏れ」「セキュリティリスク」「ボトルネック」を批判的にレビューしてください。
挨拶は不要で、[Critical / Major / Minor] の重要度順に箇条書きで具体的に指摘してください。"""

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY 環境変数が設定されていません。", file=sys.stderr)
        print("export ANTHROPIC_API_KEY='your-key' を実行してください。", file=sys.stderr)
        sys.exit(1)

    model = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-latest")

    # 入力の取得（引数ファイル または 標準入力）
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {filepath}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("Usage: python3 review_cli.py <filename> または cat <file> | python3 review_cli.py")
            sys.exit(0)
        content = sys.stdin.read()

    if not content.strip():
        print("Error: 入力内容が空です。", file=sys.stderr)
        sys.exit(1)

    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"以下のコード/ドキュメントを批判的にレビューしてください:\n\n```\n{content}\n```"
            }
        ]
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        method="POST"
    )

    try:
        print(f"--- Sending request to Claude ({model}) for review... ---", file=sys.stderr)
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            for block in res_data.get("content", []):
                if block.get("type") == "text":
                    print(block.get("text", ""))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"API Error ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
