from fastapi import FastAPI
from pydantic import BaseModel
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

app = FastAPI(title="星铁 AI 后端接口")


class ChatRequest(BaseModel):
    message: str


# 🚨 1. 初始化大模型
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0
)


@app.get("/")
def read_root():
    return {"status": "success"}


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 🚨 2. 组装消息
    messages = [
        SystemMessage(content="你是一个星铁助手。如果问原神或天气，请回答不知道。如果问三月七速度，回答101。"),
        HumanMessage(content=request.message)
    ]

    # 🚨 3. 调用大模型（这就是真正在算的地方）
    try:
        response = llm.invoke(messages)
        ai_text = response.content
    except Exception as e:
        ai_text = f"AI服务异常：{e}"

    # 🚨 4. 返回结果，注意键名必须是 ai_reply，和 eval.py 对应
    return {
        "code": 200,
        "user_query": request.message,
        "ai_reply": ai_text
    }