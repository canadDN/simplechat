# lambda/index.py
import json
import os
import boto3
import requests  # 追加: FastAPI へ HTTP リクエストを投げるため
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    try:
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        print("Using model:", MODEL_ID)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        

        # ── ここから FastAPI 呼び出し用に置き換え ──

        # ② 会話履歴をプロンプト文字列に変換
        prompt = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)

        # ③ 環境変数またはハードコードで FastAPI のエンドポイントを指定
        api_url = os.environ.get(
            "FASTAPI_URL",
            "https://6ef5-35-201-169-56.ngrok-free.app/generate"
        )

        # ④ FastAPI の仕様に合わせたペイロードを構築
        request_payload = {
            "prompt": prompt,
            "max_new_tokens": 15,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }

        print("Calling FastAPI /generate with payload:", json.dumps(request_payload))

        # ⑤ HTTP POST 実行
        response = requests.post(api_url, json=request_payload)
        print("FastAPI response status:", response.status_code, "body:", response.text)

        # ステータスコードチェック
        if response.status_code != 200:
            raise Exception(f"FastAPI error {response.status_code}: {response.text}")

        # レスポンス JSON をパース
        result = response.json()
        assistant_response = result.get("generated_text")
        if assistant_response is None:
            raise Exception("No generated_text in FastAPI response")

        # 会話履歴にアシスタントの応答を追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })

        # ── ここまで置き換え ──




        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
