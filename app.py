from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import bcrypt
import os
import psycopg2.extras
from db import get_db, init_db
from game import (
    WEAPONS, ARMORS, calc_level, get_exp_for_level, calc_max_hp,
    battle_vs_monster, battle_vs_player
)

app = Flask(__name__)
app.secret_key = "endless-battle-2026-fixed-key"
app.jinja_env.globals["enumerate"] = enumerate

init_db()

# ─── ヘルパー ───────────────────────────────────────────
def current_player():
    if "player_id" not in session:
        return None
    db = get_db()
    p = db.execute("SELECT * FROM players WHERE id=?", (session["player_id"],)).fetchone()
    db.close()
    return p

def player_info(p):
    """プレイヤー行から表示用dictを作る"""
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
        db = get_db()
        try:
            db.execute("INSERT INTO players (name, password) VALUES (?,?)", (name, hashed))
            db.commit()
            p = db.execute("SELECT * FROM players WHERE name=?", (name,)).fetchone()
            session["player_id"] = p["id"]
            flash(f"ようこそ、{name}！冒険を始めよう！")
            return redirect(url_for("dashboard"))
        except Exception:
            flash("その名前はすでに使われています")
        finally:
            db.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form["name"].strip()
        pw   = request.form["password"]
        db   = get_db()
        p    = db.execute("SELECT * FROM players WHERE name=?", (name,)).fetchone()
        db.close()
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
    db = get_db()
    logs = db.execute(
        "SELECT * FROM battle_log WHERE attacker_id=? ORDER BY id DESC LIMIT 5",
        (p["id"],)
    ).fetchall()
    ranking = db.execute(
        "SELECT name, exp, wins FROM players ORDER BY exp DESC LIMIT 10"
    ).fetchall()
    db.close()
    return render_template("dashboard.html", player=player_info(p), logs=logs, ranking=ranking)

# ─── 戦闘（モンスター）──────────────────────────────────
@app.route("/battle/monster", methods=["POST"])
def battle_monster():
    p = current_player()
    if not p:
        return redirect(url_for("index"))

    result = battle_vs_monster(dict(p))

    db = get_db()
    db.execute(
        "UPDATE players SET exp=exp+?, gold=gold+?, wins=wins+? WHERE id=?",
        (result["exp"], result["gold"], 1 if result["result"]=="win" else 0, p["id"])
    )
    db.execute(
        "INSERT INTO battle_log (attacker_id, defender, result, exp_gain, gold_gain) VALUES (?,?,?,?,?)",
        (p["id"], result["monster"], result["result"], result["exp"], result["gold"])
    )
    db.commit()
    db.close()

    return render_template("battle_result.html", result=result, player=player_info(p))

# ─── 戦闘（プレイヤー）──────────────────────────────────
@app.route("/battle/player", methods=["GET","POST"])
def battle_player():
    p = current_player()
    if not p:
        return redirect(url_for("index"))

    db = get_db()
    if request.method == "POST":
        target_id = int(request.form["target_id"])
        if target_id == p["id"]:
            flash("自分自身とは戦えません")
            return redirect(url_for("battle_player"))
        target = db.execute("SELECT * FROM players WHERE id=?", (target_id,)).fetchone()
        if not target:
            flash("プレイヤーが見つかりません")
            return redirect(url_for("battle_player"))

        result = battle_vs_player(dict(p), dict(target))

        if result["winner"] == "attacker":
            db.execute("UPDATE players SET exp=exp+?, gold=gold+?, wins=wins+1 WHERE id=?",
                       (result["exp"], result["gold"], p["id"]))
            db.execute("UPDATE players SET losses=losses+1 WHERE id=?", (target["id"],))
        elif result["winner"] == "defender":
            db.execute("UPDATE players SET losses=losses+1 WHERE id=?", (p["id"],))
        else:
            db.execute("UPDATE players SET exp=exp+? WHERE id=?", (result["exp"], p["id"]))

        db.execute(
            "INSERT INTO battle_log (attacker_id, defender, result, exp_gain, gold_gain) VALUES (?,?,?,?,?)",
            (p["id"], target["name"], result["winner"], result["exp"], result["gold"])
        )
        db.commit()
        db.close()
        return render_template("battle_result.html", result=result, player=player_info(p), pvp=True)

    players = db.execute(
        "SELECT id, name, exp, wins, losses FROM players WHERE id!=? ORDER BY exp DESC LIMIT 30",
        (p["id"],)
    ).fetchall()
    db.close()
    player_list = [{"id":r["id"],"name":r["name"],"level":calc_level(r["exp"]),"wins":r["wins"],"losses":r["losses"]} for r in players]
    return render_template("battle_player.html", player=player_info(p), players=player_list)

