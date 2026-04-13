import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# 1. 사용자별 데이터 로드 및 저장 함수
def get_user_filename(user_id):
    # 파일명에 공백이 있으면 안 되므로 처리
    safe_id = user_id.strip().replace(" ", "_")
    return f"plan_{safe_id}.csv"

def load_data(user_id):
    filename = get_user_filename(user_id)
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])

def save_data(df, user_id):
    filename = get_user_filename(user_id)
    df.to_csv(filename, index=False)

# 2. 페이지 설정
st.set_page_config(page_title="멀티유저 학습 플래너", layout="wide")

# 3. 로그인 세션 관리
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# 로그인 화면
if st.session_state.user_id is None:
    st.title("🔐 학습 플래너 로그인")
    user_input = st.text_input("사용자 아이디를 입력하세요", placeholder="예: 길동이")
    if st.button("접속하기"):
        if user_input:
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.warning("아이디를 입력해야 합니다.")
    st.stop() # 로그인이 안 되면 아래 코드를 실행하지 않음

# --- 여기서부터는 로그인 성공 시 실행되는 코드 ---
current_user = st.session_state.user_id
st.title(f"📚 {current_user}님의 학습 플래너")

with st.sidebar:
    st.header(f"👤 {current_user}님 환영합니다!")
    if st.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    st.header("➕ 새로운 계획 추가")
    task_name = st.text_input("학습 종류")
    total_units = st.number_input("전체 분량", min_value=1, value=10)
    target_date = st.date_input("목표 마감일", min_value=datetime.now().date())
    
    mode = st.radio("배분 방식", ["일찍 끝내기", "끝까지 분산"])
    min_limit = st.number_input("하루 최소 분량", min_value=1, value=5)
    
    interval = 1
    if mode == "일찍 끝내기":
        interval = st.number_input("날짜 간격 (1은 매일)", min_value=1, value=1)
    
    add_btn = st.button("계획 생성", use_container_width=True)

# 데이터 불러오기
display_df = load_data(current_user)

# 계획 생성 로직
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
        updated_df = pd.concat([display_df, new_df], ignore_index=True)
        save_data(updated_df, current_user)
        st.success("계획이 추가되었습니다!")
        st.rerun()

# 메인 화면 출력
if not display_df.empty:
    display_df = display_df.sort_values(by=['Date', 'Task'])
    tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
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
                        save_data(display_df, current_user)
                        st.rerun()
                with col_delete:
                    if row['Status'] == 'Done':
                        if st.button("🗑️ 삭제", key=f"del_{idx}"):
                            updated_df = display_df.drop(idx)
                            save_data(updated_df, current_user)
                            st.rerun()
        else:
            st.info("오늘 예정된 학습이 없습니다.")
else:
    st.info("왼쪽 사이드바에서 첫 계획을 추가해 보세요!")
