import random
import math

# 武器マスターデータ
WEAPONS = {
    1:  {"name": "木の剣",     "atk": 2,  "price": 50,   "min_lv": 1},
    2:  {"name": "銅の剣",     "atk": 5,  "price": 150,  "min_lv": 3},
    3:  {"name": "鉄の剣",     "atk": 10, "price": 400,  "min_lv": 5},
    4:  {"name": "鋼の剣",     "atk": 18, "price": 900,  "min_lv": 8},
    5:  {"name": "銀の剣",     "atk": 28, "price": 2000, "min_lv": 12},
    6:  {"name": "魔法の剣",   "atk": 42, "price": 5000, "min_lv": 18},
    7:  {"name": "ドラゴン刃", "atk": 60, "price": 12000,"min_lv": 25},
    8:  {"name": "神剣",       "atk": 85, "price": 30000,"min_lv": 35},
}

# 防具マスターデータ
ARMORS = {
    1:  {"name": "布の鎧",     "def": 2,  "price": 50,   "min_lv": 1},
    2:  {"name": "革の鎧",     "def": 5,  "price": 150,  "min_lv": 3},
    3:  {"name": "鉄の鎧",     "def": 10, "price": 400,  "min_lv": 5},
    4:  {"name": "鋼の鎧",     "def": 18, "price": 900,  "min_lv": 8},
    5:  {"name": "銀の鎧",     "def": 28, "price": 2000, "min_lv": 12},
    6:  {"name": "魔法の鎧",   "def": 42, "price": 5000, "min_lv": 18},
    7:  {"name": "龍鱗の鎧",   "def": 60, "price": 12000,"min_lv": 25},
    8:  {"name": "神の鎧",     "def": 85, "price": 30000,"min_lv": 35},
}

# モンスターマスターデータ
MONSTERS = [
    {"name": "スライム",   "hp": 20,  "atk": 3,  "def": 1,  "exp": 10,  "gold": 15,  "min_lv": 1},
    {"name": "ゴブリン",   "hp": 40,  "atk": 7,  "def": 3,  "exp": 25,  "gold": 30,  "min_lv": 2},
    {"name": "オーク",     "hp": 80,  "atk": 12, "def": 6,  "exp": 55,  "gold": 60,  "min_lv": 4},
    {"name": "トロール",   "hp": 150, "atk": 20, "def": 10, "exp": 110, "gold": 110, "min_lv": 7},
    {"name": "ワイバーン", "hp": 280, "atk": 32, "def": 16, "exp": 200, "gold": 200, "min_lv": 11},
    {"name": "ドラゴン",   "hp": 500, "atk": 50, "def": 25, "exp": 400, "gold": 380, "min_lv": 17},
    {"name": "魔王の使い", "hp": 900, "atk": 75, "def": 38, "exp": 750, "gold": 700, "min_lv": 24},
    {"name": "魔王",       "hp": 1500,"atk":110, "def": 55, "exp":1500, "gold":1500, "min_lv": 33},
]

def get_exp_for_level(level):
    """レベルアップに必要な累計経験値"""
    return int(100 * (level ** 1.8))

def calc_level(exp):
    """経験値からレベルを計算"""
    lv = 1
    while get_exp_for_level(lv + 1) <= exp:
        lv += 1
        if lv >= 99:
            break
    return lv

def calc_max_hp(level, base_hp=50):
    return base_hp + (level - 1) * 15

def get_available_monsters(player_level):
    """プレイヤーレベルに応じたモンスターリスト"""
    available = [m for m in MONSTERS if m["min_lv"] <= player_level]
    # 上位3体まで
    return available[-3:] if len(available) > 3 else available

