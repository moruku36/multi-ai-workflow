# ローカル静的チェックアダプタ、2026-11-05

[English](quality-static-runner-2026-11-05.md) | [日本語](quality-static-runner-2026-11-05.ja.md)

## 実装範囲

`tools/run_static_checks.py` は、**導入済み**のRuffとSemgrep Community Editionを、明示指定したPythonファイルに対して実行する標準ライブラリ製の単独アダプタです。導入、自動修正、LLM呼出し、認証、push、リモート規則の取得は行いません。

初回の単独アダプタ納品時は `tools/check_quality.py` を変更していません。その後のオフライン再開作業で任意接続を追加しました。詳細は [quality-wrapper-integration-2026-11-05.ja.md](quality-wrapper-integration-2026-11-05.ja.md) を参照してください。通常実行では引き続き静的エンジンを呼びません。Direct MiMo復元物は別のままで、いずれもP1/P3/P4全体の完成ではありません。常駐処理やCIは有効化していません。

## 使用方法

既に利用承認された信頼できる実行ファイルを、対象リポジトリの外の絶対PATHから利用します。

```sh
python tools/run_static_checks.py --repo-root /path/to/pilot --target app/main.py --tool ruff
python tools/run_static_checks.py --repo-root /path/to/pilot --target app/main.py --target app/service.py
```

`--tool` を省略するとRuff、Semgrepの順で逐次実行します。相対パスの `.py` ファイルごとに `--target` を繰り返します。ディレクトリ展開や全リポジトリ走査はしません。初版ではリポジトリ内の実行ファイルや仮想環境を自動選択しません。POSIX対応で、Windowsでは `UNSUPPORTED_PLATFORM` として停止します。

## 検査と境界

- Ruff: `check`、Python 3.11対象、設定隔離、キャッシュ・修正なし。最小の正当性検査 `E9,F63,F7,F82`。書式検査は含まず、行内の `noqa` 抑制は無効化します。
- Semgrep: `scan --oss-only`、同時1件、ハッシュ固定したローカルJSON規則、metrics・version check停止、strict errors、Git ignoreの影響なし、行内 `nosem` 抑制無効。最初の3規則は動的 `eval`/`exec`、所定の `subprocess` 呼出しの `shell=True`、bare/`Exception` の握りつぶしです。指摘はレビュー候補であり、悪用可能性や網羅的な安全性の証明ではありません。
- 指定された通常のUTF-8 Pythonファイルだけを隔離コピーします。シンボリックリンク、親への遡り、重複、通常ファイル以外、NULを拒否します。ディレクトリ記述子を使う上限付き読込で、選択中のリンク・FIFO差替えも防ぎます。
- 上限: 50ファイル、1件1 MiB、合計5 MiB、各エンジン30秒、標準出力・標準エラー合計2 MiB、指摘1,000件。Semgrepには追加で規則タイムアウト10秒、メモリ512 MiBを指定。再試行・並列エンジン実行はありません。
- 一時コピーと専用のHOME/config/cacheで実行します。認証情報・proxy・Pythonフックの環境変数は継承しません。タイムアウト時だけでなく親プロセスの通常終了時にもプロセス群を回収し、回収不明なら次のエンジンを止めます。
- 意図した通信処理をローカル設定とフラグで避けますが、**OSレベルの通信遮断ではありません**。通信封じ込めを証明するものではなく、厳密な遮断が必要なら承認済みのオフライン実行環境を使います。このアダプタはシステム・ネットワーク設定を変更しません。

## 結果形式

JSONを出力し、指定した全エンジンの検査が問題なく完了した場合だけ終了コード0にします。未導入、部分検査、不正出力、実行エラー、時間超過、指摘あり、未対応環境は非0です。

対象内容のハッシュ、相対パス、正規化した指摘、同梱規則のハッシュを記録します。Semgrepは `paths.scanned` に対象全件、`errors=[]` が必要で、0件や部分検査を成功扱いしません。RuffのJSONには走査パス一覧がないため、範囲の根拠は検証した明示入力と検査コマンドの正常終了に限ります。生ソース断片、ツール由来の説明文、絶対診断パス、標準エラー本文は結果へコピーしません。標準エラーはハッシュのみです。この報告内でRuffの版は `unknown`、Semgrepは出力に版がある場合のみ保持するため、受入実行ごとに導入パッケージの版も別途記録します。下記で確認した版は `tools/quality/requirements-static.txt` に固定しました。

状態は `PASSED`、`FINDINGS`、`UNAVAILABLE`、`TOOL_ERROR`、`INVALID_OUTPUT`、`CONFIG_ERROR`、`TIMEOUT`、`OUTPUT_LIMIT`、`CLEANUP_ERROR`、`NOT_RUN` などです。未導入を検査成功と扱いません。

## 検証と残る受入

2026-11-05の初期実装時は両エンジン未導入でした。最小12テストはPASS。模擬の成功・指摘・エラー形式、Semgrepの部分/不正走査、各上限、パス・環境変数境界、規則ハッシュ、実際のローカルPythonによる起動・時間超過・出力上限・子プロセス回収を検証しました。このプロセス試験はアダプタの試験であり、Ruff/Semgrepの検出精度の試験ではありません。

同日その後、許可された公式PyPI wheelを隔離環境に導入できました。**Ruff 0.17.3、Semgrep CE 1.183.0**です。`tests/fixtures/static_checks/clean.py` と `defect.py` をまとめて、各エンジン1回だけ実行しました。正常ファイルは両方0指摘。Ruffは仕込んだ未定義名F821を1件、Semgrepは同梱3規則を受け入れ、shell=True、eval、例外握りつぶしを各1件検出しました。入力ハッシュは不変。意図した指摘があるためラッパーは正しく終了コード1を返し、別のサンプル受入判定はPASSです。導入版とwheel配布元・ハッシュを記録しました。LLM/API呼出し、認証、push、ネットワーク設定変更はありません。

その後のラッパー接続では対象を明示した場合だけこのJSONを取り込みます。オフライン検証は既存基準19件と統合8件であり、新しい実エンジン走査ではありません。完全なcheckoutでの受入と、予定した試験リポジトリでの評価が残ります。実エンジンの2ファイル試験は基本的なCLI・規則互換性と既知欠陥の検出確認に限り、一般的な検出精度や網羅的な安全性の証明ではありません。LLM実評価は別に判断します。既存MiMoの試行・費用上限は変えず、このアダプタからMiMoは呼びません。

過去の基準は `8a0877ab5225cbb806389e1a19842bbce71a47e3`。2026-11-05に現在mainの `check_quality.py` blobが同一であることも確認済みです (`d1b54668c947231543be6b2be5238121aa70625e`)。現在headの全リポジトリ試験ではありません。
