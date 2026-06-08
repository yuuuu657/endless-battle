# ⚔️ エンドレスバトル

2000年代に日本で流行したCGIブラウザゲーム「エンドレスバトル」のリバイバル版です。  
Python (Flask) + SQLite3 で動作し、サーバーさえあれば複数人でプレイできます。

## 機能

- 👤 プレイヤー登録・ログイン（bcryptでパスワードをハッシュ化）
- ⚔️ モンスター討伐（経験値・GOLDを獲得、レベルアップ）
- 🗡️ プレイヤー対戦（対人PvP）
- 🏪 武器・防具ショップ（8段階のアイテム）
- 🏰 国家システム（建国・加入・離脱）
- 💬 チャット機能
- 🏆 ランキング（経験値順TOP10）

## セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/your-username/endless-battle.git
cd endless-battle

# 2. 依存パッケージをインストール
pip install -r requirements.txt

# 3. 起動
python app.py
```

ブラウザで http://localhost:5000 を開くとプレイできます。

## 本番環境での公開

### Render（無料）
1. GitHubにpushする
2. [render.com](https://render.com) でNew Web Serviceを作成
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. 環境変数 `SECRET_KEY` に任意の文字列を設定

### Railway / Fly.io でも同様に公開可能

## ゲームの仕様

### レベルアップ
- 経験値は `100 × level^1.8` で次のレベルへ
- 最大レベル: 99

### モンスター（8種類）
| モンスター | 出現Lv | EXP | GOLD |
|-----------|--------|-----|------|
| スライム | 1 | 10 | 15 |
| ゴブリン | 2 | 25 | 30 |
| オーク | 4 | 55 | 60 |
| トロール | 7 | 110 | 110 |
| ワイバーン | 11 | 200 | 200 |
| ドラゴン | 17 | 400 | 380 |
| 魔王の使い | 24 | 750 | 700 |
| 魔王 | 33 | 1500 | 1500 |

### 武器・防具（各8段階）
木の剣 → 銅の剣 → 鉄の剣 → 鋼の剣 → 銀の剣 → 魔法の剣 → ドラゴン刃 → 神剣

## ライセンス
MIT
