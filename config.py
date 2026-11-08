# config.py
# 1. 白名单配置：控制哪些字段能进入大模型
KEEP_FIELDS = ["id", "name", "rarity", "path", "element", "max_sp", "skills", "ranks"]

# 2. 翻译映射配置：控制英文代号转中文
PATH_MAP = {"Warrior": "毁灭", "Rogue": "巡猎", "Shaman": "同谐", "Memory": "记忆", "Knight": "存护","Elation": "欢愉", "Mage": "智识", "Warlock": "虚无","Priest": "丰饶"}
ELEMENT_MAP = {"Imaginary": "虚数", "Quantum": "量子", "Fire": "火","Physical":"物理","Thunder":"雷","Wind":"风",}