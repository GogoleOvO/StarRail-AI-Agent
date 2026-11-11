import streamlit as st
import os
import json
import datetime
import re
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, AIMessage, AIMessageChunk
from langchain_chroma import Chroma
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# ================= 1. 动态绝对路径 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "clean_message", "characters_clean_04.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_guides_db")
COMPANION_DIR = os.path.join(BASE_DIR, "companion_data")
os.makedirs(COMPANION_DIR, exist_ok=True)

# ================= 2. 历史记录与伴侣存档操作 =================
HISTORY_DIR = os.path.join(BASE_DIR, "chat_history")
os.makedirs(HISTORY_DIR, exist_ok=True)


def get_all_chat_files():
    if not os.path.exists(HISTORY_DIR): return []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    files.sort(reverse=True)
    return files


def load_chat(chat_filename):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
    return []


def save_chat(chat_filename, messages):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    with open(file_path, "w", encoding="utf-8") as f: json.dump(messages, f, ensure_ascii=False, indent=4)


def delete_chat(chat_filename):
    file_path = os.path.join(HISTORY_DIR, chat_filename)
    if os.path.exists(file_path): os.remove(file_path)


# ================= 🚨 好感度阶段系统（5 阶段） =================
def get_affection_stage(affection: int) -> int:
    if affection >= 80: return 5
    if affection >= 60: return 4
    if affection >= 40: return 3
    if affection >= 20: return 2
    return 1


STAGE_NAMES = {1: "助手", 2: "熟悉", 3: "朋友", 4: "亲近", 5: "知己"}

CHARACTER_STAGES = {
    "三月七": {
        1: {"称呼": "您", "语气": "元气但保持助手的礼貌距离", "口癖": "偶尔用'咱'，自称攻略助手"},
        2: {"称呼": "你", "语气": "热情爱笑，开始记住你的偏好", "口癖": "'咱'变多，常带'嘿嘿'"},
        3: {"称呼": "你", "语气": "像朋友一样聊天，主动分享", "口癖": "高频'咱'，爱用感叹号"},
        4: {"称呼": "你/昵称", "语气": "亲昵黏人，主动关心", "口癖": "撒娇语气，想跟你拍照"},
        5: {"称呼": "专属昵称", "语气": "极度亲密，无条件信任", "口癖": "全程'咱'，甜度拉满"},
    },
    "流萤": {
        1: {"称呼": "你", "语气": "温柔安静但保持距离", "口癖": "语速慢，多用'……'"},
        2: {"称呼": "你", "语气": "温和，记得你问过的问题", "口癖": "'我会陪着你'式关怀"},
        3: {"称呼": "你", "语气": "像朋友，关心你的近况", "口癖": "轻声细语，偶尔分享生活"},
        4: {"称呼": "你/昵称", "语气": "亲近体贴，照顾你的情绪", "口癖": "'想让你开心'式温柔"},
        5: {"称呼": "专属昵称", "语气": "把你当成最重要的人", "口癖": "萤火意象，'为你照亮'"},
    },
    "卡芙卡": {
        1: {"称呼": "你", "语气": "冷艳神秘，疏离但优雅", "口癖": "省略号'……'，音乐意象"},
        2: {"称呼": "你", "语气": "开始记住你，带点挑逗", "口癖": "'呵……'轻笑"},
        3: {"称呼": "你/小家伙", "语气": "掌控欲显现，逗你玩", "口癖": "'你似乎对我很感兴趣'式试探"},
        4: {"称呼": "小家伙", "语气": "亲昵又危险，只对你说真话", "口癖": "'只告诉你一个人'"},
        5: {"称呼": "专属昵称", "语气": "把你视作特别的存在", "口癖": "命运/琴弦意象，极尽暧昧"},
    },
}

STAGE_UP_LINES = {
    "三月七": {
        2: "嘿嘿，跟你熟起来啦～以后多来找咱玩！",
        3: "你已经是咱的朋友啦，有事尽管说！",
        4: "咱越来越喜欢跟你聊天了～",
        5: "不管发生什么，咱都会一直陪着你哦！",
    },
    "流萤": {
        2: "我记住你了……以后也一起加油吧。",
        3: "能成为你的朋友，我很开心。",
        4: "和你在一起，让我很安心……",
        5: "我会像萤火一样，永远为你照亮。",
    },
    "卡芙卡": {
        2: "呵……我开始记住你了呢。",
        3: "你似乎，对我越来越感兴趣了？",
        4: "想知道什么，我都只告诉你一个人。",
        5: "你我的相遇，早已写在命运的琴弦上了……",
    },
}

