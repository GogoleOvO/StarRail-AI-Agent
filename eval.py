import requests
import json
import time

# ================= 1. 定义测试用例集 =================
# 这里设置了不同的测试场景，以及期望 AI 回答里必须包含的关键词
TEST_CASES = [
    {
        "type": "数据查询",
        "question": "三月七的80级基础速度是多少？",
        "expected_keywords": ["101"]  # AI 必须说出 101
    },
    {
        "type": "防幻觉（原神角色）",
        "question": "原神里的胡桃面板属性是多少？",
        "expected_keywords": ["无法", "星铁", "不知道", "抱歉", "未找到"]  # 必须拒绝或指正
    },
    {
        "type": "边界闲聊",
        "question": "今天天气怎么样？",
        "expected_keywords": ["无法", "不知道", "抱歉"]  # 必须拒绝
    },
    {
        "type": "策划配表",
        "question": "给流萤设计一个5星专属光锥。",
        "expected_keywords": ["光锥", "流萤", "生命", "攻击"]  # 必须生成配置
    }
]

# 你的 FastAPI 地址
API_URL = "http://127.0.0.1:8000/chat"


def run_evaluation():
    print("🚀 开始执行 Agent 自动化评测...")
    print("-" * 50)

    passed_count = 0
    total_count = len(TEST_CASES)

    report_lines = ["# 🤖 Agent 自动化评测报告", ""]
    report_lines.append("| 测试类型 | 问题 | 是否通过 | 耗时 |")
    report_lines.append("| --- | --- | --- | --- |")

    for i, case in enumerate(TEST_CASES):
        question = case["question"]
        case_type = case["type"]
        keywords = case["expected_keywords"]

        print(f"\n[{i + 1}/{total_count}] 正在测试: {question}")

        start_time = time.time()
        try:
            # 发送请求给 FastAPI
            response = requests.post(API_URL, json={"message": question}, timeout=60)
            cost_time = round(time.time() - start_time, 2)

            if response.status_code == 200:
                # 🚨 核心修复：这里提取的键名必须是 ai_reply，和你后端对应！
                res_json = response.json()
                ai_reply = res_json.get("ai_reply", "")

                print(f"  📥 后端实际返回: {ai_reply[:80]}...")  # 截取前80个字看看

                # 核心判定逻辑：看看回答里有没有预期的关键词
                is_passed = any(kw in ai_reply for kw in keywords)

                if is_passed:
                    print(f"  ✅ 通过 (耗时: {cost_time}s)")
                    passed_count += 1
                    report_lines.append(f"| {case_type} | {question} | ✅ 通过 | {cost_time}s |")
                else:
                    print(f"  ❌ 失败 (未包含预期关键词: {keywords})")
                    report_lines.append(f"| {case_type} | {question} | ❌ 失败 | {cost_time}s |")
            else:
                print(f"  ❌ 接口报错: 状态码 {response.status_code}")
                report_lines.append(f"| {case_type} | {question} | ❌ 接口报错 | - |")

        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
            report_lines.append(f"| {case_type} | {question} | ❌ 异常 | - |")

        time.sleep(1)  # 稍微停顿，防止请求过快

    # ================= 3. 生成最终报告 =================
    accuracy = round((passed_count / total_count) * 100, 1)

    print("\n" + "=" * 50)
    print(f"📊 评测结束！通过率: {passed_count}/{total_count} ({accuracy}%)")

    report_lines.append("")
    report_lines.append(f"**总体通过率：{passed_count}/{total_count} ({accuracy}%)**")

    # 把报告写入 Markdown 文件，方便放进 GitHub
    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("✅ 详细报告已生成并保存为 eval_report.md")


if __name__ == "__main__":
    run_evaluation()