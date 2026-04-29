"""
2_ユーザー管理.py
管理者専用のユーザー管理ページ
ユーザーの一覧表示・新規追加・パスワード変更・削除ができる
ユーザー情報は Supabase で管理する
"""

import sys
import os
from datetime import datetime, timezone, timedelta

import streamlit as st

for _p in [os.getcwd(), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from utils.auth import require_admin, logout, current_user
from utils.database import get_all_users, create_user, delete_user, change_password, change_role, validate_username, validate_password

st.set_page_config(page_title="ユーザー管理", page_icon="👤", layout="wide")
require_admin()

JST = timezone(timedelta(hours=9))

def fmt_jst(iso_str: str) -> str:
    """ISO 8601文字列をJST（UTC+9）の 'YYYY-MM-DD HH:MM:SS' 形式に変換する。"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_str


with st.sidebar:
    st.write(f"👤 {st.session_state.get('username', '')} (管理者)")
    if st.button("ログアウト"):
        logout()
        st.switch_page("Home.py")

st.header("👤 ユーザー管理")
st.caption("管理者専用ページです")
st.markdown("---")

users = get_all_users()
me    = current_user()

# ── ユーザー一覧（権限変更・削除をインライン表示） ────────────────────────────
st.subheader("登録ユーザー一覧")

# 保存・削除の成功メッセージ（rerun後に表示）
if "success_msg" in st.session_state:
    st.success(st.session_state.pop("success_msg"))

# 削除確認ボックス
confirm_uid = st.session_state.get("confirm_delete_id")
if confirm_uid:
    confirm_user = next((u for u in users if u["id"] == confirm_uid), None)
    if confirm_user:
        st.warning(f"ユーザー「{confirm_user['username']}」を削除しますか？")
        btn_yes, btn_no, _ = st.columns([1, 1, 6])
        if btn_yes.button("はい", type="primary"):
            if delete_user(confirm_uid):
                st.session_state.pop("confirm_delete_id", None)
                st.session_state["success_msg"] = f"ユーザー「{confirm_user['username']}」を削除しました。"
            else:
                st.session_state.pop("confirm_delete_id", None)
                st.error("最後の管理者は削除できません。")
            st.rerun()
        if btn_no.button("キャンセル"):
            st.session_state.pop("confirm_delete_id", None)
            st.rerun()

if not users:
    st.info("登録ユーザーがいません。")
else:
    COL_W = [2, 2, 3, 1, 1]

    # ヘッダー行
    h1, h2, h3, h4, h5 = st.columns(COL_W)
    h1.markdown("**ユーザーID**")
    h2.markdown("**権限**")
    h3.markdown("**登録日時**")
    h4.markdown("**保存**")
    h5.markdown("**削除**")
    st.divider()

    # データ行
    for u in users:
        uid      = u["id"]
        is_me    = uid == me.get("id")
        role_key = f"role_{uid}"

        c1, c2, c3, c4, c5 = st.columns(COL_W)

        c1.write(u["username"])

        selected_role = c2.selectbox(
            "権限",
            options=["管理者", "一般ユーザー"],
            index=0 if u["is_admin"] else 1,
            key=role_key,
            label_visibility="collapsed",
        )

        c3.write(fmt_jst(u.get("created_at", "")))

        if c4.button("保存", key=f"save_{uid}"):
            new_is_admin = (st.session_state[role_key] == "管理者")
            if u["is_admin"] == new_is_admin:
                st.toast(f"「{u['username']}」の権限に変更はありません。")
            elif not change_role(uid, new_is_admin):
                st.toast("最後の管理者は一般ユーザーに変更できません。", icon="⚠️")
            else:
                st.session_state["success_msg"] = f"「{u['username']}」の権限を{st.session_state[role_key]}に変更しました。"
                st.rerun()

        if c5.button("削除", key=f"delete_{uid}", disabled=is_me, type="secondary"):
            st.session_state["confirm_delete_id"] = uid
            st.rerun()

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

with st.form("add_user_form", clear_on_submit=True):
    new_username  = st.text_input("ユーザーID")
    st.markdown("<p style='text-align:right;font-size:0.8rem;color:gray;margin-top:-12px'>半角英数字のみ、4文字以上</p>", unsafe_allow_html=True)
    new_password  = st.text_input("パスワード", type="password")
    st.markdown("<p style='text-align:right;font-size:0.8rem;color:gray;margin-top:-12px'>半角英数字のみ、8文字以上</p>", unsafe_allow_html=True)
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
