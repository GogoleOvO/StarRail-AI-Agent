# 🚂 星铁 AI 攻略助手

一个基于 **Streamlit + LangChain Agent + RAG** 的《崩坏：星穹铁道》AI 攻略助手。用自然语言提问，Agent 会自动判断该调用哪个工具，查询角色档案、技能倍率、星魂效果，并通过向量检索返回光锥 / 遗器 / 配队 / 背景攻略。

## ✨ 功能特性

- 🤖 **Agent 自主决策**：基于 LangChain Agent + DeepSeek 大模型，自动选择并调用工具
- 📋 **角色档案查询**：基础信息 + 80 级满级面板（`get_character_basic_stats`）
- ⚔️ **技能倍率查询**：普攻 / 战技 / 终结技 / 天赋（`get_character_skills`）
- 💎 **星魂（命座）查询**：1–6 命效果（`get_character_constellations`）
- 📚 **RAG 攻略检索**：光锥 / 遗器 / 配队 / 角色背景（`search_game_guide`，基于 Chroma 向量库）
- 💬 **聊天记录管理**：新建 / 切换 / 删除对话，本地 JSON 持久化
- ⚡ **流式输出**：边生成边显示

## 🧠 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | Streamlit |
| Agent 框架 | LangChain（`create_agent` + `@tool`） |
| 大模型 | DeepSeek（`deepseek-chat`） |
| Embedding | 阿里云 DashScope（`text-embedding-v3`） |
| 向量库 | Chroma |

## 🏗️ 架构

```
用户提问
   ↓
Streamlit 前端（聊天记录管理）
   ↓
LangChain Agent（DeepSeek deepseek-chat）
   ├─ get_character_basic_stats     → 读 characters_clean_04.json（角色面板）
   ├─ get_character_skills          → 读 characters_clean_04.json（技能倍率）
   ├─ get_character_constellations  → 读 characters_clean_04.json（星魂）
   └─ search_game_guide             → Chroma 向量检索（光锥/遗器/配队/背景）
                                        ↑
                                guides.md ──build_rag.py──> Chroma 向量库
```

## 📁 项目结构

```
攻略助手/
├── mission/
│   ├── Streamlit.py            # 主程序（Agent + 前端）
│   ├── chat_history/           # 聊天记录（本地生成，勿提交）
│   └── chroma_guides_db/       # 向量库（build_rag.py 生成，勿提交）
├── clean_message/
│   ├── clean.py                # 数据清洗脚本（原始数据 → 干净 JSON）
│   ├── config.py               # 字段白名单 + 英文→中文映射
│   ├── build_rag.py            # 构建向量库（guides.md → Chroma）
│   ├── guides.md               # 攻略知识库（Markdown）
│   └── characters_clean_04.json  # 角色数据（工具查询用）
└── character/                  # 原始数据（游戏资源，仅供清洗）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# Windows PowerShell
$env:ALY_API_KEY="你的阿里云 DashScope API Key"
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
```

| 环境变量 | 用途 |
|---|---|
| `ALY_API_KEY` | 阿里云 DashScope，`text-embedding-v3` 向量化 |
| `DEEPSEEK_API_KEY` | DeepSeek，`deepseek-chat` 大模型对话 |

> ⚠️ 请勿将 API Key 写进代码或提交到仓库，统一通过环境变量注入。

### 3. 构建攻略向量库

先确保 `clean_message/guides.md` 里已填写攻略内容（按 `# 角色名` / `## 分类` 组织），然后：

```bash
cd clean_message
python build_rag.py
```

> 重新构建前，请先删除旧的向量库文件夹 `mission/chroma_guides_db`。

### 4. 启动应用

```bash
cd mission
streamlit run Streamlit.py
```

浏览器会自动打开，直接提问即可，例如：

- 「三月七的面板属性是多少？」
- 「流萤的技能倍率」
- 「黄泉推荐什么光锥？」
- 「知更鸟怎么配队？」

## 🔧 数据说明

- **`characters_clean_04.json`**：由 `clean.py` 从 `character/` 原始数据清洗而来，供「角色档案 / 技能 / 星魂」三个工具直接查询。
- **`guides.md`**：攻略知识库，按 `# 角色名` + `## 分类`（角色背景 / 推荐光锥 / 推荐遗器 / 推荐配队）组织，`build_rag.py` 会按标题切成带 metadata 的知识块存入 Chroma。
- 四个工具中，前三个是结构化 JSON 查询，第四个 `search_game_guide` 走 RAG 向量检索。

## 📝 注意事项

- 本项目仅供学习交流使用，游戏数据版权归米哈游所有。
- 请勿将 API Key 提交到仓库（已通过 `.gitignore` 排除 `.env` 等文件）。
