"""
database.py
SQLiteを使ったユーザー管理モジュール。
アプリ起動時に自動でDBとテーブルを作成します。
"""

import re
import sqlite3
import bcrypt
from pathlib import Path

try:
    import streamlit as st
    _has_streamlit = True
except ImportError:
    _has_streamlit = False

# DBファイルのパス（このファイルと同じディレクトリに作成）
DB_PATH = Path(__file__).parent.parent / "users.db"


def get_connection() -> sqlite3.Connection:
    """SQLite接続を返す。行をdictとして取得できるようrow_factoryを設定する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    DBとusersテーブルを初期化する。
    テーブルが存在しない場合のみ作成し、管理者アカウントも初期生成する。
    """
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,  -- bcryptハッシュ
                is_admin    INTEGER NOT NULL DEFAULT 0,  -- 1=管理者
                created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()

        # 管理者アカウントが1件もなければデフォルト管理者を作成
        admin_exists = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_admin = 1"
        ).fetchone()[0]

        if admin_exists == 0:
            default_pw = _get_default_admin_password()
            _create_user(conn, username="admin", password=default_pw, is_admin=True)
            print(f"デフォルト管理者アカウントを作成しました (admin / {default_pw})")
            print("※ログイン後、必ずパスワードを変更してください")

    finally:
        conn.close()


def _get_default_admin_password() -> str:
    """
    デフォルト管理者パスワードを取得する。
    Streamlit Cloud / ローカル開発では st.secrets["admin"]["default_password"] を使用。
    secrets が未設定の場合はフォールバック値を返す（開発環境専用）。
    """
    if _has_streamlit:
        try:
            return st.secrets["admin"]["default_password"]
        except (KeyError, FileNotFoundError):
            pass
    raise RuntimeError(
        "管理者パスワードが設定されていません。"
        ".streamlit/secrets.toml に [admin] default_password を設定してください。"
    )


def validate_username(username: str) -> str | None:
    """
    ユーザーIDのバリデーション。
    問題がある場合はエラーメッセージを返す。問題なければ None を返す。
    ルール: 半角英数字のみ、4文字以上
    """
    if len(username) < 4:
        return "ユーザーIDは4文字以上で入力してください。"
    if not re.fullmatch(r"[A-Za-z0-9]+", username):
        return "ユーザーIDは半角英数字のみ使用できます。"
    return None


def validate_password(password: str) -> str | None:
    """
    パスワードのバリデーション。
    問題がある場合はエラーメッセージを返す。問題なければ None を返す。
    ルール: 半角英数字のみ、8文字以上
    """
    if len(password) < 8:
        return "パスワードは8文字以上で入力してください。"
    if not re.fullmatch(r"[A-Za-z0-9]+", password):
        return "パスワードは半角英数字のみ使用できます。"
    return None


def _hash_password(password: str) -> str:
    """パスワードをbcryptでハッシュ化して返す。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """入力パスワードとハッシュを照合する。"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _create_user(conn: sqlite3.Connection, username: str, password: str, is_admin: bool = False):
    """接続を受け取ってユーザーを作成する内部関数。"""
    hashed = _hash_password(password)
    conn.execute(
        "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
        (username, hashed, 1 if is_admin else 0),
    )
    conn.commit()


def authenticate(username: str, password: str) -> dict | None:
    """
    ユーザー名とパスワードで認証する。
    認証成功時はユーザー情報のdictを返す。失敗時はNoneを返す。
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if row is None:
            return None  # ユーザーが存在しない

        if not _verify_password(password, row["password"]):
            return None  # パスワード不一致

        return {
            "id": row["id"],
            "username": row["username"],
            "is_admin": bool(row["is_admin"]),
        }
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    """全ユーザーの一覧を返す（パスワードは除く）。"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    """
    新規ユーザーを作成する。
    ユーザー名が重複している場合はFalseを返す。
    """
    conn = get_connection()
    try:
        _create_user(conn, username, password, is_admin)
        return True
    except sqlite3.IntegrityError:
        return False  # ユーザー名重複
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    """指定IDのユーザーを削除する。管理者が最後の1人の場合は削除しない。"""
    conn = get_connection()
    try:
        # 削除対象が管理者かどうか確認
        target = conn.execute(
            "SELECT is_admin FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if target is None:
            return False  # 対象ユーザーが存在しない

        if target["is_admin"]:
            # 管理者が1人しかいない場合は削除しない
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_admin = 1"
            ).fetchone()[0]
            if admin_count <= 1:
                return False  # 最後の管理者は削除不可

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def change_password(user_id: int, new_password: str):
    """指定ユーザーのパスワードを変更する。"""
    conn = get_connection()
    try:
        hashed = _hash_password(new_password)
        conn.execute(
            "UPDATE users SET password = ? WHERE id = ?", (hashed, user_id)
        )
        conn.commit()
    finally:
        conn.close()
