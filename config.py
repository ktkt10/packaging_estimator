"""
config.py
アプリ全体で使う定数・マスターデータ。
"""

# メーカーリスト（ドロップダウン用）
MANUFACTURERS = [
    "",
    "Alter",
    "ALTER",
    "AOSHIMA",
    "BANDAI",
    "BANDAI SPIRITS",
    "BANDAI SPRITS",
    "BUSHIROAD",
    "ENSKY",
    "EPOCH",
    "FROOF",
    "FUJIMI",
    "GOOD SMILE COMPANY",
    "Hasegawa",
    "HASEGAWA",
    "KATO",
    "KOTOBUKIYA",
    "Kyosho Egg",
    "Kyosyo",
    "Max Factory",
    "MegaHouse",
    "Micro ace",
    "MONO CHROME",
    "PIT ROAD",
    "PLATZ",
    "Pokemon",
    "Proof",
    "quesQ",
    "Sanei Boeki",
    "SQUARE ENIX",
    "TAKARA TOMY",
    "TAMASHII NATIONS",
    "TAMIYA",
    "TOMYTEC",
]

# カテゴリ（第2階層）リスト（ドロップダウン用）
CATEGORY_2_OPTIONS = [
    "",
    "Anime Figure",
    "Figure",
    "Kids' Toy",
    "Mini 4WD",
    "Model Kits",
    "Model Trains",
    "Puzzle",
    "RC Car",
    "Stuffed animals",
    "Stuffed Toys",
    "Toys",
    "Trading Card",
]

# サブカテゴリ（第3階層）リスト（category_2 → リスト の辞書）
CATEGORY_3_OPTIONS: dict[str, list[str]] = {
    "": [""],
    "Anime Figure": [
        "",
        "Demon Slayer",
        "Etc",
        "FAIRY TAIL",
        "Final Fantasy",
        "Genshin Impact",
        "Girls Und Panzer",
        "Inuyasha",
        "Jujutsu Kaisen",
        "Mazinger Z",
        "My Hero Academia",
        "NARUTO",
        "ONE PIECE",
        "Robot",
        "Transformer",
        "Uma Musume",
        "Video Game",
    ],
    "Figure": [
        "",
        "KAMEN RIDER",
        "MARVEL",
        "METAL ROBOT Spirits",
        "Monster Collection",
        "Neon Genesis Evangelion",
        "One Piece",
        "ZOIDS",
    ],
    "Kids' Toy": [
        "",
        "BEYBLADE",
        "Kamen Rider",
        "Licca-chan",
        "Pokemon",
        "Sylvanian Families",
        "Train",
    ],
    "Mini 4WD": [
        "",
        "Mini 4WD",
    ],
    "Model Kits": [
        "",
        "30 MINUTES MISSIONS",
        "Accessary",
        "Aircraft",
        "Airplane",
        "Anime Figure",
        "Bike",
        "Car & Truck",
        "Gundam",
        "Gundam HG",
        "Gundam MG",
        "Gundam PG",
        "Military",
        "Robot",
        "Ships & Submarines",
        "Star Wars",
        "Tank",
        "Warship",
        "ZOIDS",
    ],
    "Model Trains": [
        "",
        "Train",
        "Train Parts",
    ],
    "Puzzle": [
        "",
        "Landscape",
        "Pokemon",
    ],
    "RC Car": [
        "",
        "Car & Truck",
        "Parts & Accessories",
        "Parts & Accessory",
    ],
    "Stuffed animals": [
        "",
        "Pokemon",
        "umamusume",
    ],
    "Stuffed Toys": [
        "",
        "Animals",
        "Characters",
        "DIGIMON",
        "Nintendo",
        "Pokemon",
    ],
    "Toys": [
        "",
        "Robot",
    ],
    "Trading Card": [
        "",
        "Pokemon",
        "SUPER DRAGON BALL HEROES",
        "UNION ARENA",
        "Weiss Schwarz",
    ],
}

