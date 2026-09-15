#!/usr/bin/env python3
"""
Multi-AI Workflow Pipeline CLI
Layer 1 (Ollama) による高速整形と Layer 4 (Claude API) による批判的レビューを
コマンドラインから直結・自動実行するためのオーケストレーションツールです。
標準ライブラリのみで動作します（追加pip不要）。
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error

def query_ollama(prompt: str, text: str, model: str = "qwen-processor", host: str = "http://127.0.0.1:11434") -> str:
    """Layer 1: Ollama にテキスト加工を依頼する"""
    url = f"{host.rstrip('/')}/api/generate"
    combined_prompt = f"{prompt}\n\n---\n{text}"
    payload = {
        "model": model,
        "prompt": combined_prompt,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("response", "").strip()
    except urllib.error.URLError as e:
        print(f"[Error] Ollama への接続に失敗しました ({url}): {e}", file=sys.stderr)
        print("  ※ Ollama が起動しているか、ポート11434で待機しているか確認してください。", file=sys.stderr)
        sys.exit(1)

def query_claude(prompt: str, text: str, model: str = "claude-3-5-sonnet-latest") -> str:
    """Layer 4: Claude API に批判的レビューを依頼する"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[Error] 環境変数 ANTHROPIC_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)

    url = "https://api.anthropic.com/v1/messages"
    system_prompt = (
        "あなたは極めて厳格で客観的な監査役・シニアレビュアーです。\n"
        "提出されたテキストの「潜在的リスク」「論理の欠陥」「誇大表現」「抜け漏れ」を批判的に検証してください。\n"
        "挨拶は不要で、[Critical / Major / Minor] の重要度順に箇条書きで具体的に指摘してください。"
    )
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}\n\n```\n{text}\n```"
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            blocks = res_json.get("content", [])
            texts = [b["text"] for b in blocks if b.get("type") == "text"]
            return "\n".join(texts).strip()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[Error] Claude API エラー ({e.code}): {err_body}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Multi-AI Workflow: ローカル加工(Ollama)とレビュー(Claude)を繋ぐCLIツール"
    )
    parser.add_argument("file", nargs="?", help="入力ファイルパス（省略時は標準入力）")
    parser.add_argument("--mode", choices=["clean", "review", "chain"], default="chain",
                        help="clean: Ollamaで整形のみ / review: Claudeでレビューのみ / chain: 整形後にレビュー (デフォルト)")
    parser.add_argument("--clean-prompt", default="以下のテキストからノイズを排除し、重要事項のみを箇条書きで簡潔に整理してください。",
                        help="Layer 1 (Ollama) に渡す指示")
    parser.add_argument("--review-prompt", default="以下の内容を批判的にレビューし、リスクや論理の穴を指摘してください。",
                        help="Layer 4 (Claude) に渡す指示")
    parser.add_argument("--ollama-model", default="qwen-processor", help="Ollamaモデル名 (default: qwen-processor)")
    parser.add_argument("--claude-model", default="claude-3-5-sonnet-latest", help="Claudeモデル名")
    parser.add_argument("--output", "-o", help="結果の保存先ファイルパス（省略時は標準出力）")

    args = parser.parse_args()

    # 入力の取得
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                raw_input = f.read()
        except Exception as e:
            print(f"[Error] ファイル読み込み失敗: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if sys.stdin.isatty():
            print("Usage: python pipeline.py <file> または cat <file> | python pipeline.py")
            sys.exit(0)
        raw_input = sys.stdin.read()

    if not raw_input.strip():
        print("[Error] 入力が空です。", file=sys.stderr)
        sys.exit(1)

    result = ""
    if args.mode == "clean":
        print(f"[*] Layer 1 (Ollama: {args.ollama_model}) でデータ整形中...", file=sys.stderr)
        result = query_ollama(args.clean_prompt, raw_input, model=args.ollama_model)
    elif args.mode == "review":
        print(f"[*] Layer 4 (Claude: {args.claude_model}) でレビュー中...", file=sys.stderr)
        result = query_claude(args.review_prompt, raw_input, model=args.claude_model)
    elif args.mode == "chain":
        print(f"[*] Step 1: Layer 1 (Ollama: {args.ollama_model}) でデータ整形中...", file=sys.stderr)
        cleaned = query_ollama(args.clean_prompt, raw_input, model=args.ollama_model)
        print("[*] Step 2: Layer 4 (Claude API) へ整形データを引き渡しレビュー中...", file=sys.stderr)
        result = query_claude(args.review_prompt, cleaned, model=args.claude_model)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result + "\n")
        print(f"[+] 結果を {args.output} に保存しました。", file=sys.stderr)
    else:
        print(result)

if __name__ == "__main__":
    main()