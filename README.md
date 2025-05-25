# GitLab Code Review 

このプロジェクトは、GitLabのマージリクエスト（MR）から差分情報を取得し、OpenAIのAPIを使用して自動コードレビューを実施します。レビュー結果はマークダウン形式で出力され、API呼び出しのログはJSON形式で保存されます。

## 機能概要

- **GitLab API連携**: 指定されたMRの差分情報を取得。
- **OpenAI API連携**: 差分情報をもとにコードレビューを実行。
- **レビュー観点のカスタマイズ**: JSONファイルからレビュー観点を読み込み可能。
- **結果の保存**: レビュー結果をマークダウン形式で保存し、API呼び出しのログをJSON形式で記録。

## プロジェクト構成

```
code_review/
├── code_review.py           # メインスクリプト
├── constants.py             # 定数定義
├── review_perspectives.json # レビュー観点を定義したJSONファイル
├── system_prompt.txt        # OpenAI API用のシステムプロンプト
│── api_call_logs_*.json     # API呼び出しログ
└── review_results_*.md      # レビュー結果
```

## 必要な環境変数

以下の環境変数を設定してください：

- `GITLAB_TOKEN`: GitLab APIの認証トークン
- `OPENAI_API_KEY`: OpenAI APIの認証キー

## 依存ライブラリ

このプロジェクトは以下のPythonライブラリに依存しています：

- `requests`
- `tiktoken`
- `openai`

依存ライブラリは以下のコマンドでインストールできます：

```bash
pip install -r requirements.txt
```

## 使用方法

1. **レビュー観点の設定**  
   `review_perspectives.json` にレビュー観点を記述します。

2. **システムプロンプトの設定**  
   `system_prompt.txt` にOpenAI API用のプロンプトを記述します。
   {file_name} : GitLabのMR情報から取得したファイル名
   {diff_info} : GitLabのMR情報から取得した差分情報

3. **プロジェクトIDの設定**  
   実行前に、`constants.py` 内の `PROJECT_ID` を対象のGitLabプロジェクトIDに設定してください。

   ```python
   PROJECT_ID = <your_project_id_here>  # GitLabのプロジェクトID(数値)を設定
   ```

4. **スクリプトの実行**  
   以下のコマンドを実行して、指定したMRのコードレビューを実行します：

   ```bash
   python code_review.py --mr_iid <MR_IID>
   ```

   - `<MR_IID>`: 対象のマージリクエストIDを指定してください。

5. **出力結果の確認**  
   - レビュー結果: `review_results_<timestamp>.md`
   - API呼び出しログ: `api_call_logs_<timestamp>.json`

## 注意事項

- GitLab APIやOpenAI APIの利用には、それぞれのAPIキーが必要です。
- 差分情報の取得やレビュー観点の設定は、プロジェクトの要件に応じてカスタマイズしてください。