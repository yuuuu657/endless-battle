from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt
import os
import psycopg2
import psycopg2.extras
from db import get_db, init_db
from game import (
    WEAPONS, ARMORS, calc_level, get_exp_for_level, calc_max_hp,
    battle_vs_monster, battle_vs_player
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "endless-battle-2026-fixed-key")
app.jinja_env.globals["enumerate"] = enumerate

init_db()

# ─── ヘルパー ───────────────────────────────────────────
def fetch_one(cur, query, params=()):
    cur.execute(query, params)
    row = cur.fetchone()
    return row

def fetch_all(cur, query, params=()):
    cur.execute(query, params)
    return cur.fetchall()

def current_player():
    if "player_id" not in session:
        return None
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    p = fetch_one(cur, "SELECT * FROM players WHERE id=%s", (session["player_id"],))
    cur.close()
    conn.close()
    return p

def player_info(p):
    lv = calc_level(p["exp"])
    return {
        **dict(p),
        "level": lv,
        "max_hp": calc_max_hp(lv),
        "exp_next": get_exp_for_level(lv + 1),
        "weapon_name": WEAPONS.get(p["weapon_id"], WEAPONS[1])["name"],
        "armor_name":  ARMORS.get(p["armor_id"],  ARMORS[1])["name"],
    }

# ─── トップ・認証 ──────────────────────────────────────
@app.route("/")
def index():
    if "player_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        pw   = request.form["password"]
        if not name or len(name) < 2:
            flash("名前は2文字以上で入力してください")
            return render_template("register.html")
        if len(name) > 16:
            flash("名前は16文字以内にしてください")
            return render_template("register.html")
        hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("INSERT INTO players (name, password) VALUES (%s,%s)", (name, hashed))
            conn.commit()
            p = fetch_one(cur, "SELECT * FROM players WHERE name=%s", (name,))
            session["player_id"] = p["id"]
            flash(f"ようこそ、{name}！冒険を始めよう！")
            return redirect(url_for("dashboard"))
        except Exception:
            conn.rollback()
            flash("その名前はすでに使われています")
        finally:
            cur.close()
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form["name"].strip()
        pw   = request.form["password"]
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        p    = fetch_one(cur, "SELECT * FROM players WHERE name=%s", (name,))
        cur.close()
        conn.close()
        if p and bcrypt.checkpw(pw.encode(), p["password"].encode()):
            session["player_id"] = p["id"]
            return redirect(url_for("dashboard"))
        flash("名前またはパスワードが違います")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ─── ダッシュボード ────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    logs    = fetch_all(cur, "SELECT * FROM battle_log WHERE attacker_id=%s ORDER BY id DESC LIMIT 5", (p["id"],))
    ranking = fetch_all(cur, "SELECT name, exp, wins FROM players ORDER BY exp DESC LIMIT 10")
    cur.close()
    conn.close()
    return render_template("dashboard.html", player=player_info(p), logs=logs, ranking=ranking)

# ─── 戦闘（モンスター）──────────────────────────────────
@app.route("/battle/monster", methods=["POST"])
def battle_monster():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    result = battle_vs_monster(dict(p))
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE players SET exp=exp+%s, gold=gold+%s, wins=wins+%s WHERE id=%s",
                (result["exp"], result["gold"], 1 if result["result"]=="win" else 0, p["id"]))
    cur.execute("INSERT INTO battle_log (attacker_id, defender, result, exp_gain, gold_gain) VALUES (%s,%s,%s,%s,%s)",
                (p["id"], result["monster"], result["result"], result["exp"], result["gold"]))
    conn.commit()
    cur.close()
    conn.close()
    return render_template("battle_result.html", result=result, player=player_info(p))

# ─── 戦闘（プレイヤー）──────────────────────────────────
@app.route("/battle/player", methods=["GET","POST"])
def battle_player():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        target_id = int(request.form["target_id"])
        if target_id == p["id"]:
            flash("自分自身とは戦えません")
            return redirect(url_for("battle_player"))
        target = fetch_one(cur, "SELECT * FROM players WHERE id=%s", (target_id,))
        if not target:
            flash("プレイヤーが見つかりません")
            return redirect(url_for("battle_player"))
        result = battle_vs_player(dict(p), dict(target))
        if result["winner"] == "attacker":
            cur.execute("UPDATE players SET exp=exp+%s, gold=gold+%s, wins=wins+1 WHERE id=%s",
                        (result["exp"], result["gold"], p["id"]))
            cur.execute("UPDATE players SET losses=losses+1 WHERE id=%s", (target["id"],))
        elif result["winner"] == "defender":
            cur.execute("UPDATE players SET losses=losses+1 WHERE id=%s", (p["id"],))
        else:
            cur.execute("UPDATE players SET exp=exp+%s WHERE id=%s", (result["exp"], p["id"]))
        cur.execute("INSERT INTO battle_log (attacker_id, defender, result, exp_gain, gold_gain) VALUES (%s,%s,%s,%s,%s)",
                    (p["id"], target["name"], result["winner"], result["exp"], result["gold"]))
        conn.commit()
        cur.close()
        conn.close()
        return render_template("battle_result.html", result=result, player=player_info(p), pvp=True)
    players = fetch_all(cur, "SELECT id, name, exp, wins, losses FROM players WHERE id!=%s ORDER BY exp DESC LIMIT 30", (p["id"],))
    cur.close()
    conn.close()
    player_list = [{"id":r["id"],"name":r["name"],"level":calc_level(r["exp"]),"wins":r["wins"],"losses":r["losses"]} for r in players]
    return render_template("battle_player.html", player=player_info(p), players=player_list)

