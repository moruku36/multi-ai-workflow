# タスク別ルーティングガイド

「どのAI / モデルに依頼するか」を即決するためのガイドです。

> **Model snapshot: 2026-09-23**
>
> モデル更新時は、モデル名そのものより「役割」を維持して置き換えます。

---

## 1. 現在の標準ルーティング

| 作業 | 第一候補 | 代替 / エスカレーション |
|---|---|---|
| 要件整理・設計・方針決め | ChatGPT / GPT-5.6 Sol | Claude Opus 5.5 |
| 技術調査・比較・レポート | ChatGPT | Claude Opus 5.5 |
| 文章・資料作成 | ChatGPT | Claude Opus 5.5 |
| PoC・モック・プロジェクト雛形 | Antigravity / Gemini 3.8 Flash | Claude Sonnet 5 |
| 初期実装・大量ファイル生成 | Antigravity / Gemini 3.8 Flash | GPT-6 Luna |
| 小規模コード修正 | Codex / GPT-6 Luna | Gemini 3.8 Flash |
| 通常の機能実装 | Codex / GPT-6 Sol | Claude Sonnet 5 |
| 難しい実装・デバッグ | Codex / GPT-6 Sol | Claude Opus 5.5 |
| 大規模migration・長期agentic coding | Claude Code / Opus 5.5 | Codex / GPT-6 Sol |
| コードベース横断レビュー | Claude Code / Opus 5.5 | Codex / GPT-6 Sol |
| レビュー指摘の単純修正 | GPT-6 Luna | Gemini 3.8 Flash |
| Sol / Opusでも解けない難問 | GPT-6 Astra | Opus 5.5 高effort |
| 機密ログ・社外秘データの整形 | Ollama / Qwen | - |

---

## 2. 開発フロー

```mermaid
flowchart TD
    P["ChatGPT<br/>要件・設計・受入条件"] --> G["Gemini 3.8 Flash / Antigravity<br/>PoC・モック・初期実装"]
    G --> C["Codex GPT-6 Sol<br/>本実装・テスト・品質向上"]
    C --> R["Claude Code Opus 5.5<br/>独立レビュー"]
    R --> F["Codex GPT-6 Luna / Sol<br/>指摘修正"]
    F --> D["ChatGPT<br/>文書化・最終整理"]

    C -->|Codex上限| S["Claude Code Sonnet 5<br/>通常実装を継続"]
    S --> R
```

### 開始モデルの決め方

- **仕様がまだ曖昧** → ChatGPT
- **仕様は決まっていて、まず動くものが欲しい** → Gemini 3.8 Flash
- **既存コードへ本番品質で変更したい** → GPT-6 Sol
- **変更が小さい・定型的** → GPT-6 Luna
- **長く複雑なコードベース全体を扱う** → Opus 5.5
- **外部視点でレビューしたい** → 実装担当と別ベンダーのモデル

---

## 3. エスカレーション

### Codex内

```text
GPT-6 Luna
  ↓ 設計判断・複雑なデバッグが必要
GPT-6 Sol
  ↓ Solでも解けない / 極めて重要
GPT-6 Astra
```

### Claude Code内

```text
Claude Sonnet 5
  ↓ 長期作業・難バグ・大規模レビュー
Claude Opus 5.5
```

### ベンダー横断

- Codexで詰まった → Claude Codeへセカンドオピニオン
- Claude Codeで詰まった → Codexへセカンドオピニオン
- どちらも詰まった → GPT-6 Astra
- 単純な物量不足 → Antigravity / Gemini 3.8 Flashへ戻す

---

## 4. 利用枠を守るルール

1. **初期モックをSol / Opusから始めない**
   - まずGemini 3.8 Flashで土台を作る。
2. **Lunaで済む変更をSolに投げない**
   - typo、README、テスト追加、単純修正はLuna。
3. **レビューの粒度を指定する**
   - Claude Codeには「Critical / Majorのみ」など、重要度を限定する。
4. **実装とレビューを別系列モデルにする**
   - Codex → Claude Code、またはClaude Code → Codex。
5. **同じ実装を複数モデルへゼロから二重発注しない**
   - 比較実験を除き、利用枠の無駄になるため避ける。

---

## 5. ChatGPTの位置づけ

ChatGPTは「コードを書くためだけの場所」ではなく、全体の司令塔です。

- 要件・制約の整理
- アーキテクチャ検討
- 最新情報の調査
- Codex / Claude Code / Antigravityへ渡すMaster Prompt作成
- レビュー結果の統合
- README、レポート、資料、構成図の文章設計

実際のリポジトリ操作は、原則としてCodex / Claude Code / Antigravityへ渡します。

---

## 6. ローカルモデル

Ollama / Qwenは開発能力競争には参加させず、**ローカルで処理する意味がある仕事**へ限定します。

- 機密ログの抽出
- 社外秘データの分類
- 大量テキストの前処理
- 外部AIへ送る前の匿名化・整形
