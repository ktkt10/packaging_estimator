"""
2_ユーザー管理.py
管理者専用のユーザー管理ページ
ユーザーの一覧表示・新規追加・パスワード変更・削除ができる
ユーザー情報は users.db (SQLite) で管理
"""

import sys
import os

import streamlit as st

# プロジェクトルートをパスに追加
for _p in [os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from utils.auth import require_admin, logout, current_user
from utils.database import get_all_users, create_user, delete_user, change_password, validate_username, validate_password

st.set_page_config(page_title="ユーザー管理", page_icon="👤", layout="wide")
require_admin()

with st.sidebar:
    st.write(f"👤 {st.session_state.get('username', '')} (管理者)")
    if st.button("ログアウト"):
        logout()
        st.switch_page("Home.py")

st.header("👤 ユーザー管理")
st.caption("管理者専用ページです。")
st.markdown("---")

# ── ユーザー一覧 ──────────────────────────────────────────────────────────────
st.subheader("登録ユーザー一覧")

users = get_all_users()
me    = current_user()

if not users:
    st.info("登録ユーザーがいません。")
else:
    import pandas as pd
    df = pd.DataFrame([
        {
            "ユーザーID": u["username"],
            "権限":       "管理者" if u["is_admin"] else "一般ユーザー",
            "登録日時":   u.get("created_at", ""),
        }
        for u in users
    ])
    st.dataframe(df, width="stretch", hide_index=True)

    # 削除対象の選択（自分自身は除外）
    deletable = [u for u in users if u["id"] != me.get("id")]
    if deletable:
        st.markdown("**ユーザー削除**")
        del_target = st.selectbox(
            "削除するユーザーを選択",
            options=[u["username"] for u in deletable],
            key="del_select",
        )
        if st.button("削除する", type="secondary"):
            target_id = next(u["id"] for u in deletable if u["username"] == del_target)
            if delete_user(target_id):
                st.success(f"ユーザー「{del_target}」を削除しました。")
                st.rerun()
            else:
                st.error("削除できませんでした。（最後の管理者は削除できません）")

st.markdown("---")

# ── パスワード変更 ────────────────────────────────────────────────────────────
st.subheader("パスワード変更")

user_options = {u["username"]: u["id"] for u in users}

with st.form("change_password_form", clear_on_submit=True):
    target_username = st.selectbox("対象ユーザー", options=list(user_options.keys()))
    new_pw          = st.text_input("新しいパスワード", type="password")
    new_pw2         = st.text_input("新しいパスワード（確認）", type="password")
    pw_submitted    = st.form_submit_button("変更する")

if pw_submitted:
    if not new_pw:
        st.error("新しいパスワードを入力してください。")
    elif new_pw != new_pw2:
        st.error("パスワードが一致しません。")
    elif (err := validate_password(new_pw)):
        st.error(err)
    else:
        change_password(user_options[target_username], new_pw)
        st.success(f"「{target_username}」のパスワードを変更しました。")

st.markdown("---")

# ── 新規ユーザー追加 ──────────────────────────────────────────────────────────
st.subheader("新規ユーザー追加")

st.info(
    "**入力ルール**\n"
    "- ユーザーID：半角英数字のみ、4文字以上、他ユーザーと重複不可\n"
    "- パスワード：半角英数字のみ、8文字以上"
)

with st.form("add_user_form", clear_on_submit=True):
    new_username  = st.text_input("ユーザーID")
    new_password  = st.text_input("パスワード", type="password")
    new_password2 = st.text_input("パスワード（確認）", type="password")
    new_is_admin  = st.checkbox("管理者権限を付与する")
    submitted     = st.form_submit_button("追加")

if submitted:
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
    elif not create_user(new_username, new_password, is_admin=new_is_admin):
        st.error(f"ユーザーID「{new_username}」は既に使用されています。")
    else:
        role = "管理者" if new_is_admin else "一般ユーザー"
        st.success(f"ユーザー「{new_username}」（{role}）を追加しました。")
        st.rerun()
