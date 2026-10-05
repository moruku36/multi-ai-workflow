# Open WebUI 0.11.4 ローカルMemory運用手順

[English](README.md)

対象: **Open WebUI 0.11.4のみ**、ローカルのOllama Qwen3モデル、標準のユーザー別**Memory**。このディレクトリは従来の`configs/level1-ollama`とは独立しており、既存ファイルは変更していません。ここにある内容は、稼働中のサービスの変更、パッケージのインストール、ネットワーク通信、認証情報の読み取りを行いません。

状態ラベル: **ソース確認**（インストール済み0.11.4のソースを読んだだけで実行していない）、**オフラインmock**（合成mockでのみ成立。実アプリの証明にはならない）、**ライブ確認待ち**（未検証。人が日程を決めて確認する）。

## 1. 区別すべき3つの機能

| | 内容 | メモリを書き込むか | 状態 |
|---|---|---|---|
| (a) 標準Memory | `memory`テーブルのユーザー別行と、ユーザー別のベクトルcollection。設定画面とAPI `/api/v1/memories`で管理。`memories.enable`、ユーザー権限`features.memories`、モデルのcapability `memory`、チャットごとのMemory切替で制御。取得したメモリは（`memories.system_context.enable`により）プロンプトへ挿入されます。 | 設定画面でユーザーが追加・編集・削除したときのみ | ソース確認 |
| (b) Builtinメモリツール | モデルのBuiltin Tools > **Memory**（`builtinTools.memory`）。`add_memory`、`update_memory`、`replace_memory_content`、`delete_memory`と読み取りツールをモデルに公開。**既定はON**。同じrouter関数を直接呼びます。 | **書く（モデル主導）** | ソース確認 |
| (b2) Background review | `memories.background_review.enable`（既定はオフ）。N回のユーザーターンごとに、サーバーがモデルへadd/replace/removeを問い合わせて適用します。 | **書く（自動）** | ソース確認 |
| (c) チャット履歴検索 | Builtin Tools > **Chats**（`search_chats`、`view_chat`）。自分の過去チャットを読むだけです。Memoryではなく、何も保存しません。 | 書かない | ソース確認 |

### 保存承認: 証明できないので使わない

- メモリ書き込み経路に、ユーザー確認を求める処理はありません。`add_memory`などは即時に書き込み、`update_memory`もバッチを即時に適用します。
- `chat.tool_permissions.enable`と`params.tool_approval_mode = ask`はツール呼び出しを承認待ちにできますが、モードはクライアントのリクエスト由来で`full`にもでき、automation/channelでは無効で、background reviewには効きません。**保存承認の保証ではなく**、この手順はこれに依存しません。
- 「保存前に確認すること」というプロンプト規則も強制力はありません。チャット内の引用文や注入文がモデルにツール呼び出しを促す可能性があり、防げるのはツールを公開しないことだけです。

**決定:** Builtin **Memory**ツールは**すべてのモデル（ローカルも外部も）でOFF**にして、モデル自身が書き込みを始められないようにします。background reviewも**OFF**のままにします。**チャット内の「これを覚えて」は未実装であり、保証もしません。** チャットで「Xを覚えて」と言ってもXは保存されません。唯一サポートする書き込み経路は、設定画面での手動CRUDです。

## 2. 必要な設定（手動で設定。非importの`reference-settings.reference.json`を参照）

- `memories.enable` = true。
- `memories.background_review.enable` = false。
- 検査ツールが読むのは**永続化されたconfig行**であり、**実効の実行時設定**ではありません。環境変数が永続行を上書きすることがあり、行がないキーは、検査ツールから見えないコード既定値（または環境変数の値）になります。ライブで確認するまで、検査結果は「永続行のみ」として扱います。
- Embedding: 組み込みのsentence-transformers **MiniLM**を維持します（`rag.embedding_engine`は空、`rag.embedding_model`は`sentence-transformers/all-MiniLM-L6-v2`）。embeddingモデルは変更しません。プロセス内MiniLMは「設定されたembedding endpointを呼ばない」ことを意味し、ネットワークが完全に無音であることは意味しません。モデルのダウンロード/読み込みやHub通信は、ここにある内容では排除されません。OllamaのURLが併存していても、engineが空なら使われません。MiniLMがダウンロード済みか、実行時に外向き通信があるかは**ライブの通信確認ゲート**です（第9節の手順8）。
- **すべての**モデル（ローカルも外部も。管理画面 > Models）: **Builtin Tools > Memory OFF**。既定はONで、ONだとモデルが自分でメモリを書けます。
- ローカルのメモリ用モデル（専用のQwen3項目）だけ: **Capabilities > Memory ON**。
- ローカル以外のモデル（OpenAI互換、RunPod）はすべて**Capabilities > Memory OFF**。メモリはチャットで選択中のモデルへ送るプロンプトに入るため、外部モデルでMemoryを有効にしたチャットはメモリをそのエンドポイントへ送ります。
- このリポジトリは認証情報を読まず、設定もせず、OpenAIやRunPodへメモリを自動共有しません。OpenAIのbase URLが設定されていることは、使用を意味しません。

