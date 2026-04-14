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
        return df
    return pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])

def save_data(df, user_id):
    filename = get_user_filename(user_id)
    df.to_csv(filename, index=False)

def show_progress_chart(df):
    """과목별 진척도를 타이틀 옆에 작은 바 형태로 표시"""
    if df.empty:
        return
    
    tasks = df['Task'].unique()
    # 과목이 많을 경우 최대 4컬럼으로 나누어 표시
    cols = st.columns(min(len(tasks), 4))
    
    for i, task in enumerate(tasks):
        task_df = df[df['Task'] == task]
        total = len(task_df)
        done = len(task_df[task_df['Status'] == 'Done'])
        percent = done / total if total > 0 else 0
        
        # 컬럼 순환 배치 (i % 4)
        with cols[i % 4]:
            st.caption(f"**{task}** ({done}/{total})")
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

# --- 4. 메인 기능 (로그인 완료 후) ---
current_user = st.session_state.user_id

# 사이드바 설정
with st.sidebar:
    st.subheader(f"👤 {current_user}님")
    if st.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    # 사이드바: 계획 추가 섹션 내부에 추가
    st.header("➕ 새 계획 추가")
        task_name = st.text_input("학습 과목명")
        total_units = st.number_input("전체 분량", min_value=1, value=10)

    # 시작 날짜와 마감일 설정 (시작일은 오늘 이후, 마감일은 시작일 이후로 제한)
    start_date = st.date_input("학습 시작일", value=datetime.now().date())
    target_date = st.date_input("목표 마감일", min_value=start_date, value=start_date + timedelta(days=7))

    
    mode = st.radio("배분 방식", ["일찍 끝내기", "끝까지 분산"])
    min_limit = st.number_input("하루 최소 분량", min_value=1, value=5)
    
    interval = st.number_input("날짜 간격 (1은 매일)", min_value=1, value=1)
    
    if st.button("계획 생성 및 저장", use_container_width=True):
        if task_name:
            today = datetime.now().date()
            days_available = (target_date - today).days + 1
            new_entries = []
            remaining_units = total_units
            possible_days = [today + timedelta(days=i) for i in range(days_available) if i % interval == 0]
            
            if possible_days:
                for i, current_date in enumerate(possible_days):
                    if remaining_units <= 0: break
                    days_left = len(possible_days) - i
                    
                    if days_left == 1:
                        daily_amount = remaining_units
                    else:
                        ideal = remaining_units // days_left
                        daily_amount = max(min_limit, ideal) if mode == "일찍 끝내기" else max(min_limit, ideal)
                        daily_amount = min(daily_amount, remaining_units)
                    
                    new_entries.append({'Task': task_name, 'Date': current_date, 'Amount': daily_amount, 'Status': 'Pending'})
                    remaining_units -= daily_amount

                current_df = load_data(current_user)
                updated_df = pd.concat([current_df, pd.DataFrame(new_entries)], ignore_index=True)
                save_data(updated_df, current_user)
                st.success("계획이 추가되었습니다!")
                st.rerun()

# 데이터 로드
display_df = load_data(current_user)

# --- 타이틀은 데이터 유무와 상관없이 항상 최상단에 고정 ---
st.title(f"📚 {current_user}님의 스마트 플래너")

if not display_df.empty:
    # 1. 진척도 요약 (타이틀 바로 아래 콤팩트하게 배치)
    with st.container():
        show_progress_chart(display_df)
    
    st.divider()
    
    # 2. 메인 탭 (일정 및 미션)
    display_df = display_df.sort_values(by=['Date', 'Task']).reset_index(drop=True)
    tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        if st.button("데이터 전체 초기화"):
            save_data(pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status']), current_user)
            st.rerun()

    with tab2:
        today_val = datetime.now().date()
        today_indices = display_df[display_df['Date'] == today_val].index
        
        if not today_indices.empty:
            for idx in today_indices:
                row = display_df.loc[idx]
                c1, c2 = st.columns([0.8, 0.2])
                with c1:
                    is_done = (row['Status'] == 'Done')
                    check = st.checkbox(f"{row['Task']} ({row['Amount']}개)", value=is_done, key=f"chk_{idx}")
                    if check != is_done:
                        display_df.at[idx, 'Status'] = 'Done' if check else 'Pending'
                        save_data(display_df, current_user)
                        st.rerun()
                with c2:
                    if row['Status'] == 'Done':
                        if st.button("🗑️ 삭제", key=f"del_{idx}"):
                            new_df = display_df.drop(idx)
                            save_data(new_df, current_user)
                            st.rerun()
        else:
            st.info("오늘 예정된 학습이 없습니다.")
            
else:
    # --- 데이터가 없을 때만 보이는 안내 문구 ---
    st.divider()
    st.info("💡 아직 등록된 계획이 없습니다. 왼쪽 사이드바에서 새로운 학습 계획을 추가해 보세요!")
    # 사용자가 당황하지 않게 사이드바를 보라는 화살표나 안내를 추가해도 좋습니다.
