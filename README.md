# 🚂 星铁攻略助手

基于 **Streamlit + LangGraph + FastAPI** 的《崩坏：星穹铁道》AI 助手，支持**玩家模式（角色扮演 + 好感度系统）**和**策划模式（光锥配表生成）**，并内置**自动化评测脚本**。

## ✨ 功能特性

### 🎮 玩家模式（NPC 互动）
- 可切换 3 位可攻略角色：**三月七、流萤、卡芙卡**，各有独立人设、口癖与说话风格。
- **5 阶段好感度系统**：助手 → 熟悉 → 朋友 → 亲近 → 知己，随好感度变化称呼、语气、亲密度逐步升级。
- 好感度根据聊天关键词动态增减，跨阶段时触发角色专属"升级台词"。
- 每个角色的对话与好感度**独立存档**，切换角色互不串味。
- 支持自定义角色性格、多会话历史记录管理。

### 🛠️ 策划模式（研发提效）
- 输入角色名 + 星级，自动查库分析角色机制，生成**专属光锥配表**（基础属性 + 被动效果 + 数值）。
- 输出规范化的 Markdown 排版（表格 + 列表），可直接用于研发文档。

### 🧪 自动化评测（eval.py）
- 内置 4 类测试用例：数据查询、防幻觉、边界闲聊、策划配表。
- 自动请求 FastAPI 后端，校验关键词，生成 `eval_report.md` 评测报告。

## 🏗️ 技术架构

- **前端**：Streamlit（页面交互、流式输出、进度条）
- **Agent 编排**：LangGraph（StateGraph + ToolNode，工具调用路由）
- **大模型**：DeepSeek（`deepseek-chat`，经 LangChain `ChatOpenAI` 接入）
- **向量检索**：Chroma + 阿里云 DashScope `text-embedding-v3`（攻略检索）
- **后端接口**：FastAPI（`/chat` 端点，供评测脚本调用）

## 📁 目录结构

```
攻略助手/
├── clean_message/
│   └── characters_clean_04.json      # 角色基础数据（属性/技能/星魂）
└── mission/
    ├── Streamlit.py                  # 主应用（玩家模式 + 策划模式）
    ├── api_server.py                 # FastAPI 后端接口
    ├── eval.py                       # 自动化评测脚本
    ├── chroma_guides_db/             # 攻略向量库（Chroma，需自行构建）
    ├── chat_history/                 # 聊天记录（运行时自动生成）
    └── companion_data/               # 角色好感度存档（运行时自动生成）
```

## 🔧 环境要求

- Python 3.9+
- DeepSeek API Key（大模型调用）
- 阿里云 DashScope API Key（文本向量化，用于攻略检索）

## 📦 安装

```bash
# 1. 克隆仓库
git clone <你的仓库地址>
cd 攻略助手

# 2. 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

## 🔑 环境变量

在项目根目录创建 `.env` 文件（或在系统环境变量中配置）：

```bash
# DeepSeek 大模型
DEEPSEEK_API_KEY=sk-xxxxxxxx

# 阿里云 DashScope（text-embedding-v3，用于攻略向量检索）
ALY_API_KEY=sk-xxxxxxxx
```

## 🚀 运行方式

### 1. 启动主应用（Streamlit）

```bash
cd mission
streamlit run Streamlit.py
```

浏览器打开 `http://localhost:8501`。

### 2. 启动后端接口（FastAPI，供评测使用）

```bash
cd mission
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

### 3. 运行自动化评测

先启动 FastAPI 后端，再执行：

```bash
cd mission
python eval.py
```

评测完成后会在当前目录生成 `eval_report.md`。

## 📚 数据准备

1. **角色数据**：需在 `clean_message/` 下放置 `characters_clean_04.json`（字段：name / rarity / path_cn / element_cn / level_80_stats / skills / ranks）。
2. **攻略向量库**：需预先将攻略数据写入 `mission/chroma_guides_db/`（Chroma 集合名 `game_guides`，含 `character` 和 `category` 元数据，category 取值：推荐光锥 / 推荐遗器 / 推荐配队 / 角色背景）。

> ⚠️ 角色数据与向量库体积较大，默认不提交到仓库，请按需自行准备。

## ⚠️ 注意事项

- 所有大模型调用依赖有效的 API Key，未配置时应用会报错。
- `chat_history/`、`companion_data/` 为运行时生成目录，已被 `.gitignore` 忽略。
- 本项目的角色扮演仅用于学习交流，角色版权归《崩坏：星穹铁道》官方所有。

## 📄 License

MIT License
