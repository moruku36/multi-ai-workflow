# 品質基盤 P1 最小整備と P3 単独評価準備レポート

[English](quality-baseline-evaluation-p1-p3.md) | [日本語](quality-baseline-evaluation-p1-p3.ja.md)

- 日時: 2026-10-26 (JST)
- 対象リポジトリ: `multi-ai-workflow`
- 設計正本: `docs/mailbox-quality-roadmap-2026-10-26.ja.md`
- 作業ブランチ: `feature/p3-offline-evaluation-scoring`
- 目標: 「機械的検査 → Alibaba OCR + MiMo API → 重要変更のみCloudflare監査」の役割分担により、Codexによる全文再読・重複レビューを削減する基盤の第一歩（P1最小整備およびP3合成サンプル・入力準備、評価結果受入れ・採点）。
- **現状の位置づけ**: 現状は「合成サンプルと評価入力の準備、および模擬結果の受入れ・採点検証」であり、Alibaba OCR 本体の統合ではありません。OCRの固定バージョン選定、CLIインストール、standalone実接続、API予算のハードウェア強制は未実装です。
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
  1. Python構文検査 (`py_compile.compile`, 16ファイル対象)
  2. 必須テストスイート実行 (`REQUIRED_TEST_SUITES` の存在・0件実行・スキップ・失敗を厳格判定)
  3. Fixture整合性検査 (manifest存在・パッチ欠落・空ファイル・mock_reviews存在を検知)
  4. ドキュメント書式整合性検査 (タブ混入・不正規末尾空白の検出)
  5. 外部ツール検知と未検証範囲（Unverified Scope）の明示
- **厳格化基準**:
  - 必須テストスイートの欠落、または実行テスト数 0 件の場合は成功扱いとせず直ちに FAIL とする。
  - スキップ件数（`tests_skipped`）を分離して明示。
  - テストおよびfixtureの整合性を検証する小さな回帰テスト (`tests/test_quality_baseline.py`, 11件) を配備・全件パス。

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

## 2. P3: 合成サンプルと評価入力・受入れ採点の準備（OCR統合前の前段準備）

### 2.1 現状のスコープと未実装事項

- **現状のスコープ**:
  - 公開可能な合成パッチの作成（before/after ソースからの機械的生成）
  - 正解データ（Ground Truth）の定義（※レビュアー入力からは完全除外）
  - レビュアー結果受入れスキーマと採点ロジックのオフライン実装
  - 模擬結果（mock review fixtures）によるアルゴリズム検証
  - オフラインでのドライラン検証 (`tools/eval_ocr_mimo.py`)
- **意図的に未実装として残す項目**:
  - Alibaba OCR 公式 CLI（`ocr`）の固定バージョン選定およびバイナリ導入
  - Standalone MiMo API への実ネットワーク接続
  - API 課金・トークン予算の強制機構（外側プロキシや認証認可によるハードリミット）

### 2.2 合成評価サンプルと Ground Truth

実リポジトリの非公開コード・個人情報・秘密の送信を防止するため、合成テストパッチを用意。

保存先: `tests/fixtures/synthetic_samples/`
1. **正常例 (`clean_refactor.patch`)**:
   - 内容: 動作（セマンティクス）を完全に変更しない純粋なリファクタリング（型ヒント付与、内包表記による等価な記述）。
   - 目的: False Positive（誤検知・過剰な指摘・ハルシネーション）の計測。
   - 期待欠陥数: **0件**
2. **欠陥例 (`defect_seeded.patch`)**:
   - 内容: `DEFECT` や答えを示すヒントコメントを一切排除した自然なコード差分。
     - 行 11: Path Traversal (`target_path = self.base_path / user_supplied_name`, CWE-22, CRITICAL)
     - 行 12: Resource Leak (`open()` の非クローズ・`with` 未使用, CWE-775, MEDIUM)
     - 行 18: 任意コード実行 (`eval(filter_expr)`, CWE-95, CRITICAL)
     - 行 20: 例外の完全黙殺 (`except Exception: pass`, CWE-391, LOW)
   - 目的: Recall（見逃し率）、深刻度判定精度、有用な指摘（Actionable Findings）の計測。
   - 期待欠陥数: **4件**
3. **正解データマニフェスト (`synthetic_samples_manifest.json`)**:
   - 正解データの行番号・CWE・重大度を定義。
   - **重要**: 正解データはレビュー入力プロンプトには絶対に含めず、ローカル評価・検証でのみ使用。

### 2.3 評価メトリクスの記録基準

実試験の際は、以下の項目を分離して記録する：
- **Actionable Findings**: 具体的な修正案・影響根拠を伴う有用な指摘件数
- **False Positives**: 正常なコードに対する誤検知・不当な指摘件数
- **Missed Defects (Seeded Misses)**: Ground Truth の欠陥を見逃した件数
- **Coverage Scope**: 検査対象ファイルおよび除外ファイル範囲
- **Latency**: 実行所要時間（秒）
- **Usage & Cost**: 入力トークン数、出力トークン数、推定実費（USD/JPY、未取得時は `UNKNOWN`）
※作者ベンチマーク「約1/9」は保証値と扱わない。指摘ゼロや部分失敗を合格扱いしない。

### 2.4 評価結果の受入れと採点（オフライン模擬検証）

レビュアー結果の受入れスキーマと採点ロジックをオフラインで実装完了。
実AIの品質評価ではなく、受入れ・採点アルゴリズムの検証として模擬（mock）結果 fixture (`tests/fixtures/synthetic_samples/mock_reviews/`) を用いて検証。

- **受入れ最小形式**: `schema_version`, `is_mock: true`（実AI結果との誤認防止）, `sample_file`, `status`, `findings`（`file`, `line`, `severity`, `category` 必須）。
- **採点ルール**:
  1. **指摘の一致 (Matched)**: 行番号の一致に加え、カテゴリや内容が合致している場合のみ一致と判定。
  2. **重複指摘 (Duplicate)**: 同一欠陥に対して複数の指摘がなされた場合、重複として分離記録。
  3. **見逃し (Missed)**: Ground Truth の欠陥に対応する指摘が存在しない場合。
  4. **判定保留 (Pending Human Review)**: 行番号は一致しているがカテゴリ・説明が乖離している場合や、近接行（±2行以内）の指摘は機械的正解とせず、人による内容確認が必要な保留として集計。
  5. **未取得メトリクス**: 模擬データにおいて usage / 実費 / latency は未取得とし、一律 `unknown` を維持。実試験上限案は変更しない。

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
  - 正解データ（Ground Truth）は入力に含めない。
  - APIキー等の秘密値は画面表示、ログ出力、コミットを一切行わない。
  - 不明なエラーや権限拒否が発生した場合は即時停止（fail-closed）。

---

## 5. 現在の状態と次フェーズへの引き継ぎ

- **現在のステータス**: P1 最小整備完了、P3 合成サンプル・入力準備および受入れ・採点オフライン検証完了（オフライン dry-run 検証済み、回帰テスト 11 件全件合格）。
- **停止条件**: 本フェーズの目標を達成したため、自動でマージや次フェーズ（実通信、P2、P4）へ進まず停止。
