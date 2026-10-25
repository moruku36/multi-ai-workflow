# 品質基盤 P1 最小整備と P3 単独評価準備レポート

[English](quality-baseline-evaluation-p1-p3.md) | [日本語](quality-baseline-evaluation-p1-p3.ja.md)

- 日時: 2026-10-26 (JST)
- 対象リポジトリ: `multi-ai-workflow`
- 設計正本: `docs/mailbox-quality-roadmap-2026-10-26.ja.md`
- 作業ブランチ: `feature/quality-baseline-p1-p3`
- 目標: 「機械的検査 → Alibaba OCR + MiMo API → 重要変更のみCloudflare監査」の役割分担により、Codexによる全文再読・重複レビューを削減する基盤の第一歩（P1最小整備およびP3単独評価準備）。
- 制約遵守: Mailboxアダプター・常駐化・全リポジトリ展開は作成せず、新規パッケージの無断インストールや外部通信を行わない。

---

## 1. P1: 既存環境の棚卸しと決定的検査（非LLM）の最小整備

### 1.1 既存資産の棚卸し

| 項目 | 状態 / 内容 | 備考 |
|---|---|---|
| **CI / ワークフロー** | `.github/workflows` 未配備 | リポジトリ単体での自動CIは未設定 |
| **対象言語** | Python 3.11, Node.js 22.23 (v8), Shell, PowerShell, Markdown, Mermaid | 主体はワークフロー設計文書と補助スクリプト |
| **テストスイート** | `configs/openwebui-local-memory-0.11.4` 配下に合計88件の `unittest` | 全88件パス確認（54 + 27 + 7） |
| **ビルド / 描画** | `tools/architecture/` にて Pele 1.6.0 (vendor済みtarball) による Mermaid → SVG 生成 | `npm run build` 用（実行にはオフライン `npm ci` が必要） |
| **静的解析ツール** | グローバルPATHに `ruff`, `semgrep` は未導入 | Python, Node.js, npm は利用可能 |

### 1.2 最小の check-only ラッパー (`tools/check_quality.py`)

外部パッケージを追加せず、Python 3.11 標準ライブラリのみで動作する決定論的検査ラッパーを配備。
自動修正や全面フォーマットは行わず、check-onlyで現在の状態を検査・記録する。

- **実行コマンド**: `python tools/check_quality.py` (または `--json`)
- **検査項目**:
  1. Python構文検査 (`py_compile.compile`, 14ファイル対象)
  2. 既存unittestの一括実行 (3スイート、88テスト対象)
  3. ドキュメント書式整合性検査 (タブ混入・不正規末尾空白の検出)
  4. 外部ツール検知と未検証範囲（Unverified Scope）の明示
- **実行結果**:
  - `overall_status`: **PASSED**
  - Python Syntax: OK (14 files)
  - Unittests: OK (88 tests run, 0 failures, 0 errors)
  - Doc Format: OK (47 files)
  - 未導入ツール: `ruff` (MISSING), `semgrep` (MISSING) を検知し、スキップ理由を記録。

### 1.3 初回試行パイロットリポジトリの提案

`multi-ai-workflow` 自体はワークフロー設計と運用文書が中心のリポジトリであり、コードのない文書リポジトリへ形式だけの Ruff / Semgrep を空振り導入すべきではない。

**提案リポジトリ**: `web-security-control-lab`
- **選定根拠**:
  - FastAPI / Python 3.11 ベースの実装コード（37コードファイル）を保有。
  - `pyproject.toml` にすでに `[tool.ruff]` (E, F, W, I, line-length 100) および `[tool.pytest]` 設定が明記されている。
  - 専用の `.venv` 内に `ruff.exe` および `pytest.exe` がインストール済みであり、新規依存インストールのリスクなく即座に検証可能。
  - セキュリティ学習ラボとしての性質上、静的解析・欠陥検知の精度検証に最も適している。
- **次点候補**: `home-ai-engineering-lab` (52コードファイル、スキーマ・スクリプト・テストあり)

---

## 2. P3: Alibaba OCR + MiMo API 単独評価の準備

### 2.1 Alibaba OCR の仕様と運用形態の明確化

- **ツール概要**: Alibaba 製 `open-code-review` (CLI: `ocr`, Apache-2.0)。Go言語による決定論的エンジニアリングパイプラインとLLMエージェントを組み合わせたハイブリッド構造。Git diffを行レベルで追従し、行番号のズレを防ぐ。
- **Standalone + MiMo 構成**:
  - 通常レビューの推論バックエンドとして Xiaomi MiMo API（OpenAI互換エンドポイント）を指定して実行する。
  - **Codex delegation との明確な区別**: Codex のホストセッションやクォータを間接消費し続ける委託経路ではなく、独立した API エンドポイント（MiMo）へ接続する standalone 構成とする。
