# OpenCodeReview + MiMo：単独接続の第一段階

[English](ocr-mimo-standalone.md) | [日本語](ocr-mimo-standalone.ja.md)

## 更新（2026-11-11）

後続の操作者報告のlive receiptでMiMo応答2回とツール往復を確認しました。品質受入の証拠ではありません。次の[合成差分レビュー](ocr-mimo-synthetic-review.ja.md)で実CLIレビュー入口を追加し、ローカル模擬検証を実施しました。実差分のliveレビューは未完了です。以下は初回実装時点の記録として保持します。

## 過去の現在地（2026-11-11）

**実装済み：固定版の実CLIを使う接続確認入口と、ローカル模擬応答によるツール往復。実MiMo接続は未確認です。** コードレビュー、品質評価、Mailbox連携、Cloudflare監査の完成を意味しません。

[全体計画](mailbox-quality-roadmap-2026-10-26.ja.md)のP3へ進む前の接続準備です。既存の `eval_ocr_mimo.py` は引き続きmock専用で、今回live対応に変更していません。

## 固定したupstream

- [Alibaba OpenCodeReview v1.13.7](https://github.com/alibaba/open-code-review/releases/tag/v1.13.7)
- ソース：`b1dcffb0729f3f2e3e47170968a5014a2e035580`
- ライセンス：Apache-2.0。vendorや改変はせず公式CLIを外部依存として使用します。
- 公式releaseの各OS/CPUのSHA256を `tools/ocr_mimo_connection.py` に固定。違うバイナリは実行前に拒否します。
- 今回の取得・確認対象はDarwin arm64。その他OSの実行確認はしていません。

Darwin arm64の取得例（リポジトリ外の既存作業用ディレクトリで実行）：

```sh
curl --fail --location --proto '=https' --tlsv1.2 --output ./opencodereview-v1.13.7-darwin-arm64 https://github.com/alibaba/open-code-review/releases/download/v1.13.7/opencodereview-darwin-arm64
shasum -a 256 ./opencodereview-v1.13.7-darwin-arm64
chmod u+x ./opencodereview-v1.13.7-darwin-arm64
```

期待SHA256：`ce2eab495483f9b119992b48253a4e2f6969c27c3b02514350d9e7aa0083b4e8`。ハッシュが違う場合は実行せず停止します。

## 利用方法

依存Pythonパッケージは不要です。既存の `~/.opencodereview/config.json` がある環境では、設定の優先順位により別providerや認証コマンドが選ばれる可能性があるため、接続試験を停止します。設定の削除・上書き、HOMEの差し替えは行いません。

```sh
# 事前確認だけ。ネットワーク通信もCLI実行もしません。
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr

# 実CLIを使い、外部へは送らずloopbackの合成応答で2段階を確認。
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr --mock
```

ローカル試験では実CLIの `llm test` を起動します。固定版に埋め込まれた短い合成会話 → `ocr_selftest` の呼出し → 固定のtool結果 → 最終応答、という経路です。リポジトリのコードや正解データは入力しません。模擬成功の表示は `MOCK_PASSED` であり `CONNECTED` ではありません。

## 実MiMo接続（未実施）

認可された秘密注入により既存の `MIMO_API_KEY` がプロセスへ設定され、モデルID・価格・試行費用が確認された後にだけ使います。OpenClawのモデル登録と外部CLIに使える環境変数は別物で、キーの自動探索・コピーはしません。キーを引数、ソース、公開ログやGitに置きません。

```sh
python3 tools/ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr --live --receipt /private/non-git-directory/new-probe-receipt.json
```

- 送信先は `https://api.xiaomimimo.com/v1/chat/completions`、要求モデルは `mimo-v2.6-pro` に固定します。
- upstreamの組込み候補一覧は古いモデル名を含みます。この新しいモデルの提供可否、実際の応答モデルは未確認。別モデルや別経路へ自動で変更しません。
- 実APIキーは親の中継処理だけが保持し、CLIには一時的なloopback認証だけを渡します。
- POSTの上限は**合計2回**。失敗・結果不明の試行も含みます。中継は再試行せず、失敗後は停止状態になります。
- 1回のリクエスト本文は8,192 byte以下、出力指定は1,024 token、HTTP timeoutは30秒、CLI全体は70秒です。
- byte上限は正確な入力token上限ではありません。**ドル建て上限を強制する仕組みは未実装**で、計画書の「$0.10」を保証しません。価格・費用上限の取扱いを確定するまではliveを開始しません。
- 成功にはCLI終了コード0だけでなく、同一要求モデルの2応答、self-test tool結果の再入力、最終応答の完了が必要です。
- receiptは新規・排他的・権限0600で作成します。使用済みパスは拒否します。途中停止のreceiptや `FAILED_OR_UNKNOWN` は結果を照合し、機械的に再実行しません。
- usage欠測とlive費用は `unknown`。モデル本文やCLI stdout/stderrは保存・表示しません。
- 中継はコマンドの間だけloopbackで起動し、終了時に閉じます。常駐・スケジュール・global設定の変更はありません。

## 今回の検証と残件

1回の選択テスト実行で**5件成功、1.726秒**。実際の固定CLIとのmock接続、環境変数・認証分離、通信結果不明時の停止、入力上限とモデル不一致、2回上限と「終了コード0だけでは不合格」を確認しました。テストは最大10件の開発試行枠のうち5件を使用。live API呼出し0回です。

```sh
python3 tests/check_ocr_mimo_connection.py --binary /absolute/path/to/pinned-ocr
```

実認証・モデル提供・価格の確認後に限定live試験を行い、その後、正常／欠陥入りの公開合成差分を実OCR reviewへ渡す段階へ進みます。差分reviewの実行入口、実結果の受入れ採点、品質／費用の受入、Mailbox接続、高リスク時のCloudflare分岐はまだ未実装です。自動CIや全リポジトリ展開も今回追加していません。
