"""
database.py
Supabaseを使ったユーザー管理モジュール
アプリ起動時に管理者アカウントが存在しない場合のみ初期管理者を作成する
"""

import re
import bcrypt
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _get_client() -> Client:
    """Supabaseクライアントを返す。アプリ起動時に1回だけ接続する。"""
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def init_db():
    """
    管理者アカウントが1件もない場合のみデフォルト管理者を作成する。
    Supabaseのテーブルはあらかじめ作成済みであること。
    """
    client = _get_client()
    result = client.table("users").select("id").eq("is_admin", True).execute()
    if not result.data:
        default_pw = st.secrets.get("admin", {}).get("default_password", "admin123")
        _create_user_internal(client, "admin", default_pw, is_admin=True)
        print(f"デフォルト管理者アカウントを作成しました (admin / {default_pw})")
        print("※ログイン後、必ずパスワードを変更してください")


def authenticate(username: str, password: str) -> dict | None:
    """
    ユーザー名とパスワードで認証する。
    認証成功時はユーザー情報のdictを返す。失敗時はNoneを返す。
    """
    client = _get_client()
    result = client.table("users").select("*").eq("username", username).execute()
    if not result.data:
        return None
    user = result.data[0]
    if not _verify_password(password, user["password"]):
        return None
    return {
        "id":       user["id"],
        "username": user["username"],
        "is_admin": user["is_admin"],
    }


def get_all_users() -> list[dict]:
    """全ユーザーの一覧を返す（パスワードは除く）。"""
    client = _get_client()
    result = client.table("users").select("id, username, is_admin, created_at").order("id").execute()
    return result.data or []


def create_user(username: str, password: str, is_admin: bool = False) -> bool:
    """
    新規ユーザーを作成する。
    ユーザー名が重複している場合はFalseを返す。
    """
    client = _get_client()
    try:
        _create_user_internal(client, username, password, is_admin)
        return True
    except Exception:
        return False  # ユーザー名重複など


def delete_user(user_id: int) -> bool:
    """指定IDのユーザーを削除する。管理者が最後の1人の場合は削除しない。"""
    client = _get_client()
    target = client.table("users").select("is_admin").eq("id", user_id).execute()
    if not target.data:
        return False
    if target.data[0]["is_admin"]:
        admin_count = client.table("users").select("id").eq("is_admin", True).execute()
        if len(admin_count.data) <= 1:
            return False  # 最後の管理者は削除不可
    client.table("users").delete().eq("id", user_id).execute()
    return True


def change_password(user_id: int, new_password: str):
    """指定ユーザーのパスワードを変更する。"""
    client = _get_client()
    hashed = _hash_password(new_password)
    client.table("users").update({"password": hashed}).eq("id", user_id).execute()


def change_role(user_id: int, is_admin: bool) -> bool:
    """
    指定ユーザーの権限を変更する。
    管理者を一般ユーザーに降格する場合、最後の管理者であれば変更しない。
    """
    client = _get_client()
    if not is_admin:
        admin_count = client.table("users").select("id").eq("is_admin", True).execute()
        target = client.table("users").select("is_admin").eq("id", user_id).execute()
        if target.data and target.data[0]["is_admin"] and len(admin_count.data) <= 1:
            return False
    client.table("users").update({"is_admin": is_admin}).eq("id", user_id).execute()
    return True


def validate_username(username: str) -> str | None:
    """ユーザーIDのバリデーション。問題があればエラーメッセージを返す。"""
    if len(username) < 4:
        return "ユーザーIDは4文字以上で入力してください。"
    if not re.fullmatch(r"[A-Za-z0-9]+", username):
        return "ユーザーIDは半角英数字のみ使用できます。"
    return None


def validate_password(password: str) -> str | None:
    """パスワードのバリデーション。問題があればエラーメッセージを返す。"""
    if len(password) < 8:
        return "パスワードは8文字以上で入力してください。"
    if not re.fullmatch(r"[A-Za-z0-9]+", password):
        return "パスワードは半角英数字のみ使用できます。"
    return None


# ── 内部ヘルパー ──────────────────────────────────────────────────────────────

def _create_user_internal(client: Client, username: str, password: str, is_admin: bool):
    """Supabaseにユーザーを挿入する内部関数。"""
    hashed = _hash_password(password)
    client.table("users").insert({
        "username": username,
        "password": hashed,
        "is_admin": is_admin,
    }).execute()


def _hash_password(password: str) -> str:
    """パスワードをbcryptでハッシュ化して返す。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """入力パスワードとハッシュを照合する。"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