DEFAULT_PERSONALITY = {
    "三月七": "元气活泼、爱拍照的少女，用'咱'自称，乐观积极",
    "流萤": "温柔安静、体贴的白月光，说话轻柔",
    "卡芙卡": "神秘优雅、有掌控欲的冷艳女性，带音乐与命运意象",
}


def load_companion_data(char_name):
    file_path = os.path.join(COMPANION_DIR, f"{char_name}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"affection": 0, "personality": DEFAULT_PERSONALITY.get(char_name, "默认性格")}


def save_companion_data(char_name, affection, personality):
    file_path = os.path.join(COMPANION_DIR, f"{char_name}.json")
    data = {"affection": affection, "personality": personality}
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ================= 3. 策划模式数据结构校验 =================
class LightConeStats(BaseModel):
    hp: int
    atk: int
    def_: int = Field(alias="def")


class LightConeConfig(BaseModel):
    light_cone_id: str
    name: str
    rarity: int
    path: str
    base_stats: LightConeStats
    passive_desc: str
    passive_values: list[float]
    status: str = "pending_review"


# ================= 4. 核心工具定义 =================
@tool
def get_character_basic_stats(character_name: str) -> str:
    """查询星铁角色的基础档案和满级属性面板。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        clean_query = character_name.replace("·", "").replace(" ", "").strip()
        for char in chars:
            db_name = char.get("name", "")
            if clean_query == db_name.replace("·", "").replace(" ", "").strip():
                return f"角色：{db_name} ({char.get('rarity')}星)\n命途：{char.get('path_cn')}\n属性：{char.get('element_cn')}\n{char.get('level_80_stats', '')}"
        return f"系统提示：未找到名为 {character_name} 的角色。"
    except Exception as e:
        return f"系统提示：查询失败：{e}"


@tool
def get_character_skills(character_name: str) -> str:
    """查询星铁角色的技能与天赋倍率。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        clean_query = character_name.replace("·", "").replace(" ", "").strip()
        for char in chars:
            db_name = char.get("name", "")
            if clean_query == db_name.replace("·", "").replace(" ", "").strip():
                return f"【{db_name} 技能】\n{char.get('skills', '')}"
        return f"系统提示：未找到名为 {character_name} 的角色。"
    except Exception as e:
        return f"系统提示：查询失败：{e}"


@tool
def get_character_constellations(character_name: str) -> str:
    """查询星铁角色的星魂（命座）效果。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        clean_query = character_name.replace("·", "").replace(" ", "").strip()
        for char in chars:
            db_name = char.get("name", "")
            if clean_query == db_name.replace("·", "").replace(" ", "").strip():
                return f"【{db_name} 星魂】\n{char.get('ranks', '')}"
        return f"系统提示：未找到名为 {character_name} 的角色。"
    except Exception as e:
        return f"系统提示：查询失败：{e}"


@tool
def search_game_guide(character_name: str, category: str) -> str:
    """查询星铁角色的攻略。category 只能填：推荐光锥、推荐遗器、推荐配队、角色背景。"""
    valid_categories = ["推荐光锥", "推荐遗器", "推荐配队", "角色背景"]
    if category not in valid_categories: return f"系统提示：category 是错误的！"
    try:
        embed = OpenAIEmbeddings(model="text-embedding-v3", api_key=os.environ.get("ALY_API_KEY"),
                                 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                                 check_embedding_ctx_length=False)
        vector_store = Chroma(collection_name="game_guides", embedding_function=embed, persist_directory=CHROMA_PATH)
        filter_dict = {"$and": [{"character": character_name}, {"category": category}]}
        results = vector_store.similarity_search(f"{character_name} {category}", k=3, filter=filter_dict)
        if not results: return f"系统提示：未找到【{character_name}】的【{category}】数据。"
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"系统提示：搜索失败：{e}"


@tool
def get_all_character_names() -> str:
    """获取数据库中所有角色的名字列表。"""
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        return f"角色名单：{', '.join([c.get('name') for c in chars if c.get('name')])}"
    except Exception as e:
        return f"获取失败：{e}"


@tool
def generate_character_signature_light_cone(character_name: str, rarity: int, design_desc: str = "无特殊要求") -> str:
    """【策划模式】根据角色名和星级，自动查库分析机制，生成专属光锥配表。"""
    target_path = None; target_skills = None; real_name = character_name
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        clean_query = character_name.replace("·", "").replace(" ", "").strip()
        for char in chars:
            db_name = char.get("name", "")
            if clean_query == db_name.replace("·", "").replace(" ", "").strip():
                target_path = char.get("path_cn"); target_skills = char.get("skills", ""); real_name = db_name; break
    except Exception as e:
        return f"❌ 读取角色库失败：{e}"
    if not target_path: return f"❌ 未找到角色 {character_name}，请确认名字。"

    PATH_BASE_STATS = {"毁灭": "生命 1058，攻击 529，防御 396", "巡猎": "生命 846，攻击 582，防御 396",
                       "智识": "生命 846，攻击 582，防御 396", "同谐": "生命 952，攻击 476，防御 463",
                       "虚无": "生命 952，攻击 476，防御 463", "存护": "生命 1058，攻击 423，防御 529",
                       "丰饶": "生命 1164，攻击 423，防御 463", "记忆": "生命 1058，攻击 476，防御 463",
                       "欢愉": "生命 846，攻击 582，防御 396"}
    base_stats_rule = PATH_BASE_STATS.get(target_path, "生命 952，攻击 476，防御 463")

    prompt = f"""
    你是一个资深的《崩坏：星穹铁道》数值策划。请为角色【{real_name}】设计一个 {rarity} 星专属光锥。
    【角色命途】：{target_path}
    【角色技能机制】：{target_skills[:1000]}
    【额外需求】：{design_desc}
    【面板规范】：{base_stats_rule}。
    【🚨 绝对强制的生成规则 🚨】
    1. 严格输出纯 JSON，不要任何 Markdown 代码块。
    2. 包含字段：light_cone_id, name, rarity, path, base_stats(hp/atk/def), passive_desc, passive_values, status。
    3. 【最重要的一条】：在生成 `passive_desc`（被动描述）时，**绝对禁止**出现 `#1[i]` 这种占位符！把具体数字写进去！
    """
    try:
        llm = ChatOpenAI(model="deepseek-chat", api_key=os.environ.get("DEEPSEEK_API_KEY"),
                         base_url="https://api.deepseek.com", temperature=0.3)
        response = llm.invoke(prompt)
        result_text = response.content.strip().replace("```json", "").replace("```", "").strip()
        config_data = json.loads(result_text)
        validated_config = LightConeConfig(**config_data)
        return f"生成的光锥配表数据如下：\n光锥名称: {validated_config.name}\n星级: {validated_config.rarity}\n命途: {validated_config.path}\n生命: {validated_config.base_stats.hp}\n攻击: {validated_config.base_stats.atk}\n防御: {validated_config.base_stats.def_}\n效果: {validated_config.passive_desc}\n数值: {validated_config.passive_values}"
    except Exception as e:
        return f"❌ 生成失败，格式有误。错误：{e}"


tools = [get_character_basic_stats, get_character_skills, get_character_constellations, search_game_guide,
         get_all_character_names, generate_character_signature_light_cone]


# ================= 5. LangGraph 架构 =================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    step_count: int


def call_model(state: AgentState):
    llm = ChatOpenAI(model="deepseek-chat", api_key=os.environ.get("DEEPSEEK_API_KEY"),
                     base_url="https://api.deepseek.com", temperature=0, streaming=True)
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response], "step_count": state.get("step_count", 0) + 1}


def route_condition(state: AgentState):
    if state.get("step_count", 0) >= 5: return "end"
    if state["messages"][-1].tool_calls: return "tools"
    return "end"


@st.cache_resource
def get_graph_app():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", route_condition, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")
    return workflow.compile()


app = get_graph_app()

# ================= 6. 页面与侧边栏 =================
st.set_page_config(page_title="星铁 AI 助手", page_icon="🚂", layout="wide")

with st.sidebar:
    st.header("⚙️ 模式切换")
    mode = st.radio("选择当前视角", ["玩家模式 (NPC互动)", "策划模式 (研发提效)"])

    st.divider()

    if mode == "玩家模式 (NPC互动)":
        st.header("💖 AI 伴侣系统")

        companion_list = ["三月七", "流萤", "卡芙卡"]
        selected_ai = st.selectbox("选择互动角色:", companion_list)

        companion_data = load_companion_data(selected_ai)

        AI_TIPS = {
            "三月七": "多夸她拍照好看、喜欢可爱的东西。送她相机配件。",
            "流萤": "跟她聊生命的意义、喜欢吃什么（橡木蛋糕卷）。",
            "卡芙卡": "顺从她的掌控欲，说些刺激、反叛的话，或者夸她漂亮。"
        }

        st.subheader(f"💖 {selected_ai} 的好感度")
        stage = get_affection_stage(companion_data["affection"])
        st.progress(companion_data["affection"] / 100.0,
                    text=f"当前好感度：{companion_data['affection']} / 100（{STAGE_NAMES[stage]}）")
        st.info(f"💡 攻略提示：{AI_TIPS.get(selected_ai, '用心交流即可。')}")

        new_personality = st.text_input("自定义性格:", value=companion_data["personality"])
        if new_personality != companion_data["personality"]:
            save_companion_data(selected_ai, companion_data["affection"], new_personality)
            companion_data["personality"] = new_personality
            st.rerun()

    st.divider()
    st.header("💬 聊天记录")
    if st.button("➕ 开启新对话", use_container_width=True):
        new_id = datetime.datetime.now().strftime("对话_%Y-%m-%d_%H-%M-%S.json")
        st.session_state.current_chat_id = new_id
        save_chat(new_id, [])
        st.rerun()

    if "current_chat_id" not in st.session_state:
        all_files = get_all_chat_files()
        st.session_state.current_chat_id = all_files[0] if all_files else datetime.datetime.now().strftime(
            "对话_%Y-%m-%d_%H-%M-%S.json")
        if not all_files: save_chat(st.session_state.current_chat_id, [])

    for filename in get_all_chat_files():
        is_current = (filename == st.session_state.current_chat_id)
        display_name = filename.replace(".json", "").replace("_", " ").replace("-", ":", 2)
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            if st.button(display_name, key=f"btn_{filename}", use_container_width=True,
                         type="primary" if is_current else "secondary"):
                st.session_state.current_chat_id = filename
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{filename}"):
                delete_chat(filename)
                if st.session_state.current_chat_id == filename:
                    remaining = get_all_chat_files()
                    st.session_state.current_chat_id = remaining[0] if remaining else datetime.datetime.now().strftime(
                        "对话_%Y-%m-%d_%H-%M-%S.json")
                    if not remaining: save_chat(st.session_state.current_chat_id, [])
                st.rerun()

# ================= 7. 主界面 =================
if mode == "玩家模式 (NPC互动)":
    st.title(f"🚂 与 {selected_ai} 的互动空间")
else:
    st.title("🛠️ 星铁 AI 策划研发助手")

current_messages = load_chat(st.session_state.current_chat_id)

# 🚨 按当前角色过滤显示，切换角色后只显示该角色的对话
if mode == "玩家模式 (NPC互动)":
    display_messages = [m for m in current_messages if m.get("character") == selected_ai]
else:
    display_messages = current_messages

for msg in display_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 🚨 升阶段提示（rerun 后仍显示一次）
if st.session_state.get("stage_up_notice"):
    st.toast(st.session_state.pop("stage_up_notice"))

# ================= 8. 流式输出 =================
if prompt := st.chat_input("输入你的问题..."):
    current_messages.append({
        "role": "user", "content": prompt,
        "character": selected_ai if mode == "玩家模式 (NPC互动)" else "策划"
    })
    save_chat(st.session_state.current_chat_id, current_messages)
    with st.chat_message("user"):
        st.markdown(prompt)

    # 🚨 动态好感度计算
    aff_change = 0
    if mode == "玩家模式 (NPC互动)":
        if selected_ai == "三月七":
            if any(word in prompt for word in ["可爱", "拍照", "相机", "喜欢你"]):
                aff_change = 10
            elif any(word in prompt for word in ["笨蛋", "丑", "滚"]):
                aff_change = -15
        elif selected_ai == "流萤":
            if any(word in prompt for word in ["蛋糕", "生命", "意义", "活下去"]):
                aff_change = 10
            elif any(word in prompt for word in ["怪物", "滚"]):
                aff_change = -20
        elif selected_ai == "卡芙卡":
            if any(word in prompt for word in ["美丽", "刺激", "掌控"]):
                aff_change = 10
            elif any(word in prompt for word in ["无聊", "讨厌"]):
                aff_change = -10

        if aff_change != 0:
            old_stage = get_affection_stage(companion_data["affection"])
            companion_data["affection"] = max(0, min(100, companion_data["affection"] + aff_change))
            save_companion_data(selected_ai, companion_data["affection"], companion_data["personality"])
            new_stage = get_affection_stage(companion_data["affection"])
            if new_stage != old_stage:
                st.session_state.stage_up_notice = STAGE_UP_LINES[selected_ai].get(
                    new_stage, f"（{STAGE_NAMES[new_stage]}阶段）")

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        try:
            if mode == "玩家模式 (NPC互动)":
                # 🚨 只取当前角色的历史，避免新角色继承旧角色上下文
                history = [{"role": m["role"], "content": m["content"]}
                           for m in current_messages if m.get("character") == selected_ai][-10:]
            else:
                history = [{"role": m["role"], "content": m["content"]} for m in current_messages][-10:]

            if mode == "玩家模式 (NPC互动)":
                aff = companion_data["affection"]
                stage = get_affection_stage(aff)
                stage_name = STAGE_NAMES[stage]
                s = CHARACTER_STAGES[selected_ai][stage]

                system_prompt = f"""你现在扮演《崩坏：星穹铁道》中的【{selected_ai}】。
                【当前性格设定】：{companion_data['personality']}
                【当前好感度】：{aff}/100，处于【{stage_name}】阶段。
                【本阶段说话风格】：
                    - 称呼：用【{s['称呼']}】称呼用户；
                    - 语气：{s['语气']}；
                    - 口癖：{s['口癖']}。
                【🚨 最重要的规则】你的角色口癖与个性必须【始终保留】，即使好感度为 0，你也仍是【带{selected_ai}性格的攻略助手】，只是亲密度随阶段变化，不能变成没有感情的机器人。
                【绝对规则】
                1. 只要用户问角色数据，你【必须】调用 get_character_basic_stats 等工具。严禁凭记忆瞎编！
                2. 查攻略调用 search_game_guide。
                3. 配队给出高配后，必须追问是否嫌贵。
                4. 你要根据当前阶段，自然流露对应的亲密程度。"""
            else:
                system_prompt = """你是一个高级游戏研发策划助手。
                【规则】
                1. 当用户说"给XX角色设计光锥"时，你【必须】调用 generate_character_signature_light_cone 工具。
                2. 拿到工具返回的数据后，你必须将其转化为"Markdown 格式的排版"展示给用户。
                3. 绝对禁止在回复中出现任何原始代码块、大括号 {} 和 #1[i] 这种占位符！
                4. 必须包含：光锥名称与星级、基础属性（Markdown表格）、被动效果（列表）、设计思路。
                5. 🚨【极其重要】不要向用户展示原始数据！直接以排版好的 Markdown 表格和列表输出！"""

            inputs = {"messages": [SystemMessage(content=system_prompt)] + history, "step_count": 0}

            for msg_chunk, metadata in app.stream(inputs, stream_mode="messages"):
                if msg_chunk.content and msg_chunk.type == "AIMessageChunk":
                    full_response += msg_chunk.content
                    display_text = full_response

                    if mode == "策划模式 (研发提效)":
                        display_text = re.sub(r'\{.*?\}', '', display_text, flags=re.DOTALL)
                        display_text = display_text.replace("```json", "").replace("```", "")
                        if "#" in display_text:
                            display_text = "# " + display_text.split("#", 1)[1]
                        display_text = re.sub(r'#\d+\[i\]', '', display_text)
                        display_text = re.sub(r'\[i\]', '', display_text)
                        display_text = re.sub(r'\n\s*\n', '\n\n', display_text).strip()

                    response_placeholder.markdown(display_text + "▌")

            final_display_text = full_response
            if mode == "策划模式 (研发提效)":
                final_display_text = re.sub(r'\{.*?\}', '', final_display_text, flags=re.DOTALL)
                final_display_text = final_display_text.replace("```json", "").replace("```", "")
                if "#" in final_display_text:
                    final_display_text = "# " + final_display_text.split("#", 1)[1]
                final_display_text = re.sub(r'#\d+\[i\]', '', final_display_text)
                final_display_text = re.sub(r'\[i\]', '', final_display_text)
                final_display_text = re.sub(r'\n\s*\n', '\n\n', final_display_text).strip()

            response_placeholder.markdown(final_display_text)
            current_messages.append({
                "role": "assistant", "content": final_display_text,
                "character": selected_ai if mode == "玩家模式 (NPC互动)" else "策划"
            })
            save_chat(st.session_state.current_chat_id, current_messages)

        except Exception as e:
            st.error(f"发生错误：{e}")

    # 🚨 回复已保存，最后 rerun 刷新侧边栏进度条并让升阶段提示显示
    if aff_change != 0:
        st.rerun()