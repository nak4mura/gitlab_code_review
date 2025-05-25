import os
import json
import requests
import argparse
import tiktoken
from constants import GITLAB_URL, GIT_API_PER_PAGE, PROJECT_ID, MODEL_NAME, TEMPERATURE, MAX_TOKENS, TIKTOKEN_MODEL, TOKENS_PER_MESSAGE, TOKENS_PER_NAME
from datetime import datetime
from openai import OpenAI

PRIVATE_TOKEN = os.getenv("GITLAB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HEADERS = {
    "PRIVATE-TOKEN": PRIVATE_TOKEN
}

CLIENT = OpenAI(api_key=OPENAI_API_KEY)
TIKTOKEN_ENCODING = tiktoken.encoding_for_model(TIKTOKEN_MODEL)

def load_review_perspectives(file_path="review_perspectives.json") -> list:
    """
    レビュー観点をJSONファイルから読み込む。

    Args:
        file_path (str): レビュー観点が記載されたJSONファイルのパス。

    Returns:
        list: レビュー観点のリスト。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_system_prompt(file_path="system_prompt.txt") -> str:
    """
    システムプロンプトをテキストファイルから読み込む。

    Args:
        file_path (str): システムプロンプトが記載されたテキストファイルのパス。

    Returns:
        str: システムプロンプトの内容。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def num_tokens_from_messages(messages) -> int:
    """
    メッセージからトークン数を計算する。

    Args:
        messages (list): メッセージのリスト。

    Returns:
        int: メッセージに含まれるトークン数。
    """
    num_tokens = 0
    for message in messages:
        num_tokens += TOKENS_PER_MESSAGE
        for key, value in message.items():
            num_tokens += len(TIKTOKEN_ENCODING.encode(value))
            if key == "name":
                num_tokens += TOKENS_PER_NAME
    num_tokens += 3  # assistantの返信の開始トークン
    return num_tokens

def call_openai_chat_api(messages: list, model: str, temperature: float, max_tokens: int) -> str:
    """
    OpenAIのChat APIを呼び出す関数。

    Args:
        messages (list): APIに送信するメッセージリスト。
        model (str): 使用するモデル名。
        temperature (float): 出力の多様性を制御する温度パラメータ。
        max_tokens (int): 最大トークン数。

    Returns:
        str: OpenAI APIからのレスポンス。
    """
    response = CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content

def review_code(review_perspective: str, file_name: str, diff_info: str, log_file: str) -> str:
    """
    指定された観点でコードレビューを実行し、結果をログに記録する。

    Args:
        review_perspective (str): レビュー観点。
        file_name (str): 対象ファイル名。
        diff_info (str): 差分情報。
        log_file (str): ログを保存するファイル名。

    Returns:
        str: レビュー結果。
    """
    # ファイル名と差分情報でシステムプロンプトをフォーマット
    current_system_prompt = load_system_prompt().format(file_name=file_name, diff_info=diff_info)
    messages = [
        {"role": "system", "content": current_system_prompt},
        {"role": "user", "content": review_perspective}
    ]

    start_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")
    # OpenAI APIを呼び出してレビュー結果を取得
    response_str = call_openai_chat_api(
        messages=messages,
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    end_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")

    log_data = {
        "file_name": file_name,
        "diff_content": diff_info,
        "review_perspective": review_perspective,
        "request_tokens": num_tokens_from_messages(messages),
        "api_params": {"model": MODEL_NAME, "temperature": TEMPERATURE},
        "response": response_str,
        "response_tokens": len(TIKTOKEN_ENCODING.encode(response_str)),
        "start_time": start_time,
        "end_time": end_time,
    }

    # 既存のログデータをロード（なければ空リストを使う）
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                existing_logs = json.load(f)
            except json.JSONDecodeError:
                existing_logs = []
    else:
        existing_logs = []

    # 新しいログデータを追加
    existing_logs.append(log_data)
    
    # ログをJSON形式で保存
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(existing_logs, f, ensure_ascii=False, indent=4)
    return response_str

def get_mr_info(mr_iid) -> list:
    """
    GitLabのマージリクエスト情報を取得する。

    Args:
        mr_iid (int): マージリクエストのIID。

    Returns:
        list: マージリクエストの差分情報リスト。
    """
    base = f"{GITLAB_URL}/api/v4"
    # 1. MR基本情報
    mr_api_base_url = f"{base}/projects/{PROJECT_ID}/merge_requests/{mr_iid}"
    # 2. 差分情報（Diff）
    #    MRの差分情報を取得するエンドポイント
    diffs_endpoint_url = f"{mr_api_base_url}/diffs"

    all_diffs = []
    current_page = 1

    while True:
        params = {"page": current_page, "per_page": GIT_API_PER_PAGE}
        response = requests.get(diffs_endpoint_url, headers=HEADERS, params=params)
        try:
            response.raise_for_status()  # HTTPエラーがあれば例外を発生させる
        except requests.exceptions.HTTPError as e:
            print(f"APIリクエストに失敗しました: {e}")
            break 
        try:
            page_data = response.json()
        except requests.exceptions.JSONDecodeError:
            print(f"APIレスポンスのJSONデコードに失敗しました。ステータス: {response.status_code}, 本文: {response.text}")
            break
        if not isinstance(page_data, list):
            print(f"APIが差分情報のリストを返しませんでした。レスポンス: {page_data}")
            break
        if not page_data:  # 現在のページにデータがなければ、全ページ取得済み
            break

        all_diffs.extend(page_data)

        # x-total-pages ヘッダーで総ページ数を確認 (存在する場合)
        total_pages_header = response.headers.get("x-total-pages")
        if total_pages_header and current_page >= int(total_pages_header):
            break # 最後のページまで到達
        current_page += 1
    return all_diffs

def main():
    """
    コマンドライン引数で指定したマージリクエストのIIDからGitLab APIで差分情報を取得し、
    その差分情報をOpenAI APIに送信してレビュー結果をマークダウン形式で出力する。
    """
    # コマンドライン引数を解析
    parser = argparse.ArgumentParser(description="GitLab MR情報を取得してコードレビューを実行します。")
    parser.add_argument("--mr_iid", type=int, required=True, help="マージリクエストのIIDを指定してください。")
    args = parser.parse_args()

    # GitLab MR情報を取得
    diffs = get_mr_info(args.mr_iid)
    # レビュー観点をロード
    review_perspectives = load_review_perspectives()
    
    # 出力ファイルの末尾に付与する現在時刻を取得してフォーマット
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # レビュー結果出力ファイル名とログファイル名を生成
    output_file = f"review_results_{timestamp}.md"
    log_file = f"api_call_logs_{timestamp}.json"
    
    # 各DIFFに対してレビューを実行
    with open(output_file, "a", encoding="utf-8") as f:
        for diff in diffs:
            file_name = diff['new_path']
            diff_info = diff['diff']
            if not diff_info:
                continue
            f.write(f"# レビュー対象：{file_name}\n")
            for perspective in review_perspectives:
                f.write(f"## レビュー観点：{perspective}\n")
                review_result = review_code(perspective, file_name, diff_info, log_file)
                f.write(f"{review_result}\n")

if __name__ == "__main__":
    main()
