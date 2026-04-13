import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# 1. 데이터 관리 함수
DB_FILE = 'study_plan.csv'

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date']).dt.date
        return df
    return pd.DataFrame(columns=['Task', 'Date', 'Amount', 'Status'])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

# 2. 페이지 설정 및 제목
st.set_page_config(page_title="스마트 학습 플래너", layout="wide")
st.title("📚 스마트 학습 플래너")

# 3. 사이드바 입력창 (없어졌다면 이 부분을 확인하세요!)
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
    
    add_btn = st.button("계획 생성 및 저장", use_container_width=True)

# 4. 계획 생성 로직
if add_btn and task_name:
    today = datetime.now().date()
    days_available = (target_date - today).days + 1
    
    new_entries = []
    remaining_units = total_units
    possible_days = [today + timedelta(days=i) for i in range(days_available) if i % interval == 0]
    
    if not possible_days:
        st.error("설정한 조건으로 배분할 수 있는 날짜가 없습니다.")
    else:
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

        # 데이터 업데이트
        new_df = pd.DataFrame(new_entries)
        all_df = pd.concat([load_data(), new_df], ignore_index=True)
        save_data(all_df)
        st.success(f"'{task_name}' 계획이 추가되었습니다!")
        st.rerun()

# 5. 메인 화면: 결과 출력 및 삭제 기능
display_df = load_data()

if not display_df.empty:
    display_df = display_df.sort_values(by=['Date', 'Task'])
    
    tab1, tab2, tab3 = st.tabs(["📅 전체 일정", "✅ 오늘의 할 일", "🛠️ 관리 및 삭제"])
    
    with tab1:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
    with tab2:
        today_val = datetime.now().date()
        today_tasks = display_df[display_df['Date'] == today_val]
        if not today_tasks.empty:
            st.table(today_tasks[['Task', 'Amount', 'Status']])
        else:
            st.info("오늘 예정된 학습이 없습니다. 여유로운 하루 되세요! ☕")

    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("과목별 삭제")
            unique_tasks = display_df['Task'].unique()
            task_to_delete = st.selectbox("과목 선택", unique_tasks)
            if st.button(f"'{task_to_delete}' 전체 삭제"):
                new_df = display_df[display_df['Task'] != task_to_delete]
                save_data(new_df)
                st.rerun()

        with col2:
            st.subheader("개별 일정 삭제")
            selected_rows = st.multiselect(
                "삭제할 행 선택",
                options=display_df.index,
                format_func=lambda x: f"{display_df.loc[x, 'Date']} | {display_df.loc[x, 'Task']} ({display_df.loc[x, 'Amount']})"
            )
            if st.button("선택 삭제"):
                new_df = display_df.drop(selected_rows)
                save_data(new_df)
                st.rerun()
else:
    st.info("왼쪽 사이드바의 [새로운 계획 추가] 메뉴를 이용해 첫 일정을 만들어 보세요!")