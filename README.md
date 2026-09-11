# Multi-AI Workflow Architecture

複数のAIモデル（Ollama/Qwen, Gemini + Antigravity, ChatGPT + Codex, Claude API）それぞれの強みに応じて役割を分担し、最大の生産性とアウトプット品質を実現するための運用基盤・設定リポジトリです。

<p align="center">
  <img src="assets/architecture.jpg" alt="Multi-AI Workflow Architecture" width="100%"/>
</p>

---

## 1. 全体コンセプトと4つのレベル定義

各モデルは「性能の優劣」ではなく、**「扱う対象と責務」** で切り分けるのが最も効率的です。

```text
       【作業発生】
            │
            ├─ [Layer 1] Strategy & Orchestration / 単純加工・大量処理
            │     └─ Ollama / Qwen (Project Manager AI / Processing)
            │
            ├─ [Layer 2] Reasoner & Planning / 調査・実務・コード生成・エージェント操作
            │     └─ Gemini 3.8 Flash + Antigravity (Worker AI)
            │
            ├─ [Layer 3] Complex Execution / 思考・設計・相談・個人文脈を踏まえた判断
            │     └─ ChatGPT 5.6 Sol / Codex (Execution AI)
            │
            └─ [Layer 4] Finalization & Memory / 批判的検証・セカンドオピニオン・最終レビュー
                  └─ Claude API (Knowledge Base & Final Reviewer)
```

### レベル別詳細マトリクス

| レベル | 主役 | 向いている仕事 | 役割のキーワード |
|---|---|---|---|
| **Layer 1** | **Ollama / Qwen** | 要約、整形、分類、ログ処理、定型変換など、手元情報だけで完結する軽作業 | **加工・オーケストレーション** |
| **Layer 2** | **Gemini + Antigravity** | 最新情報の調査、Web検索、資料作成、コード生成、ファイル操作、エージェント作業、日常の実務全般 | **実務・調査・計画** |
| **Layer 3** | **ChatGPT + Codex** | 複雑な推論、設計、計算、レビュー、難しいコード、そして**長期記憶・価値観・過去の経緯を踏まえた相談や判断** | **思考・専属アーキテクト** |
| **Layer 4** | **Claude API** | セカンドオピニオン、最終レビュー、他モデルで詰まった時の再検討 | **最終レビュー・ナレッジベース** |

---

## 2. Gemini と ChatGPT の境界線

本ワークフローにおいて最も重要な切り分けです。

```text
                ┌────────────────────────┐
                │        タスク発生      │
                └───────────┬────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
      【 外の世界・実務 】         【 自分の文脈・設計 】
     Gemini + Antigravity         ChatGPT 5.6 Sol / Codex
              │                           │
              │ (実装の壁・抽象的設計)    │ (実務への展開・実機適用)
              ├───────────────────────────┤
              │                           │
              └─────────────┬─────────────┘
                            │ (重要成果物の検証)
                            ▼
                    【 批判的検証 】
                       Claude API
```

### 🔷 Gemini（外の世界を扱う）
- 最新情報を調べる（Google検索・外部ドキュメント）
- Webやプロジェクト内のローカルファイルを横断走査する
- Antigravityなどの自律型エージェントで実際に手を動かす
- まず大量に処理・プロトタイプ作成をする
- 日常的な実務作業をスピード重視でこなす

### 🔶 ChatGPT（自分自身の文脈を扱う）
- 過去の相談内容や個人の背景を踏まえる
- 自分の性格、仕事観、生活方針、プロジェクト経緯を加味して判断する
- 複雑なアーキテクチャや抽象度の高い問題をじっくり考える
- Geminiの出した結論やプロトタイプを再検討・ブラッシュアップする
- Codex枠を使って難易度の高い実装・リファクタリングを詰める

> **Note: Codex枠とChatGPT本体の切り分け**  
> Codexの使用枠（Rate Limit）を使い切っても、ChatGPT 5.6 Sol本体での相談・設計・思考パートナーとしての対話は継続可能です。  
> 「Codexが切れた ＝ Level 3が使えない」ではなく、思考・設計は引き続きChatGPTで行い、実務コードへの落とし込みをGemini（Level 2）に委ねる柔軟な運用が可能です。

---

## 3. リポジトリ構成

```text
.
├── README.md                      # 本ドキュメント（全体像と運用思想）
├── .gitignore                     # Git管理除外設定
├── assets/
│   └── architecture.jpg           # アーキテクチャ概念図
├── docs/
│   ├── routing-guide.md           # 逆引きタスク振り分けガイド
│   └── handoff-templates.md       # モデル間のコンテキスト引き継ぎ雛形
├── configs/
│   ├── level1-ollama/             # Level 1 (Qwen) のModelfile・起動定義
│   ├── level2-antigravity/        # Level 2 (Gemini) のエージェント行動ルール
│   ├── level3-chatgpt/            # Level 3 (ChatGPT) のカスタム指示・ペルソナ定義
│   └── level4-claude/             # Level 4 (Claude API) のレビュープロンプト＆CLI
└── templates/
    └── .env.example               # 環境変数テンプレート
```

---

## 4. クイックスタート

### 1. 環境変数の設定
```bash
cp templates/.env.example .env
# .env を編集して各種APIキーを設定（.envは.gitignoreで除外されます）
```

### 2. 各階層のセットアップ
- **Level 1**: `configs/level1-ollama/` を参照して Ollama の Modelfile を登録
- **Level 2**: `configs/level2-antigravity/` のルールを Antigravity のプロンプトや設定に反映
- **Level 3**: `configs/level3-chatgpt/custom_instructions.md` の内容を ChatGPT の「カスタム指示」に登録
- **Level 4**: `configs/level4-claude/` のスクリプトで即座にレビューを実行できるように準備