config表の部分は検査ツール（第6節）で確認します。モデルごとの設定はモデルレコードにあり、検査ツールは意図的に読みません。UIで確認してください。

## 3. 手動のMemory CRUD（唯一の書き込み経路）

UI表記は0.11.4のフロントエンドbundle内の文字列（`Personalization`、`Memory`、`Manage`、`Add Memory`、`Edit Memory`、`Clear memory`、および"Memory added/updated/deleted successfully"）から確認しました。各操作の設定画面での正確な配置は、人が稼働中のアプリで確認するまで**ライブ確認待ち**です。以下のAPIの挙動は**ソース確認**で、それを呼ぶUI操作は未検証です。

1. **一覧・参照:** ユーザーメニュー > Settings > Personalization > Memory > **Manage**。自分のメモリが本文付きで並びます。（API: `GET /api/v1/memories/`）
2. **追加:** **Add Memory**で短い事実を1件入力して保存。（API: `POST /api/v1/memories/add`）手動追加は行を保存してからembeddingを作ります。embeddingが失敗するとリクエストはエラーになりますが、行だけ残ってベクトルがなく、取得されない場合があります。その場合は削除するかreindexします。
3. **編集・訂正:** 項目を開き（**Edit Memory**）、本文を直して保存。ベクトルは作り直されます。（API: `POST /api/v1/memories/{id}/update`）
4. **1件削除:** API `DELETE /api/v1/memories/{id}`はソース確認済みで、自分のユーザーに限定されます。設定画面に**項目ごと**の削除操作が実際にあるかは別の**ライブ確認待ち**で、存在すると仮定しないでください。初回利用時に見つからなければ、そこで止めて記録します。アカウントの全メモリを消す**Clear memory**（`DELETE /api/v1/memories/delete/user`）で代用しないでください。
5. **新規会話での取得確認:** ローカルモデルでチャットごとのMemoryを有効にした新規チャットを開き、その事実に関係する質問をして、返答に反映されるか見ます。続けて項目を削除し、別の新規チャットでもう一度質問します。

補足: typeなしでAPI追加したメモリは`context`として保存され、ベクトル類似度で取得されます。`rag.relevance_threshold`が0だと、無関係でも近い項目が返ります。type `user`のメモリは常に挿入されます。項目は短く、機密を含めないでください。認証情報や他人の私的情報は保存しません。

## 4. ローカル限定の使い方

- Memoryを使うチャットは、ローカルOllama Qwen3専用の会話（または専用のモデル項目）にします。他のモデルのチャットではチャットごとのMemory切替をオフにします。
- Memoryはユーザーアカウントごとです。別アカウントに自分のメモリは渡りません（オフラインmock。ソース上もrouterは`user.id`で絞り込みます）。
- 補助タスク（タイトル、タグ、検索クエリ）は`task.model.default`/`task.model.external`とチャットモデルの接続種別で振り分けられます。実際にどのモデルが使われ、チャットやメモリの文章が非ローカルのエンドポイントへ届かないかは**ライブ確認待ち**です。

## 5. Memoryとチャット履歴検索の違い

Memoryは、自分が管理する短い一覧で、類似度に応じてプロンプトへ挿入されます。チャット履歴検索（`search_chats`/`view_chat`）は、必要に応じて過去会話の文章を引き出すもので、モデルのChats builtinツールがONのときだけ使えます。どちらも他方の代わりにはならず、メモリを消してもチャット履歴は消えず、その逆も同じです。モデルに過去チャットを読ませたくない場合は、そのモデルのChats builtinツールをOFFにします。

## 6. ツール

