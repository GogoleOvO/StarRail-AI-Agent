import streamlit as st
import os
import json
import datetime
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_chroma import Chroma

# ================= 1. 动态绝对路径 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "clean_message", "characters_clean_04.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_guides_db")

# ================= 2. 历史记录操作 =================
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
os.makedirs(HISTORY_DIR, exist_ok=True)


def get_all_chat_files():
    if not os.path.exists(HISTORY_DIR): return []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    files.sort(reverse=True)  # 按时间倒序
    return files


def load_chat(chat_filename):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_chat(chat_filename, messages):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)


def delete_chat(chat_filename):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    if os.path.exists(file_path):
        os.remove(file_path)


# ================= 3. 核心工具定义 =================
@tool
def get_character_basic_stats(character_name: str) -> str:
    """查询星铁角色的基础档案和满级属性面板。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        for char in chars:
            if char.get("name") == character_name:
                return f"角色：{char.get('name')} ({char.get('rarity')}星)\n命途：{char.get('path_cn')}\n属性：{char.get('element_cn')}\n{char.get('level_80_stats', '')}"
        return f"未找到 {character_name}。"
    except Exception as e:
        return f"查询失败：{e}"


@tool
def get_character_skills(character_name: str) -> str:
    """查询星铁角色的技能与天赋倍率。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        for char in chars:
            if char.get("name") == character_name:
                return f"【{character_name} 技能】\n{char.get('skills', '')}"
        return f"未找到 {character_name}。"
    except Exception as e:
        return f"查询失败：{e}"


@tool
def get_character_constellations(character_name: str) -> str:
    """查询星铁角色的星魂（命座）效果。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        for char in chars:
            if char.get("name") == character_name:
                return f"【{character_name} 星魂】\n{char.get('ranks', '')}"
        return f"未找到 {character_name}。"
    except Exception as e:
        return f"查询失败：{e}"


@tool
def search_game_guide(character_name: str, category: str) -> str:
    """查询星铁角色的攻略。category 只能填这四个词之一：推荐光锥、推荐遗器、推荐配队、角色背景。"""
    print(f"\n🚨🚨🚨 [Agent成功调用RAG工具] 角色={character_name}, 分类={category}")
    try:
        embed = OpenAIEmbeddings(
            model="text-embedding-v3",
            api_key=os.environ.get("ALY_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            check_embedding_ctx_length=False
        )
        vector_store = Chroma(
            collection_name="game_guides",
            embedding_function=embed,
            persist_directory=CHROMA_PATH
        )

        if category in ["推荐光锥", "推荐遗器", "推荐配队", "角色背景"]:
            filter_dict = {
                "$and": [
                    {"character": character_name},
                    {"category": category}
                ]
            }
        else:
            filter_dict = {"character": character_name}

        print(f"🚨 [数据库检索条件] filter={filter_dict}")

        results = vector_store.similarity_search(f"{character_name} {category}", k=3, filter=filter_dict)

        print(f"🚨 [数据库返回结果] 找到了 {len(results)} 条数据")

        if not results:
            return f"未找到【{character_name}】的【{category}】数据。"

        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"搜索攻略失败：{e}"


# ================= 4. 初始化 Agent =================
@st.cache_resource
def get_agent():
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        temperature=0,
        streaming=True
    )

    tools = [get_character_basic_stats, get_character_skills, get_character_constellations, search_game_guide]

    system_prompt = """
    你是一个极其专业、回答简练的《崩坏：星穹铁道》游戏助手。

    【工具调用规则】
    1. 查面板属性：调用 get_character_basic_stats。
    2. 查技能倍率：调用 get_character_skills。
    3. 查命座星魂：调用 get_character_constellations。
    4. 查搭配攻略：调用 search_game_guide。
       - 🚨 必须严格按照以下映射传参：
       - 问“光锥”，category 传 "推荐光锥"。
       - 问“遗器”，category 传 "推荐遗器"。
       - 问“配队”，category 传 "推荐配队"。
       - 问“故事/背景”，category 传 "角色背景"。

    【绝对回答规则】
    - 必须精准作答，查不到就说“知识库未收录”，绝不瞎编。
    """

    return create_agent(model=llm, tools=tools, system_prompt=system_prompt)


agent = get_agent()

# ================= 5. 页面与侧边栏设置 =================
st.set_page_config(page_title="星铁 AI 助手", page_icon="🚂", layout="wide")
st.title("🚂 星铁 AI 攻略助手")

# 初始化当前对话
if "current_chat_id" not in st.session_state:
    all_files = get_all_chat_files()
    if all_files:
        st.session_state.current_chat_id = all_files[0]
    else:
        new_id = datetime.datetime.now().strftime("对话_%Y-%m-%d_%H-%M-%S.json")
        st.session_state.current_chat_id = new_id
        save_chat(new_id, [])

with st.sidebar:
    st.header("💬 聊天记录")

    # 新建对话
    if st.button("➕ 开启新对话", use_container_width=True):
        new_id = datetime.datetime.now().strftime("对话_%Y-%m-%d_%H-%M-%S.json")
        st.session_state.current_chat_id = new_id
        save_chat(new_id, [])
        st.rerun()

    st.divider()

    # 🌟 渲染历史列表（带删除功能）
    all_files = get_all_chat_files()
    for filename in all_files:
        is_current = (filename == st.session_state.current_chat_id)
        display_name = filename.replace(".json", "").replace("_", " ").replace("-", ":", 2)

        # 将侧边栏分成两列：左边 85% 放对话名，右边 15% 放删除按钮
        col1, col2 = st.columns([0.85, 0.15])

        with col1:
            # 点击进入对话
            if st.button(display_name, key=f"btn_{filename}", use_container_width=True,
                         type="primary" if is_current else "secondary"):
                st.session_state.current_chat_id = filename
                st.rerun()

        with col2:
            # 点击删除按钮
            if st.button("🗑️", key=f"del_{filename}", help="删除该对话"):
                # 1. 从磁盘删除文件
                delete_chat(filename)

                # 2. 如果删除的是当前正在看的对话，需要重置状态
                if st.session_state.current_chat_id == filename:
                    remaining_files = get_all_chat_files()
                    if remaining_files:
                        st.session_state.current_chat_id = remaining_files[0]
                    else:
                        # 如果全删光了，自动新建一个
                        new_id = datetime.datetime.now().strftime("对话_%Y-%m-%d_%H-%M-%S.json")
                        st.session_state.current_chat_id = new_id
                        save_chat(new_id, [])

                # 3. 刷新页面
                st.rerun()

# ================= 6. 主界面渲染 =================
current_messages = load_chat(st.session_state.current_chat_id)

for msg in current_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ================= 7. 接收输入并流式输出 =================
if prompt := st.chat_input("问问关于星铁的问题..."):
    current_messages.append({"role": "user", "content": prompt})
    save_chat(st.session_state.current_chat_id, current_messages)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        try:
            input_messages = [{"role": m["role"], "content": m["content"]} for m in current_messages][-10:]

            for chunk in agent.stream({"messages": input_messages}, stream_mode="messages"):
                msg_chunk, metadata = chunk
                if msg_chunk.content:
                    full_response += msg_chunk.content
                    response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)
            current_messages.append({"role": "assistant", "content": full_response})
            save_chat(st.session_state.current_chat_id, current_messages)

        except Exception as e:
            st.error(f"发生错误：{e}")