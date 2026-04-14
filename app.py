import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 1. 데이터 관리 함수 ---
def get_user_filename(user_id):
    safe_id = user_id.strip().replace(" ", "_")
    return f"plan_{safe_id}.csv"

def load_data(user_id):
    filename = get_user_filename(user_id)
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            # Group_ID 컬럼이 없으면 추가
            if 'Group_ID' not in df.columns:
                df['Group_ID'] = "Default"
        return df
    return pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status', 'Group_ID'])

def save_data(df, user_id):
    filename = get_user_filename(user_id)
    df.to_csv(filename, index=False)

def show_progress_chart(df):
    """과목별 진척도를 그룹별 아이콘과 함께 표시"""
    if df.empty:
        return
    
    # 그룹별 아이콘 설정
    group_icons = ["🟦", "🟩", "🟧", "🟥", "🟪", "🟨", "🟫", "⬛"]
    unique_groups = df['Group_ID'].unique()
    group_map = {gid: group_icons[i % len(group_icons)] for i, gid in enumerate(unique_groups)}

    tasks = df['Task'].unique()
    cols = st.columns(min(len(tasks), 4))
    
    for i, task in enumerate(tasks):
        task_df = df[df['Task'] == task]
        latest_gid = task_df['Group_ID'].iloc[-1]
        icon = group_map.get(latest_gid, "⚪")
        
        total = len(task_df)
        done = len(task_df[task_df['Status'] == 'Done'])
        percent = done / total if total > 0 else 0
        
        with cols[i % 4]:
            with st.container(border=True):
                st.markdown(f"{icon} **{task}**")
                st.caption(f"완료: {done}/{total}")
                st.progress(percent)

# --- 2. 페이지 설정 및 세션 초기화 ---
st.set_page_config(page_title="스마트 학습 플래너", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- 3. 로그인 로직 ---
if st.session_state.user_id is None:
    st.title("🔐 학습 플래너 접속")
    user_input = st.text_input("사용자 아이디를 입력하세요")
    if st.button("접속하기"):
        if user_input:
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.warning("아이디를 입력해주세요.")
    st.stop()

# --- 4. 메인 기능 ---
current_user = st.session_state.user_id
display_df = load_data(current_user) # 데이터 먼저 로드

# 사이드바 설정
with st.sidebar:
    st.subheader(f"👤 {current_user}님")
    if st.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    st.header("➕ 새 계획 추가")
    task_name = st.text_input("학습 과목명")
    total_units = st.number_input("전체 분량", min_value=1, value=10)

    start_date = st.date_input("학습 시작일", value=datetime.now().date())
    target_date = st.date_input("목표 마감일", min_value=start_date, value=start_date + timedelta(days=7))
    
    mode = st.radio("배분 방식", ["일찍 끝내기", "끝까지 분산"])
    min_limit = st.number_input("하루 최소 분량", min_value=1, value=5)
    interval = st.number_input("날짜 간격 (1은 매일)", min_value=1, value=1)
    
    # ✅ 수정: 버튼을 사이드바(with) 안으로 이동
    if st.button("계획 생성 및 저장", use_container_width=True):
        if task_name:
            group_id = datetime.now().strftime("%H%M%S")
            days_available = (target_date - start_date).days + 1
            new_entries = []
            remaining_units = total_units
            
            possible_days = [start_date + timedelta(days=i) for i in range(days_available) if i % interval == 0]
            
            if possible_days:
                for i, current_date in enumerate(possible_days):
                    if remaining_units <= 0: break
                    days_left = len(possible_days) - i
                    ideal = remaining_units // days_left
                    daily_amount = max(min_limit, ideal)
                    daily_amount = min(daily_amount, remaining_units)
                    
                    new_entries.append({
                        'Task': task_name, 
                        'Date': current_date, 
                        'Amount': daily_amount, 
                        'Status': 'Pending',
                        'Group_ID': group_id
                    })
                    remaining_units -= daily_amount

                updated_df = pd.concat([display_df, pd.DataFrame(new_entries)], ignore_index=True)
                save_data(updated_df, current_user)
                st.success(f"{start_date}부터 시작하는 계획 생성 완료!")
                st.rerun()

# --- 메인 화면 ---
st.title(f"📚 {current_user}님의 스마트 플래너")

if not display_df.empty:
    with st.container():
        show_progress_chart(display_df)
    
    st.divider()
    
    display_df = display_df.sort_values(by=['Date', 'Task']).reset_index(drop=True)
    tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        if st.button("데이터 전체 초기화"):
            save_data(pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status', 'Group_ID']), current_user)
            st.rerun()

    with tab2:
        today_val = datetime.now().date()
        today_indices = display_df[display_df['Date'] == today_val].index
        
        if not today_indices.empty:
            # 그룹별 아이콘 다시 매핑 (색상 구분을 위해)
            group_icons = ["🟦", "🟩", "🟧", "🟥", "🟪", "🟨", "🟫", "⬛"]
            unique_groups = display_df['Group_ID'].unique()
            group_map = {gid: group_icons[i % len(group_icons)] for i, gid in enumerate(unique_groups)}

            for idx in today_indices:
                row = display_df.loc[idx]
                icon = group_map.get(row['Group_ID'], "⚪")
                
                # --- [수정 포인트] 셀 색깔 효과를 위한 컨테이너 ---
                with st.container(border=True):
                    c1, c2 = st.columns([0.8, 0.2])
                    
                    with c1:
                        is_done = (row['Status'] == 'Done')
                        # 과목명 앞에 그룹 색상 아이콘을 붙여 '색깔이 바뀐 효과'를 줌
                        label = f"{icon} **{row['Task']}** ({row['Amount']}개)"
                        if is_done:
                            label = f"✅ ~{label}~" # 완료 시 취소선
                        
                        check = st.checkbox(label, value=is_done, key=f"chk_{idx}")
                        
                        if check != is_done:
                            display_df.at[idx, 'Status'] = 'Done' if check else 'Pending'
                            save_data(display_df, current_user)
                            st.rerun()
                    
                    with c2:
                        if is_done:
                            if st.button("🗑️ 삭제", key=f"del_{idx}", use_container_width=True):
                                save_data(display_df.drop(idx), current_user)
                                st.rerun()
        else:
            st.info("오늘 예정된 학습이 없습니다.")

