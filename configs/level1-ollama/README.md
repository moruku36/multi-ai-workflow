# Layer 1: Ollama / Qwen (+ Open WebUI)

手元PCのローカル環境で動作する、高速データ加工・定型処理用の構成ファイル群です。  
機密データや個人情報を外部サーバーに送信することなく、通信費ゼロで安全に処理できます。

---

## 1. 構成ファイル
- **`Modelfile`**: 定型加工に特化したパラメータ（Temperature 0.2等）と、前置きや挨拶を排除してデータ本体のみを出力するシステムプロンプトを定義。
- **`run.sh`**: Linux/Mac環境でModelfileからカスタムモデル `qwen-processor` を自動作成するシェルスクリプト。
- **`run.ps1`**: Windows (PowerShell) 環境で `qwen-processor` を自動作成するスクリプト。
- **`start-webui.bat`**: WindowsでOpen WebUIを起動するバッチファイル。
- **`launch_silent.vbs`**: Windowsで黒いコマンド画面を出さずにバックグラウンド常駐起動するスクリプト。

---

## 2. セットアップ手順

### Step 1: Ollama でモデルを作成

**Windows (PowerShell) の場合:**
```powershell
# ベースモデルを取得 (7b または 14b)
ollama pull qwen2.5:14b

# スクリプトを実行してカスタムモデルを作成
.\run.ps1
```

**Linux / macOS (Bash) の場合:**
```bash
chmod +x ./run.sh
./run.sh
```

---

### Step 2: Open WebUI（ブラウザUI）との連携

ブラウザからチャット形式で利用したい場合は、Open WebUI を導入します。

1. **起動**:
   ```powershell
   .\start-webui.bat
   ```
2. **ブラウザでアクセス**:
   `http://localhost:8080` を開きます。
3. **モデル選択**:
   画面上部のモデル選択プルダウンで **`qwen-processor`** を選んで利用します。

> **⚠️ Windows 環境での注意点 (IPv6 / IPv4)**:  
> Windows では `localhost:11434` への通信が拒否される場合があるため、Open WebUI の管理者設定（または環境変数 `OLLAMA_BASE_URL`）に `http://127.0.0.1:11434` を指定してください。