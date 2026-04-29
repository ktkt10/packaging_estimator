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
from utils.database import create_user, validate_username, validate_password

st.set_page_config(
    page_title="梱包サイズ推定",
    page_icon="📦",
    layout="wide",
)


def show_login_signup():
    st.header("📦 梱包サイズ推定")
    st.markdown("---")

    _, col, _ = st.columns([1, 2, 1])
    with col:
        # ── ログイン ──────────────────────────────────────────────────
        st.subheader("ログイン")
        with st.form("login_form"):
            username  = st.text_input("ユーザー名")
            password  = st.text_input("パスワード", type="password")
            submitted = st.form_submit_button("ログイン", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください。")
            elif login(username, password):
                st.switch_page("pages/1_梱包サイズ推定.py")
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")

        st.markdown("---")

        # ── 新規登録 ──────────────────────────────────────────────────
        st.subheader("新規ユーザー登録")
        with st.form("signup_form", clear_on_submit=True):
            new_username  = st.text_input("ユーザーID")
            st.markdown("<p style='text-align:right;font-size:0.8rem;color:gray;margin-top:-12px'>半角英数字のみ、4文字以上</p>", unsafe_allow_html=True)
            new_password  = st.text_input("パスワード", type="password")
            st.markdown("<p style='text-align:right;font-size:0.8rem;color:gray;margin-top:-12px'>半角英数字のみ、8文字以上</p>", unsafe_allow_html=True)
            new_password2 = st.text_input("パスワード（確認）", type="password")
            signup_submitted = st.form_submit_button("アカウントを作成", use_container_width=True)

        if signup_submitted:
            if not new_username:
                st.error("ユーザーIDを入力してください。")
            elif (err := validate_username(new_username)):
                st.error(err)
            elif not new_password:
                st.error("パスワードを入力してください。")
            elif new_password != new_password2:
                st.error("パスワードが一致しません。")
            elif (err := validate_password(new_password)):
                st.error(err)
            elif not create_user(new_username, new_password, is_admin=False):
                st.error(f"ユーザーID「{new_username}」は既に使用されています。")
            else:
                st.success(f"アカウント「{new_username}」を作成しました。上のログインフォームからログインしてください。")


if is_logged_in():
    st.switch_page("pages/1_梱包サイズ推定.py")
else:
    show_login_signup()
