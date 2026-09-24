# レシピ 04: コード実装・リファクタリング・独立レビュー

現在の標準開発フローを、そのまま使える形にしたレシピです。

---

## ワークフロー

```mermaid
flowchart LR
    A[要件] --> B[ChatGPT<br/>設計・受入条件]
    B --> C[Antigravity / Gemini 3.8 Flash<br/>PoC・初期実装]
    C --> D[Codex / GPT-6 Luna Medium<br/>本実装・テスト]
    D --> E[Claude Code / Opus 5.5 Medium<br/>独立レビュー]
    E --> F[Codex / Luna or Sol<br/>指摘修正]
```

---

## Step 1: ChatGPTで設計を確定

```text
以下の変更について、実装前に仕様を整理してください。

出力:
- 目的
- 変更範囲
- 非対象
- アーキテクチャ上の方針
- セキュリティ上の制約
- 受入条件
- 必須テスト
```

## Step 2: Gemini 3.8 Flash / Antigravityで初期実装

```text
以下の確定仕様に従って、まず動く実装を作成してください。
対象ファイルを確認し、実装、テスト追加、test/lint/buildまで実行してください。

過剰設計は避け、仕様外の大きな変更が必要な場合は勝手に進めず論点を残してください。

--- 確定仕様 ---
[ChatGPTの仕様]
```

## Step 3: Codex GPT-6 Luna / Mediumで本番品質へ

```text
Antigravityで作成した初期実装をレビューし、本番品質へ仕上げてください。

- 仕様との乖離
- エラー処理
- 境界値
- テスト品質
- 保守性
- 不要な複雑性

を確認し、必要な修正を行ってtest/lint/buildを実行してください。
```

通常はGPT-6 Luna / Mediumを使います。単純な変更だけLowへ下げ、Lunaで設計判断やデバッグが不足した場合のみGPT-6 Sol / Mediumへ上げます。

## Step 4: Claude Code Opus 5.5 / Mediumで独立レビュー

```text
この変更を独立レビューしてください。
Critical / Major を優先し、Minor・typo・好みのリファクタリングは原則不要です。

各指摘に:
- 根拠
- 影響
- 最小修正案

を付けてください。問題がなければ無理に指摘を作らないでください。
```

## Step 5: Codexで修正

- 単純〜通常の指摘 → GPT-6 Luna / Medium（単純作業だけLowも可）
- Lunaで不足するロジック・設計問題 → GPT-6 Sol / Medium
- Solでも解けない問題だけ → GPT-6 Astra

レビュー指摘は無条件に採用せず、コード上の根拠を確認してから修正します。