# ─── ショップ ──────────────────────────────────────────
@app.route("/shop")
def shop():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    lv = calc_level(p["exp"])
    available_w = {k:v for k,v in WEAPONS.items() if v["min_lv"] <= lv}
    available_a = {k:v for k,v in ARMORS.items()  if v["min_lv"] <= lv}
    return render_template("shop.html", player=player_info(p), weapons=available_w, armors=available_a)

@app.route("/shop/buy", methods=["POST"])
def shop_buy():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    item_type = request.form["type"]
    item_id   = int(request.form["item_id"])
    item = WEAPONS.get(item_id) if item_type == "weapon" else ARMORS.get(item_id)
    if not item:
        flash("アイテムが見つかりません")
        return redirect(url_for("shop"))
    lv = calc_level(p["exp"])
    if item["min_lv"] > lv:
        flash("レベルが足りません")
        return redirect(url_for("shop"))
    if p["gold"] < item["price"]:
        flash("GOLDが足りません")
        return redirect(url_for("shop"))
    conn = get_db()
    cur  = conn.cursor()
    if item_type == "weapon":
        cur.execute("UPDATE players SET gold=gold-%s, weapon_id=%s WHERE id=%s", (item["price"], item_id, p["id"]))
    else:
        cur.execute("UPDATE players SET gold=gold-%s, armor_id=%s WHERE id=%s", (item["price"], item_id, p["id"]))
    conn.commit()
    cur.close()
    conn.close()
    flash(f"「{item['name']}」を購入しました！")
    return redirect(url_for("shop"))

# ─── 国家 ──────────────────────────────────────────────
@app.route("/nations")
def nations():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    nations_list = fetch_all(cur, """
        SELECT n.*, COUNT(pl.id) as member_count
        FROM nations n
        LEFT JOIN players pl ON pl.nation_id = n.id
        GROUP BY n.id ORDER BY n.gold DESC
    """)
    cur.close()
    conn.close()
    return render_template("nations.html", player=player_info(p), nations=nations_list)

@app.route("/nations/create", methods=["POST"])
def create_nation():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    if p["nation_id"]:
        flash("すでに国に所属しています")
        return redirect(url_for("nations"))
    nation_name = request.form["name"].strip()
    if not nation_name or len(nation_name) < 2:
        flash("国名は2文字以上で入力してください")
        return redirect(url_for("nations"))
    cost = 500
    if p["gold"] < cost:
        flash(f"建国には{cost}G必要です")
        return redirect(url_for("nations"))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("INSERT INTO nations (name, leader_id, gold) VALUES (%s,%s,%s)", (nation_name, p["id"], 0))
        nation = fetch_one(cur, "SELECT id FROM nations WHERE name=%s", (nation_name,))
        cur.execute("UPDATE players SET nation_id=%s, gold=gold-%s WHERE id=%s", (nation["id"], cost, p["id"]))
        conn.commit()
        flash(f"「{nation_name}」を建国しました！")
    except Exception:
        conn.rollback()
        flash("その国名はすでに使われています")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("nations"))

@app.route("/nations/join/<int:nation_id>", methods=["POST"])
def join_nation(nation_id):
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    if p["nation_id"]:
        flash("すでに国に所属しています")
        return redirect(url_for("nations"))
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE players SET nation_id=%s WHERE id=%s", (nation_id, p["id"]))
    conn.commit()
    cur.close()
    conn.close()
    flash("国に加入しました！")
    return redirect(url_for("nations"))

@app.route("/nations/leave", methods=["POST"])
def leave_nation():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("UPDATE players SET nation_id=NULL WHERE id=%s", (p["id"],))
    conn.commit()
    cur.close()
    conn.close()
    flash("国を離脱しました")
    return redirect(url_for("nations"))

# ─── チャット ───────────────────────────────────────────
@app.route("/chat")
def chat():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    messages = fetch_all(cur, "SELECT * FROM chat ORDER BY id DESC LIMIT 50")
    cur.close()
    conn.close()
    return render_template("chat.html", player=player_info(p), messages=reversed(list(messages)))

@app.route("/chat/post", methods=["POST"])
def chat_post():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    msg = request.form["message"].strip()[:200]
    if msg:
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("INSERT INTO chat (player_id, name, message) VALUES (%s,%s,%s)", (p["id"], p["name"], msg))
        cur.execute("DELETE FROM chat WHERE id NOT IN (SELECT id FROM chat ORDER BY id DESC LIMIT 200)")
        conn.commit()
        cur.close()
        conn.close()
    return redirect(url_for("chat"))

# ─── 管理者ページ ──────────────────────────────────────
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.args.get("key") != "endless2026admin":
        return "403 Forbidden", 403
    conn = get_db()
    cur = conn.cursor()
    if request.method == "POST":
        name   = request.form["name"]
        exp    = request.form.get("exp")
        gold   = request.form.get("gold")
        weapon = request.form.get("weapon_id")
        armor  = request.form.get("armor_id")
        if exp:    cur.execute("UPDATE players SET exp=%s WHERE name=%s", (exp, name))
        if gold:   cur.execute("UPDATE players SET gold=%s WHERE name=%s", (gold, name))
        if weapon: cur.execute("UPDATE players SET weapon_id=%s WHERE name=%s", (weapon, name))
        if armor:  cur.execute("UPDATE players SET armor_id=%s WHERE name=%s", (armor, name))
        conn.commit()
        flash(f"{name}のデータを更新しました")
    cur.execute("SELECT id,name,exp,gold,weapon_id,armor_id FROM players ORDER BY exp DESC")
    players = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return render_template("admin.html", players=players, weapons=WEAPONS, armors=ARMORS)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
