# Open WebUI 0.11.4: ローカルMemoryガードと確認付き保存ツール

この資料はOpen WebUI 0.11.4に限定した再利用用の参考資料です。自動Memoryコンテキストのサーバー側ルート確認と、ユーザー確認後に保存するツールを含みます。実機の稼働状況は含まず、テストは合成データだけを使います。

## 使用前の設定

1. 対象バージョンのOpen WebUIソースを確認し、一致するソースだけに`context-guard/memory.py.patch`を適用してください。これはコンテキストなしのパッチなので、対応ツールで適用し、結果を確認してください。
2. 2つのPythonモジュールとパッチにある`YOUR_LOCAL_OLLAMA_MODEL_ID`を、自分の環境の正確なローカルモデルIDに置換してください。ローカル経路とloopback前提を確認してください。
3. 全ての書き込みを明示確認経由にする場合、全モデルで組み込みMemoryツールを無効にします。**Confirmed Memory Save**は対象ローカルモデルだけに割り当てます。Memoryコンテキスト機能も、ユーザーのMemoryを受け取ってよいローカルモデルだけ有効にし、外部モデルでは無効にします。
4. 実機変更前に、アプリDBとベクトルストアを整合性のある形で個人用バックアップへ保存します。既存データとプロバイダー設定を保持してください。
5. **Workspace > Tools > Import JSON**で`confirmed-memory-tool/confirmed_memory_tool.import.json`を読み込みます。その後、**Workspace > Models**から対象ローカルモデルだけにツールを割り当てます。
6. インストール前に合成テストを実行します。実機確認には合成データを使い、実効設定をUIで確認してください。

このガードが対象にするのは自動コンテキスト注入経路です。組み込みMemoryツール、バックグラウンドレビュー、補助モデルの経路、実効設定は別経路の場合があります。ローカル限定ポリシーを前提にする前に、対象リリースを確認してください。

## 合成テスト

```sh
python -m unittest discover -s confirmed-memory-tool/tests -v
python -m unittest discover -s context-guard/tests -v
```

テストはmockと合成データだけを使います。実DBの読み取り、モデル読込、ネットワーク通信は行いません。