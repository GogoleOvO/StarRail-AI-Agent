from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from pathlib import Path
import os

# 1. 初始化 Embedding 模型
embed = OpenAIEmbeddings(
    model="text-embedding-v3",
    api_key=os.environ.get("ALY_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    check_embedding_ctx_length=False,
    chunk_size=10 # 阿里云限制
)

# 2. 读取 Markdown
md_text = Path("./guides.md").read_text(encoding="utf-8")

# 3. 第一层切分：按标题提取 Metadata（分类）
headers_to_split_on = [
    ("#", "character"),  # 一级标题作为角色名
    ("##", "category")   # 二级标题作为分类（如：推荐光锥）
]
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
header_splits = md_splitter.split_text(md_text)

# 4. 第二层切分：按字数兜底，保护段落完整
char_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,      # 👈 【关键】放大到800，你的光锥400字完全装得下
    chunk_overlap=50,    # 重叠50字，防止上下文断层
    # 👇 【关键】指定切分的符号优先级：
    separators=["\n\n", "\n", "。", "！", "？", " ", ""]
)
final_docs = char_splitter.split_documents(header_splits)

# 5. 存入 Chroma（记得先把你电脑里的旧数据库文件夹删掉！）
vector_store = Chroma(
    collection_name="game_guides",
    embedding_function=embed,
    persist_directory="../mission/chroma_guides_db"
)

vector_store.add_documents(final_docs)
for doc in final_docs:
    if doc.metadata.get("character") == "三月七":
        print(f"【三月七的数据被切分了！】分类：{doc.metadata.get('category')}")
print(f"✅ 攻略知识库构建完毕！共存入 {len(final_docs)} 个知识块。")