# メーカー → カテゴリ（第2階層）マップ（メーカー選択時のカテゴリ絞り込み用）
MANUFACTURER_CATEGORY_MAP: dict[str, list[str]] = {
    "Alter": ["Anime Figure"],
    "ALTER": ["Anime Figure"],
    "AOSHIMA": ["Model Kits"],
    "BANDAI": ["Figure", "Kids' Toy", "Stuffed Toys", "Trading Card"],
    "BANDAI SPIRITS": ["Anime Figure", "Figure", "Model Kits"],
    "BANDAI SPRITS": ["Model Kits"],
    "BUSHIROAD": ["Trading Card"],
    "ENSKY": ["Puzzle"],
    "EPOCH": ["Kids' Toy"],
    "FROOF": ["Anime Figure"],
    "FUJIMI": ["Model Kits"],
    "GOOD SMILE COMPANY": ["Anime Figure", "Model Kits", "Stuffed animals", "Stuffed Toys"],
    "Hasegawa": ["Model Kits"],
    "HASEGAWA": ["Model Kits"],
    "KATO": ["Model Trains"],
    "KOTOBUKIYA": ["Anime Figure", "Figure", "Model Kits"],
    "Kyosho Egg": ["RC Car"],
    "Kyosyo": ["RC Car"],
    "Max Factory": ["Anime Figure", "Model Kits"],
    "MegaHouse": ["Anime Figure"],
    "Micro ace": ["Model Kits"],
    "MONO CHROME": ["Model Kits"],
    "PIT ROAD": ["Model Kits"],
    "PLATZ": ["Model Kits"],
    "Pokemon": ["Trading Card"],
    "Proof": ["Anime Figure"],
    "quesQ": ["Anime Figure"],
    "Sanei Boeki": ["Stuffed animals", "Stuffed Toys"],
    "SQUARE ENIX": ["Anime Figure", "Stuffed Toys"],
    "TAKARA TOMY": ["Anime Figure", "Figure", "Kids' Toy", "Model Kits", "Stuffed Toys", "Toys"],
    "TAMASHII NATIONS": ["Anime Figure"],
    "TAMIYA": ["Mini 4WD", "Model Kits", "RC Car"],
    "TOMYTEC": ["Model Trains"],
}

