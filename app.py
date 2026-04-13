import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# --- 1. 데이터 관리 함수 ---
def get_user_filename(user_id):
    """아이디별 고유 파일명 생성"""
    safe_id = user_id.strip().replace(" ", "_")
    return f"plan_{safe_id}.csv"

def load_data(user_id):
    """사용자 파일에서 데이터 로드"""
    filename = get_user_filename(user_id)
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])

def save_data(df, user_id):
    """사용자 파일에 데이터 저장"""
    filename = get_user_filename(user_id)
    df.to_csv(filename, index=False)

def show_progress_chart(df):
    """타이틀 옆에 작고 깔끔한 직사각형 바 형태로 표시"""
    if df.empty:
        return
    
    # 과목별 데이터 계산
    tasks = df['Task'].unique()
    
    # 한 줄에 여러 과목이 나오도록 컬럼 배치
    cols = st.columns(len(tasks) if len(tasks) > 0 else 1)
    
    for i, task in enumerate(tasks):
        task_df = df[df['Task'] == task]
        total = len(task_df)
        done = len(task_df[task_df['Status'] == 'Done'])
        percent = done / total
        
        with cols[i]:
            # 과목명과 개수 표시
            st.caption(f"**{task}** ({done}/{total})")
            # 그라데이션 없는 단색(파란색) 막대
            st.progress(percent)

# --- 3. 메인 기능 (로그인 완료된 경우에만 실행) ---
# 세션에 user_id가 있는 경우에만 변수 할당
if st.session_state.user_id:
    current_user = st.session_state.user_id
    
    # 1. 데이터 불러오기 (함수 호출 시 current_user 전달)
    display_df = load_data(current_user)
    
    st.title(f"📚 {current_user}님의 스마트 플래너")

    # 2. 데이터가 있는 경우에만 그래프와 탭 표시
    if not display_df.empty:
        # 제목과 그래프 배치
        col_title, col_status = st.columns([0.3, 0.7])
        with col_title:
            st.subheader("📊 과목 현황")
        with col_status:
            show_progress_chart(display_df)
        
        st.divider()
        
        # 탭 로직 (전체 일정 / 오늘의 미션)
        display_df = display_df.sort_values(by=['Date', 'Task']).reset_index(drop=True)
        tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
        
        # ... (이후 tab1, tab2 내부 코드는 그대로 유지) ...
        
    else:
        st.info("왼쪽 사이드바에서 계획을 추가해 보세요!")
else:
    # 혹시 모를 에러 방지용: 세션 아이디가 없으면 다시 로그인 유도
    st.warning("로그인이 필요합니다.")
    st.rerun()




# --- 2. 페이지 설정 및 로그인 ---
st.set_page_config(page_title="스마트 학습 플래너", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.title("🔐 학습 플래너 접속")
    user_input = st.text_input("사용자 아이디를 입력하세요", placeholder="예: 길동이")
    if st.button("접속하기"):
        if user_input:
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.warning("아이디를 입력해주세요.")
    st.stop()

# --- 3. 메인 기능 (로그인 후) ---
current_user = st.session_state.user_id
st.title(f"📚 {current_user}님의 스마트 플래너")

# 사이드바: 계획 추가 및 로그아웃
with st.sidebar:
    st.subheader(f"👤 {current_user}님")
    if st.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()
    
    st.divider()
    st.header("➕ 새 계획 추가")
    task_name = st.text_input("학습 과목명")
    total_units = st.number_input("전체 분량", min_value=1, value=10)
    target_date = st.date_input("목표 마감일", min_value=datetime.now().date())
    
    mode = st.radio("배분 방식", ["일찍 끝내기", "끝까지 분산"])
    min_limit = st.number_input("하루 최소 분량", min_value=1, value=5)
    
    interval = 1
    if mode == "일찍 끝내기":
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
                    if i == len(possible_days) - 1:
                        daily_amount = remaining_units
                    else:
                        ideal = remaining_units // (len(possible_days) - i)
                        daily_amount = max(min_limit, ideal) if mode == "일찍 끝내기" else max(min_limit, remaining_units // (len(possible_days) - i))
                        daily_amount = min(daily_amount, remaining_units)
                    
                    new_entries.append({'Task': task_name, 'Date': current_date, 'Amount': daily_amount, 'Status': 'Pending'})
                    remaining_units -= daily_amount

                current_df = load_data(current_user)
                updated_df = pd.concat([current_df, pd.DataFrame(new_entries)], ignore_index=True)
                save_data(updated_df, current_user)
                st.success("계획이 추가되었습니다!")
                st.rerun()

# 메인 화면 데이터 표시
display_df = load_data(current_user)

if not display_df.empty:
    # 상단 진척도 그래프
    show_progress_chart(display_df)
    
    display_df = display_df.sort_values(by=['Date', 'Task']).reset_index(drop=True)
    tab1, tab2 = st.tabs(["📅 전체 일정", "✅ 오늘의 미션"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        if st.button("데이터 전체 초기화", type="secondary"):
            save_data(pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status']), current_user)
            st.rerun()

    with tab2:
        st.subheader("오늘 할 일")
        today_val = datetime.now().date()
        # 원본 display_df의 인덱스를 유지하기 위해 필터링 후 인덱스 사용
        today_indices = display_df[display_df['Date'] == today_val].index
        
        if not today_indices.empty:
            for idx in today_indices:
                row = display_df.loc[idx]
                col_check, col_del = st.columns([0.8, 0.2])
                
                with col_check:
                    is_done = (row['Status'] == 'Done')
                    check = st.checkbox(f"{row['Task']} - {row['Amount']}개", value=is_done, key=f"chk_{idx}")
                    if check != is_done:
                        display_df.at[idx, 'Status'] = 'Done' if check else 'Pending'
                        save_data(display_df, current_user)
                        st.rerun()
                
                with col_del:
                    if row['Status'] == 'Done':
                        if st.button("🗑️ 삭제", key=f"del_{idx}"):
                            new_df = display_df.drop(idx)
                            save_data(new_df, current_user)
                            st.rerun()
        else:
            st.info("오늘 예정된 학습이 없습니다.")
else:
    st.info("계획을 추가하여 학습을 시작해보세요!")
