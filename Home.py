"""
Home.py
Streamlitアプリのエントリーポイント（ログイン画面）
ユーザー情報は Supabase で管理。初回起動時に管理者アカウントを自動生成する
"""

import sys
import os

for _p in [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from utils.database import init_db
init_db()

import streamlit as st
from utils.auth import login, is_logged_in

st.set_page_config(
    page_title="梱包サイズ推定",
    page_icon="📦",
    layout="wide",
)


def show_login_form():
    st.header("📦 梱包サイズ推定")
    st.markdown("---")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.subheader("ログイン")
        with st.form("login_form"):
            username  = st.text_input("ユーザー名")
            password  = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン", width="stretch")

        if submitted:
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください。")
            elif login(username, password):
                st.switch_page("pages/1_梱包サイズ推定.py")
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")


if is_logged_in():
    st.switch_page("pages/1_梱包サイズ推定.py")
else:
    show_login_form()
