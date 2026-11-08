import json
import re
import os

# ================= 1. 路径配置 =================
# 请根据你实际的文件位置修改这里的路径
RAW_DIR = "../character"  # 原始文件所在的文件夹
CLEAN_DIR = "./data_clean"  # 输出文件保存的文件夹
os.makedirs(CLEAN_DIR, exist_ok=True)


# ================= 2. 核心规则判断函数（星魂限制） =================
def get_star_lock_warning(skill_type, char_path, level_num):
    """
    根据技能类型、角色命途和当前等级，判断是否被星魂锁住。
    """
    # 欢愉命途 (Elation) 专属逻辑
    if char_path == "Elation" and "欢愉" in skill_type:
        if 10 < level_num <= 12:
            return "（需3星魂解锁）"
        elif level_num > 12:
            return "（需5星魂解锁）"

    # 记忆命途 (Memory / Remembrance) 专属逻辑
    elif char_path in ["Memory", "Remembrance"] and "忆灵" in skill_type:
        if "忆灵天赋" in skill_type and level_num > 6:
            return "（需3星魂解锁）"
        elif "忆灵技能" in skill_type and level_num > 6:
            return "（需5星魂解锁）"

    # 通用逻辑
    if "普攻" in skill_type:
        if level_num > 6: return "（需3星魂解锁）"
    elif "终结技" in skill_type:
        if level_num > 10: return "（需3星魂解锁）"
    elif "战技" in skill_type or "天赋" in skill_type:
        if level_num > 10: return "（需5星魂解锁）"
    return ""


# ================= 3. 读取原始数据 =================
print("正在读取原始数据文件...")
with open(f"{RAW_DIR}/characters.json", "r", encoding="utf-8-sig") as f:
    chars_raw = json.load(f)

with open(f"{RAW_DIR}/character_skills.json", "r", encoding="utf-8-sig") as f:
    skills_raw = json.load(f)

with open(f"{RAW_DIR}/character_ranks.json", "r", encoding="utf-8-sig") as f:
    ranks_raw = json.load(f)

with open(f"{RAW_DIR}/character_promotions.json", "r", encoding="utf-8-sig") as f:
    promotions_raw = json.load(f)

# ================= 4. 开始大清洗 =================
cleaned_characters = []

print("开始进行数据清洗与缝合...")
for char_id, char_info in chars_raw.items():
    # 跳过非角色配置项
    if not isinstance(char_info, dict) or "name" not in char_info:
        continue

    # --- 4.1 基础信息提取与翻译 ---
    char_name = char_info.get("name")
    if char_name == "{NICKNAME}":
        char_name = "男开拓者" if "playerboy" in char_info.get("tag", "") else "女开拓者"

    # 简单的英文转中文（如果你有config，直接换成 config.PATH_MAP）
    path_en = char_info.get("path", "")
    element_en = char_info.get("element", "")

    path_cn = {"Warrior": "毁灭", "Rogue": "巡猎", "Mage": "智识", "Shaman": "同谐", "Warlock": "虚无",
               "Knight": "存护", "Priest": "丰饶", "Memory": "记忆", "Remembrance": "记忆", "Elation": "欢愉"}.get(
        path_en, path_en)
    element_cn = {"Physical": "物理", "Fire": "火", "Ice": "冰", "Lightning": "雷", "Wind": "风", "Quantum": "量子",
                  "Imaginary": "虚数"}.get(element_en, element_en)

    # --- 4.2 提取 80 级满级面板 ---
    promo_values = promotions_raw.get(char_id, {}).get("values", [])
    if promo_values:
        max_stats = promo_values[-1]
        level_80_stats = (
            f"80级面板：生命值{max_stats.get('hp', {}).get('base', 0)}, "
            f"攻击力{max_stats.get('atk', {}).get('base', 0)}, "
            f"防御力{max_stats.get('def', {}).get('base', 0)}, "
            f"基础速度{max_stats.get('spd', {}).get('base', 0)}"
        )
    else:
        level_80_stats = "暂无满级面板数据"

    # --- 4.3 提取 技能倍率 + 星魂限制 ---
    skill_ids = char_info.get("skills", [])
    all_skills_text = []
    for s_id in skill_ids:
        target_skill = skills_raw.get(s_id) if isinstance(skills_raw, dict) else None
        if not target_skill: continue

        s_name = target_skill.get("name", "未知技能")
        s_type = target_skill.get("type_text", "技能")
        s_desc = target_skill.get("desc", "")
        params = target_skill.get("params", [])

        level_texts = []
        for idx, p_list in enumerate(params):
            level_num = idx + 1
            temp_desc = s_desc

            # 替换占位符（带百分号）
            for p_idx, val in enumerate(p_list):
                percent_val = f"{val * 100:.1f}%"
                temp_desc = temp_desc.replace(f"#{p_idx + 1}[i]", percent_val)

            # 洗掉富文本标签
            temp_desc = re.sub(r'<[^>]+>', '', temp_desc)

            # 获取星魂限制警告
            lock_warning = get_star_lock_warning(s_type, path_en, level_num)
            level_texts.append(f"    {level_num}级{lock_warning}：{temp_desc}")

        if level_texts:
            all_skills_text.append(f"【{s_type} - {s_name}】\n" + "\n".join(level_texts))

    # --- 4.4 提取 星魂效果（带序号） ---
    rank_ids = char_info.get("ranks", [])
    all_ranks_text = []
    for idx, r_id in enumerate(rank_ids):
        rank_num = idx + 1
        target_rank = ranks_raw.get(r_id) if isinstance(ranks_raw, dict) else None

        if target_rank:
            r_name = target_rank.get("name", "未知星魂")
            r_desc = re.sub(r'<[^>]+>', '', target_rank.get("desc", ""))
            # ✨ 加入 1命、2命 的序号
            all_ranks_text.append(f"{rank_num}命【{r_name}】：\n{r_desc}")

    # --- 4.5 组装最终数据 ---
    clean_obj = {
        "id": char_id,
        "name": char_name,
        "rarity": char_info.get("rarity", 0),
        "path": path_cn,
        "element": element_cn,
        "level_80_stats": level_80_stats,
        "skills": "\n\n".join(all_skills_text),
        "ranks": "\n\n".join(all_ranks_text)
    }
    cleaned_characters.append(clean_obj)

# ================= 5. 保存最终文件 =================
with open(f"{CLEAN_DIR}/characters_final.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_characters, f, ensure_ascii=False, indent=4)

print(f"✅ 大功告成！共清洗了 {len(cleaned_characters)} 个角色。最终文件已保存至 {CLEAN_DIR}/characters_final.json")