- **課金・クォータの境界**:
  - 作者ベンチマークの「トークン約 1/9」は参考値であり、実環境の削減率や品質保証とは扱わない。
  - `max-token-budget` を厳密な課金上限とは扱わず、ラッパー外側で「最大呼出回数」「入出力トークン上限」「タイムアウト」「実費上限」を強制する。
  - 指摘ゼロや部分失敗を安易に「合格」と判定しない。

### 2.2 合成評価サンプルと Ground Truth

実リポジトリの非公開コード・個人情報・秘密の送信を防止するため、合成テストパッチ（公開可能な最小差分）を用意。

保存先: `tests/fixtures/synthetic_samples/`
1. **正常例 (`clean_refactor.patch`)**:
   - 内容: 型ヒント追加、内包表記リファクタリング、組み込み `sum()` 活用。
   - 目的: False Positive（誤検知・過剰な文句・ハルシネーション）の計測。
   - 期待欠陥数: **0件**
2. **欠陥例 (`defect_seeded.patch`)**:
   - 内容: 4つの明確な既知の欠陥を意図的に埋め込み。
     - DEFECT-01: Path Traversal (`target_path = self.base_path / user_supplied_name`, CWE-22, CRITICAL)
     - DEFECT-02: Resource Leak (`open()` の非クローズ・`with` 未使用, CWE-775, MEDIUM)
     - DEFECT-03: 任意コード実行 (`eval(filter_expr)`, CWE-95, CRITICAL)
     - DEFECT-04: 例外の完全黙殺 (`except Exception: pass`, CWE-391, LOW)
   - 目的: Recall（見逃し率）、深刻度判定精度、有用な指摘（Actionable Findings）の計測。
   - 期待欠陥数: **4件**
3. **メタデータマニフェスト (`synthetic_samples_manifest.json`)**:
   - 正解データ（Ground Truth）の行番号、CWE、重大度を定義。

### 2.3 評価メトリクスの記録基準

実試験の際は、以下の項目を分離して記録する：
- **Actionable Findings**: 具体的な修正案・影響根拠を伴う有用な指摘件数
- **False Positives**: 正常なコードに対する誤検知・不当な指摘件数
- **Missed Defects (Seeded Misses)**: Ground Truth の欠陥を見逃した件数
- **Coverage Scope**: 検査対象ファイルおよび除外ファイル範囲
- **Latency**: 実行所要時間（秒）
- **Usage & Cost**: 入力トークン数、出力トークン数、推定実費（USD/JPY、未取得時は `UNKNOWN`）

---

## 3. 将来の分岐: Cloudflare security-audit-skill の位置づけ

Cloudflare の `security-audit-skill` は全PRに一律適用するゼロトークンスキャナーではなく、人間を含む高負荷な監査手順である。

### 分岐基準（将来のトリガー条件）
- **通常差分**: 機械的検査（非LLM） → Alibaba OCR + MiMo API レビュー
- **高リスク変更（Cloudflare 監査手順へ分岐）**:
  - 認証・認可ロジックの追加・変更
  - 秘密情報（APIキー、トークン、証明書）の境界や取り扱い変更
  - 外部入力の直接実行、コマンド実行、ファイルシステムアクセス境界の変更
  - 権限設定（IAM、セキュリティポリシー、アクセス制御）の変更
  - 外部サプライチェーン（新規パッケージ依存）の追加
※今回はフル監査や多人数の検証ループは起動せず、上記のルーティング分岐条件の整理にとどめる。

---

## 4. MiMo 接続試験の実行案（承認待ち）

実際の外部API接続は行わず、オフラインの dry-run ツール `tools/eval_ocr_mimo.py` を実装完了。
試験開始の承認が得られた場合、以下の条件で段階的に実施する。

### 実行条件案
- **接続先認可経路**: 事前合意された OpenAI 互換 MiMo エンドポイント
- **推論モデル**: `mimo-v2.6-pro`（または認可済み特定モデルID）
- **上限バウンド**:
  - 最大呼出回数: **2回**（合成サンプル2件分のみ）
  - 入力トークン上限: **2,048 tokens / 回**
  - 出力トークン上限: **1,024 tokens / 回**
  - タイムアウト: **30秒 / 回**
  - 実費上限: **$0.10 USD**
- **安全境界**:
  - 送信データは `tests/fixtures/synthetic_samples/` の合成パッチのみに限定。
  - APIキー等の秘密値は画面表示、ログ出力、コミットを一切行わない。
  - 不明なエラーや権限拒否が発生した場合は即時停止（fail-closed）。

---

## 5. 現在の状態と次フェーズへの引き継ぎ

- **現在のステータス**: P1 最小整備完了、P3 単独評価準備完了（API未呼出・dry-run検証済み）。
- **停止条件**: 本フェーズの目標を達成したため、自動でマージや次フェーズ（実通信、P2、P4）へ進まず停止。
