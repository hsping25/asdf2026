import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- [멀티유저/세션 관리 핵심 로직] ---
# 서버의 파일(CSV)이 아닌, 각 브라우저 세션 메모리에 데이터를 저장합니다.
if 'user_plan' not in st.session_state:
    st.session_state.user_plan = pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])

def load_session_data():
    return st.session_state.user_plan

def save_session_data(df):
    st.session_state.user_plan = df

# --- 페이지 설정 ---
st.set_page_config(page_title="개인별 학습 플래너", layout="wide")
st.title("🔐 개인 세션 학습 플래너")
st.caption("이 창에서 입력한 계획은 이 창에서만 유지됩니다. (새로고침 시 초기화)")

# --- 사이드바 입력창 ---
with st.sidebar:
    st.header("➕ 새로운 계획 추가")
    task_name = st.text_input("학습 종류", placeholder="예: 파이썬")
    total_units = st.number_input("전체 분량", min_value=1, value=10)
    target_date = st.date_input("목표 마감일", min_value=datetime.now().date())
    
    st.divider()
    mode = st.radio("배분 방식", ["일찍 끝내기", "끝까지 분산"])
    min_limit = st.number_input("하루 최소 분량", min_value=1, value=5)
    
    interval = 1
    if mode == "일찍 끝내기":
        interval = st.number_input("날짜 간격 (1은 매일)", min_value=1, value=1)
    
    add_btn = st.button("계획 생성", use_container_width=True)

# --- 계획 생성 로직 ---
if add_btn and task_name:
    today = datetime.now().date()
    days_available = (target_date - today).days + 1
    
    new_entries = []
    remaining_units = total_units
    possible_days = [today + timedelta(days=i) for i in range(days_available) if i % interval == 0]
    
    if possible_days:
        for i, current_date in enumerate(possible_days):
            if remaining_units <= 0: break
            
            if i == len(possible_days) - 1:
                daily_amount = remaining_units
            else:
                if mode == "일찍 끝내기":
                    ideal_daily = remaining_units // (len(possible_days) - i)
                    daily_amount = max(min_limit, ideal_daily)
                else:
                    daily_amount = max(min_limit, remaining_units // (len(possible_days) - i))
                daily_amount = min(daily_amount, remaining_units)
                
            new_entries.append({'Task': task_name, 'Date': current_date, 'Amount': daily_amount, 'Status': 'Pending'})
            remaining_units -= daily_amount

        new_df = pd.DataFrame(new_entries)
        # 세션 데이터에 병합
        updated_df = pd.concat([load_session_data(), new_df], ignore_index=True)
        save_session_data(updated_df)
        st.success(f"'{task_name}' 계획이 추가되었습니다!")
        st.rerun()

# --- 메인 화면 출력 및 삭제 기능 ---
display_df = load_session_data()

if not display_df.empty:
    display_df['Date'] = pd.to_datetime(display_df['Date']).dt.date
    display_df = display_df.sort_values(by=['Date', 'Task'])
    
    tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        if st.button("🗑️ 세션 데이터 전체 초기화"):
            st.session_state.user_plan = pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])
            st.rerun()
        
    with tab2:
        today_val = datetime.now().date()
        today_tasks = display_df[display_df['Date'] == today_val].copy()
        
        if not today_tasks.empty:
            for idx, row in today_tasks.iterrows():
                col_task, col_delete = st.columns([0.8, 0.2])
                
                with col_task:
                    is_done = (row['Status'] == 'Done')
                    check = st.checkbox(f"{row['Task']} ({row['Amount']}개)", value=is_done, key=f"chk_{idx}")
                    
                    if check != is_done:
                        display_df.at[idx, 'Status'] = 'Done' if check else 'Pending'
                        save_session_data(display_df)
                        st.rerun()

                with col_delete:
                    if row['Status'] == 'Done':
                        if st.button("🗑️ 삭제", key=f"del_{idx}"):
                            updated_df = display_df.drop(idx)
                            save_session_data(updated_df)
                            st.rerun()
        else:
            st.info("오늘의 계획이 없습니다.")
else:
    st.info("왼쪽에서 계획을 입력해 보세요. 이 데이터는 브라우저를 닫으면 사라집니다.")
