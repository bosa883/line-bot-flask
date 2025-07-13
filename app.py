from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
import os
import random
import json


app = Flask(__name__)

# LINE Bot設定
CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 現在の作業ディレクトリ
base_dir = os.path.dirname(os.path.abspath(__file__))

# OpenAIクライアント（gpt-4o-mini使用）
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# カテゴリに応じた返信文
CATEGORY_RESPONSES = {}

print("aaa")

def save_message_to_json(user_input):
    try:
        key, value = user_input.split(":::")  # 半角コロンに注意
    except ValueError:
        print("入力形式が不正です。例：場所:::東京")
        exit()
    
    # JSONファイルが存在すれば読み込み、なければ空の辞書に
    json_path = os.path.join(base_dir, "responses.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {}
    
    # 既にキーが存在する場合はリストに追加、それ以外は新しく作成
    if key in data:
        # 値がリストでなければリストに変換
        if not isinstance(data[key], list):
            data[key] = [data[key]]
        if value not in data[key]:
            data[key].append(value)
    else:
        data[key] = [value]

    # JSONファイルに書き込み
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("保存しました！")
    return

def classify_text(user_text):
    global CATEGORY_RESPONSES
    try:
        # カテゴリ一覧をキーから自動生成
        categories = "、".join(CATEGORY_RESPONSES.keys())
        print(categories)

        params = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content":f"あなたは入力をカテゴリ分類するAIです。次のカテゴリのいずれかに分類してください。：{categories}。出力はカテゴリ名だけで返してください。"
                },
                {"role": "user", "content": user_text}
            ],
            "max_tokens": 10,
            "temperature": 0.3,
        }
        response = client.chat.completions.create(**params)

        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI API呼び出しエラー:", e)
        return "雑談・その他"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global CATEGORY_RESPONSES

    with open(os.path.join(base_dir, "responses.json"), encoding="utf-8") as f:
        CATEGORY_RESPONSES = json.load(f)

    user_msg = event.message.text
    category = classify_text(user_msg)

    print(f"分類結果: {category}")  # ← デバッグ用

    if ":::" in user_msg:
        save_message_to_json(user_msg)
        reply_text = "、".join(CATEGORY_RESPONSES.keys())
    else:
        responses = CATEGORY_RESPONSES.get(category, [user_msg])
        reply_text = random.choice(responses)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))