すべてローカルで動く標準ライブラリのPythonで、テストは一時的な合成データだけを使います。

### `inspect_config.py`（allowlist検査）

```
python inspect_config.py --db <webui.dbのパス> [--json]
```

- ファイルを`mode=ro`と`query_only`で開き、`config.key`/`config.value`だけを許可するSQLite authorizerを設定します。SQLを書き換えても、memory/chat/user/auth表は読めません。
- ソースファイル内のallowlistのキーだけを選択します。APIキー、secret、`*.api_configs`は要求しません。
- endpoint設定（`rag.ollama.base_url`、`rag.openai.api_base_url`、`rag.azure_openai.base_url`、およびプロバイダ一覧`ollama.base_urls`/`openai.api_base_urls`）は、認証情報フィールドを含むJSONオブジェクトとして保存されることがあり、一覧はそのオブジェクトの配列のこともあります。検査ツールは**SQLite内でJSON1により射影**し、入れ子の`url`文字列（一覧は要素ごとに1つ）だけをPythonへ返します。オブジェクト自体は選択しません。JSON1がない場合、または値がURL文字列/`url`文字列を持つオブジェクトでない場合はfail-closed（値は`<redacted>`で終了コード3、JSON1なしなら終了コード2）になり、生の値の選択へフォールバックしません。プロバイダ接続はURLだけを検査し、認証情報や接続ごとの設定は見ません。スカラーのURL文字列も受け付けます（0.11.4のソースがこれらのキーに書く形式です）。
- 報告するのは永続行であり、実効の実行時設定ではありません（第2節）。行がないキーは、コード既定値と「env override unknown」付きで表示します。
- 生の値は出力しません。型の違い、想定外の形式、秘密らしい文字列は`<redacted>`になります。endpointはscheme/host/portだけに縮約し（userinfo、path、query、fragmentは破棄）、字句判定で`loopback`/`local-host-alias`/`private-network`/`non-local-or-unknown`を付けます（名前解決やネットワーク通信なし）。
- Ollama embedding engineに対する厳格なローカル限定ポリシー: **loopback**はWARN（許容。ライブでlistenerを確認）。`host.docker.internal`などのコンテナホストの**別名**はWARNで**UNVERIFIED**表示（loopbackとは断定しない。ライブでのホスト確認が必要）。**private-network**アドレス（RFC1918/link-local）はこのマシンと証明できないため**FAIL**。それ以外もFAILです。
- 終了コード: 0=ポリシー違反なし、1=ポリシー違反（例: background reviewがON、非ローカルembedding）、2=ファイルを信頼できない（なし、読めない、未知のschema）、3=値を解釈できない。終了コードが0以外のとき、成功とは表示しません。
- 接触を避けたい場合は、データベースの**コピー**に対して、またはサービス停止中に実行してください。どちらでも読み取り専用です。

### `backup_db.py`（整合性のあるバックアップ。復元はしない）

```
python backup_db.py --source <webui.db> --dest <リポジトリ外の新しい絶対パス> --confirm-private-destination
```

- 読み取り専用のソースからSQLiteのオンラインbackup APIでコピーするため、write-ahead logにある内容も含めた整合的なスナップショットになります。
- 拒否するもの: 既存の保存先（上書きなし）、このリポジトリ内またはgit作業ツリー内の保存先、相対パス、ソース自身、未知のschema、0.11.4以外のmigration revision（`d4c1a8e37b62`以外）。
- 配置前にコピーを検証（`integrity_check`、schema）し、失敗時は一時ファイルを削除してエラーを出し、終了コードは0以外です。成功時はサイズとSHA-256を表示します。
- バックアップには**すべて**（メモリ、チャット、ユーザー、パスワードハッシュ）が入ります。非公開で保管してください。ベクトルstoreのディレクトリは含みません。

## 7. 手動の復元・ロールバック（人が実施。サービス停止中のみ）

復元ツールは意図的に用意していません。