# ─── 武器・防具ショップ ──────────────────────────────────
@app.route("/shop")
def shop():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    lv = calc_level(p["exp"])
    available_w = {k:v for k,v in WEAPONS.items() if v["min_lv"] <= lv}
    available_a = {k:v for k,v in ARMORS.items()  if v["min_lv"] <= lv}
    return render_template("shop.html", player=player_info(p),
                           weapons=available_w, armors=available_a)

@app.route("/shop/buy", methods=["POST"])
def shop_buy():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    item_type = request.form["type"]   # "weapon" or "armor"
    item_id   = int(request.form["item_id"])

    if item_type == "weapon":
        item = WEAPONS.get(item_id)
    else:
        item = ARMORS.get(item_id)

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

    db = get_db()
    if item_type == "weapon":
        db.execute("UPDATE players SET gold=gold-?, weapon_id=? WHERE id=?",
                   (item["price"], item_id, p["id"]))
    else:
        db.execute("UPDATE players SET gold=gold-?, armor_id=? WHERE id=?",
                   (item["price"], item_id, p["id"]))
    db.commit()
    db.close()
    flash(f"「{item['name']}」を購入しました！")
    return redirect(url_for("shop"))

# ─── 国家 ──────────────────────────────────────────────
@app.route("/nations")
def nations():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    db = get_db()
    nations_list = db.execute("""
        SELECT n.*, COUNT(pl.id) as member_count
        FROM nations n
        LEFT JOIN players pl ON pl.nation_id = n.id
        GROUP BY n.id ORDER BY n.gold DESC
    """).fetchall()
    db.close()
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
    db = get_db()
    try:
        db.execute("INSERT INTO nations (name, leader_id, gold) VALUES (?,?,?)",
                   (nation_name, p["id"], 0))
        nation = db.execute("SELECT id FROM nations WHERE name=?", (nation_name,)).fetchone()
        db.execute("UPDATE players SET nation_id=?, gold=gold-? WHERE id=?",
                   (nation["id"], cost, p["id"]))
        db.commit()
        flash(f"「{nation_name}」を建国しました！")
    except Exception:
        flash("その国名はすでに使われています")
    finally:
        db.close()
    return redirect(url_for("nations"))

@app.route("/nations/join/<int:nation_id>", methods=["POST"])
def join_nation(nation_id):
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    if p["nation_id"]:
        flash("すでに国に所属しています")
        return redirect(url_for("nations"))
    db = get_db()
    db.execute("UPDATE players SET nation_id=? WHERE id=?", (nation_id, p["id"]))
    db.commit()
    db.close()
    flash("国に加入しました！")
    return redirect(url_for("nations"))

@app.route("/nations/leave", methods=["POST"])
def leave_nation():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    db = get_db()
    db.execute("UPDATE players SET nation_id=NULL WHERE id=?", (p["id"],))
    db.commit()
    db.close()
    flash("国を離脱しました")
    return redirect(url_for("nations"))

# ─── チャット ───────────────────────────────────────────
@app.route("/chat")
def chat():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    db = get_db()
    messages = db.execute(
        "SELECT * FROM chat ORDER BY id DESC LIMIT 50"
    ).fetchall()
    db.close()
    return render_template("chat.html", player=player_info(p), messages=reversed(list(messages)))

@app.route("/chat/post", methods=["POST"])
def chat_post():
    p = current_player()
    if not p:
        return redirect(url_for("index"))
    msg = request.form["message"].strip()[:200]
    if msg:
        db = get_db()
        db.execute("INSERT INTO chat (player_id, name, message) VALUES (?,?,?)",
                   (p["id"], p["name"], msg))
        # チャットは200件で上限
        db.execute("DELETE FROM chat WHERE id NOT IN (SELECT id FROM chat ORDER BY id DESC LIMIT 200)")
        db.commit()
        db.close()
    return redirect(url_for("chat"))

# ─── 管理者ページ ──────────────────────────────────────
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.args.get("key") != "endless2026admin":
        return "403 Forbidden", 403
    conn = get_db()

    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "POST":
        name   = request.form["name"]
        exp    = request.form.get("exp")
        gold   = request.form.get("gold")
        weapon = request.form.get("weapon_id")
        armor  = request.form.get("armor_id")
        if exp:    cur.execute("UPDATE players SET exp=%s    WHERE name=%s", (exp, name))
        if gold:   cur.execute("UPDATE players SET gold=%s   WHERE name=%s", (gold, name))
        if weapon: cur.execute("UPDATE players SET weapon_id=%s WHERE name=%s", (weapon, name))
        if armor:  cur.execute("UPDATE players SET armor_id=%s  WHERE name=%s", (armor, name))
        conn.commit()
        flash(f"{name}のデータを更新しました")
    players = fetch_all(cur, "SELECT id,name,exp,gold,weapon_id,armor_id FROM players ORDER BY exp DESC")
    cur.close()
    conn.close()
    return render_template("admin.html", players=players, weapons=WEAPONS, armors=ARMORS)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