# メーカー × カテゴリ → シリーズリスト（シリーズ選択肢の絞り込み用）
SERIES_MAP: dict[str, dict[str, list[str]]] = {
    "Alter": {
        "Anime Figure": ["ウマ娘 プリティーダービー", "原神"],
    },
    "ALTER": {
        "Anime Figure": ["ARTFX J"],
    },
    "AOSHIMA": {
        "Model Kits": ["アイアンクラッド(鋼鉄艦)", "ザ・チューンドカー", "ザ・モデルカー", "頭文字D"],
    },
    "BANDAI": {
        "Figure": ["DXアイテム(王様戦隊キングオージャー)"],
        "Kids' Toy": ["仮面ライダーディケイド"],
        "Stuffed Toys": ["アプリアライズアクション"],
        "Trading Card": ["UNION ARENA(ユニオンアリーナ)", "ドラゴンボール"],
    },
    "BANDAI SPIRITS": {
        "Anime Figure": ["Figuarts Zero Touche Metallique", "PROPLICA(プロップリカ)", "ROBOT魂(ロボット魂)", "S.H.フィギュアーツ", "ジャンボマシンダー", "フィギュアーツZERO", "超合金", "超合金魂"],
        "Figure": ["DYNACTION(ダイナクション)", "S.H.フィギュアーツ", "フィギュアライズスタンダード", "フィギュアーツZERO", "メタルビルド", "超合金魂"],
        "Model Kits": ["30 MINUTES MISSIONS", "HG", "HGUC", "MG その他", "MG ガンダム00", "MG ガンダムUC", "ゲッターロボG", "ザ・マンダロリアン", "ハイレゾリューションモデル", "パーフェクトグレード(PG)", "リアルグレード(RG)", "ワンピース", "宇宙戦艦ヤマト2202", "機動警察パトレイバー(MG)"],
    },
    "BANDAI SPRITS": {
        "Model Kits": ["HG"],
    },
    "BUSHIROAD": {
        "Trading Card": ["ヴァイスシュヴァルツブラウ"],
    },
    "ENSKY": {
        "Puzzle": ["ジグソーパズル"],
    },
    "EPOCH": {
        "Kids' Toy": ["シルバニアファミリー"],
    },
    "FROOF": {
        "Anime Figure": ["僕のヒーローアカデミア"],
    },
    "FUJIMI": {
        "Model Kits": ["1/350 艦船(フジミ)"],
    },
    "GOOD SMILE COMPANY": {
        "Anime Figure": ["POP UP PARADE(ポップアップパレード)", "ブルーアーカイブ -Blue Archive-"],
        "Model Kits": ["figma(フィグマ)"],
        "Stuffed animals": ["ぬいぐるみ"],
        "Stuffed Toys": ["ぬいぐるみ"],
    },
    "HASEGAWA": {
        "Model Kits": ["1/350 艦船(ハセガワ)", "超時空要塞マクロス"],
    },
    "KATO": {
        "Model Trains": ["入門セット", "車両セット(新幹線)", "車両単品(蒸気機関車)", "車両単品(電気機関車)"],
    },
    "KOTOBUKIYA": {
        "Anime Figure": ["ARTFX J", "ウマ娘 プリティーダービー"],
        "Figure": ["ARTFX PREMIER"],
        "Model Kits": ["HMM(ハイエンド マスターモデル)", "METAL GEAR SOLID", "V.I.(ヴァリアブル.インフィニティ.)", "フレームアームズ・ガール", "ヘキサギア", "ヱヴァンゲリヲン新劇場版"],
    },
    "Kyosho Egg": {
        "RC Car": ["MINI-Z Racer(ミニッツ レーサー)"],
    },
    "Kyosyo": {
        "RC Car": ["MINI-Z Racer(ミニッツ レーサー)"],
    },
    "Max Factory": {
        "Anime Figure": ["figma(フィグマ)"],
        "Model Kits": ["PLAMAX"],
    },
    "MegaHouse": {
        "Anime Figure": ["るかっぷ"],
    },
    "Micro ace": {
        "Model Kits": ["ビッグスケール戦艦"],
    },
    "PIT ROAD": {
        "Model Kits": ["ガールズ＆パンツァー", "スカイウェーブ"],
    },
    "PLATZ": {
        "Model Kits": ["BEEMAX"],
    },
    "Pokemon": {
        "Trading Card": ["ポケモンカードゲーム(カード)"],
    },
    "Proof": {
        "Anime Figure": ["犬夜叉"],
    },
    "quesQ": {
        "Anime Figure": ["ガールズ＆パンツァー 劇場版"],
    },
    "Sanei Boeki": {
        "Stuffed animals": ["クッション"],
        "Stuffed Toys": ["ぬいぐるみ"],
    },
    "SQUARE ENIX": {
        "Anime Figure": ["プレイアーツ改"],
        "Stuffed Toys": ["ぬいぐるみ"],
    },
    "TAKARA TOMY": {
        "Anime Figure": ["ウォーフォーサイバトロン"],
        "Figure": ["ZOIDS(ゾイド)", "ゾイドワイルド"],
        "Kids' Toy": ["プラレール(セット)", "リカちゃん"],
        "Model Kits": ["トランスフォーマー ゴー", "トランスフォーマー プライム"],
        "Stuffed Toys": ["ぬいぐるみ", "リカちゃん"],
        "Toys": ["ダイアクロン", "トランスフォーマー", "プラレール(車両)", "マスターピースG"],
    },
    "TAMASHII NATIONS": {
        "Anime Figure": ["S.H.フィギュアーツ"],
    },
    "TAMIYA": {
        "Mini 4WD": ["グレードアップパーツ", "サーキットコース", "ミニ四駆限定"],
        "Model Kits": ["1/32 エアークラフト", "1/350 艦船(タミヤ)", "1/48 傑作機", "1/6 オートバイ", "ビッグスケール"],
        "RC Car": ["RCシステム", "RCビッグトラック", "XBエキスパートビルト", "スターユニットシリーズ", "電動RCカー"],
    },
    "TOMYTEC": {
        "Model Trains": ["レール・レール関連", "入門セット"],
    },
}

# Pinecone インデックス設定
PINECONE_INDEX_NAME = "hobby-packaging"
PINECONE_DIMENSION  = 1536          # text-embedding-3-small の次元数
PINECONE_METRIC     = "cosine"

# 検索設定
TOP_K = 5                           # 類似商品を何件取得するか

# LLM設定（梱包サイズ推定用）
OPENAI_CHAT_MODEL = "gpt-4.1-mini"  # 推定に使うチャットモデル