def battle_vs_monster(player, monster_id_or_name=None):
    """
    プレイヤー vs モンスター 戦闘処理
    Returns: dict with result, log, rewards
    """
    level = calc_level(player["exp"])
    available = get_available_monsters(level)
    if not available:
        available = [MONSTERS[0]]

    monster = random.choice(available).copy()

    # プレイヤーのステータス計算
    weapon = WEAPONS.get(player["weapon_id"], WEAPONS[1])
    armor  = ARMORS.get(player["armor_id"],  ARMORS[1])
    p_atk = level * 3 + weapon["atk"]
    p_def = level * 2 + armor["def"]
    p_hp  = calc_max_hp(level)
    p_cur_hp = p_hp

    m_hp = monster["hp"]
    m_atk = monster["atk"]
    m_def = monster["def"]

    log = []
    log.append(f"⚔️ {monster['name']}が現れた！")

    turn = 0
    while p_cur_hp > 0 and m_hp > 0 and turn < 30:
        turn += 1
        # プレイヤーの攻撃
        p_dmg = max(1, p_atk - m_def + random.randint(-3, 5))
        m_hp -= p_dmg
        log.append(f"あなたの攻撃！ {monster['name']}に {p_dmg} ダメージ（残HP: {max(0,m_hp)}）")

        if m_hp <= 0:
            break

        # モンスターの攻撃
        m_dmg = max(1, m_atk - p_def + random.randint(-3, 5))
        p_cur_hp -= m_dmg
        log.append(f"{monster['name']}の攻撃！ あなたに {m_dmg} ダメージ（残HP: {max(0,p_cur_hp)}）")

    if m_hp <= 0:
        exp_gain  = monster["exp"] + random.randint(0, monster["exp"] // 4)
        gold_gain = monster["gold"] + random.randint(0, monster["gold"] // 4)
        log.append(f"🎉 {monster['name']}を倒した！ EXP+{exp_gain} GOLD+{gold_gain}")
        return {
            "result": "win",
            "log": log,
            "exp": exp_gain,
            "gold": gold_gain,
            "monster": monster["name"],
            "survived_hp": max(0, p_cur_hp),
            "max_hp": p_hp,
        }
    else:
        log.append(f"💀 {monster['name']}に倒された… 経験値は得られなかった。")
        return {
            "result": "lose",
            "log": log,
            "exp": 0,
            "gold": 0,
            "monster": monster["name"],
            "survived_hp": 0,
            "max_hp": p_hp,
        }

def battle_vs_player(attacker, defender):
    """
    プレイヤー vs プレイヤー 戦闘処理
    """
    def stats(p):
        lv = calc_level(p["exp"])
        w  = WEAPONS.get(p["weapon_id"], WEAPONS[1])
        a  = ARMORS.get(p["armor_id"],  ARMORS[1])
        return {
            "lv":  lv,
            "atk": lv * 3 + w["atk"],
            "def": lv * 2 + a["def"],
            "hp":  calc_max_hp(lv),
        }

    a_st = stats(attacker)
    d_st = stats(defender)
    a_hp = a_st["hp"]
    d_hp = d_st["hp"]

    log = []
    log.append(f"⚔️ {attacker['name']} (Lv{a_st['lv']}) vs {defender['name']} (Lv{d_st['lv']})")

    turn = 0
    while a_hp > 0 and d_hp > 0 and turn < 30:
        turn += 1
        # 攻撃側
        dmg = max(1, a_st["atk"] - d_st["def"] + random.randint(-5, 8))
        d_hp -= dmg
        log.append(f"{attacker['name']}の攻撃！ {defender['name']}に {dmg} ダメージ（残HP: {max(0,d_hp)}）")
        if d_hp <= 0:
            break
        # 防御側の反撃
        dmg2 = max(1, d_st["atk"] - a_st["def"] + random.randint(-5, 8))
        a_hp -= dmg2
        log.append(f"{defender['name']}の反撃！ {attacker['name']}に {dmg2} ダメージ（残HP: {max(0,a_hp)}）")

    if d_hp <= 0:
        exp_gain  = max(10, d_st["lv"] * 15)
        gold_gain = max(5,  d_st["lv"] * 8)
        log.append(f"🎉 {attacker['name']}の勝利！ EXP+{exp_gain} GOLD+{gold_gain}")
        return {"winner": "attacker", "log": log, "exp": exp_gain, "gold": gold_gain}
    elif a_hp <= 0:
        log.append(f"💀 {defender['name']}の勝利！")
        return {"winner": "defender", "log": log, "exp": 0, "gold": 0}
    else:
        log.append("引き分け！")
        return {"winner": "draw", "log": log, "exp": 5, "gold": 0}
