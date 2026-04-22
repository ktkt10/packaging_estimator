"""
utils/auth.py
Streamlitのsession_stateを使った認証ヘルパーモジュール
各ページの先頭でrequire_login()を呼ぶだけでログイン必須にできる
ユーザー情報は utils/database.py (Supabase + bcrypt) で管理する
"""

import streamlit as st
from utils.database import authenticate


def login(username: str, password: str) -> bool:
    """
    ログイン処理。
    認証成功時はsession_stateにユーザー情報をセットしてTrueを返す。
    """
    user = authenticate(username, password)
    if user:
        st.session_state["logged_in"] = True
        st.session_state["user"]      = user
        st.session_state["username"]  = user["username"]
        return True
    return False


def logout():
    """ログアウト処理。session_stateをクリアする。"""
    st.session_state.clear()


def is_logged_in() -> bool:
    """ログイン済みかどうかを返す。"""
    return st.session_state.get("logged_in", False)


def is_admin() -> bool:
    """現在ログイン中のユーザーが管理者かどうかを返す。"""
    user = st.session_state.get("user", {})
    return user.get("is_admin", False)


def current_user() -> dict:
    """現在ログイン中のユーザー情報を返す。未ログイン時は空のdictを返す。"""
    return st.session_state.get("user", {})


def require_login():
    """
    ログインが必要なページの先頭で呼ぶ。
    未ログインの場合はログインページにリダイレクトする。
    """
    if not is_logged_in():
        st.switch_page("Home.py")
        st.stop()


def require_admin():
    """
    管理者権限が必要なページの先頭で呼ぶ。
    管理者でない場合はエラーメッセージを表示してページの処理を停止する。
    """
    require_login()
    if not is_admin():
        st.error("このページは管理者のみアクセスできます。")
        st.stop()