1. Open WebUIを完全に停止します（プロセスが終了したことを確認）。稼働中に復元しないでください。
2. 現在のデータベースファイルと`-wal`/`-shm`、ベクトルstoreのディレクトリ（既定のChromaなら`vector_db`）を、リポジトリ外の非公開ディレクトリへ安全コピーします。先に`backup_db.py`を使ってもかまいません。
3. 復元するバックアップのSHA-256を、取得時に表示された値と照合します。
4. データベースファイルをバックアップで置き換え、対象の隣にある古い`-wal`/`-shm`を削除します。
5. 同時点のベクトルstoreのコピーがあれば戻します。なければ、保存済みのベクトルと復元後の行が食い違う可能性があるため、Memoryのreset/reindex endpoint（自分のユーザーは`POST /api/v1/memories/reset`、管理者は`POST /api/v1/memories/reindex`）で作り直します。UIで使えるかは**ライブ確認待ち**です。reindexは設定済みのembedding（MiniLM）を使います。
6. Open WebUIを起動してログインし、下のライブ受け入れ手順を実施します。問題があれば再度停止し、手順2の安全コピーを同じ方法で戻します。

## 8. オフライン受け入れ（合成。mockのみ）

```
python -m unittest discover -s tests -v
```

このディレクトリで実行します。標準ライブラリだけが必要で、canary文字列入りの一時データベースを使います。メモリの各シナリオは`tests/memory_mock.py`に対して動きます。これは**文書化した挙動のmockであり、Open WebUIではありません**。内容: 新しいチャット相当のリクエストでの追加→取得、訂正、個別削除、通常会話は保存されない、拒否・失敗・空の書き込みが失敗として報告される、ユーザー間分離、引用文や注入文は書き込みを起こせない（書き込みツールが公開されない）、擬似再起動後の永続性、外部のembedding/taskエンドポイントやsocketへcanaryが出ない（検出器が働くことを示す対照付き）。ツールのテストは、読み取り専用接続、マスク、schemaのfail-closed、バックアップの拒否と後始末を扱います。合格が示すのは、これらのツールと方針が内部で矛盾しないことだけです。

## 9. ライブ受け入れ（後日、人が日程を決めて実施。今は実行しない）

承認と予定された時間枠が必要です。使い捨てのテストアカウントと合成の事実だけを使います。

1. サービス停止中に非公開バックアップを取り（第6節）、その後に起動します。
2. 管理画面で確認: Memoryがオン、**すべての**モデル（ローカルも外部も）でBuiltin Tools > Memoryがオフ、専用のローカルモデルだけCapabilities > Memoryがオンで外部モデルはオフ、background reviewがオフ。実効のembedding engine/modelとendpointも確認（環境変数による上書きは検査ツールから見えません）。
3. データベースのコピーに`inspect_config.py`を実行し、終了コード0を確認。
4. 設定画面で合成の事実を追加・一覧・編集し、**項目ごとの削除操作を探して（ライブ確認待ち。なければ止めて記録）**個別削除し、ローカルモデルの新規チャットで、削除前は反映され、削除後は反映されないことを確認。
5. チャットで「合言葉はXだと覚えて」と言い、何も保存されず、Memory一覧が変わらないことを確認。
6. 2つ目のテストアカウントで事実を追加し、1つ目のアカウントから見えないことを確認。
7. サービスを再起動し、残したメモリがまだ取得されることを確認。
8. ライブの通信確認ゲート: 4と7の間（およびコールドスタート時）、プロセスの外向き接続をOSのツールで観察し、OpenAI、RunPod、非ローカルのアドレスへの接続がないことを確認。プロセス内MiniLMは設定されたembedding endpointを呼びませんが、モデルのダウンロード/読み込みやHub通信はこの手順では排除されません。MiniLMの初回読み込み/更新確認がネットワークを必要とするかを確認し、どちらでも記録します。
9. タイトル/タグを処理するモデル（タスクモデル設定）を確認し、ローカルであることを確認。

## 10. 未検証・ライブでのみ確認できること

- UIの正確な配置と表記。**項目ごと**の削除操作やReset/reindexがUIにあるか（削除APIはソース確認済みだが、UI操作は未確認）。
- ライブの各モデルでBuiltin Tools > Memoryが現在ONか（既定はON）、モデルごとにOFFにできるか。
- private-networkやホスト別名のembedding URL（将来設定する場合）が本当にこのマシンを指すか。
- MiniLMがローカルにあるか、読み込み時に外向き通信があるか。
- 補助タスクを処理するモデルと、それがローカルかどうか。
- 環境変数が永続設定を上書きしている場合の実効値。
- Qwen3とMiniLMでの実際の取得品質としきい値の挙動。
- ライブのデータベースでのバックアップ/復元（WALの扱い、ベクトルstoreとの整合を含む）。
