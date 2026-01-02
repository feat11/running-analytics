import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os
import json
from datetime import datetime, timedelta
import calendar

# --- 페이지 설정 (다크모드 기본) ---
st.set_page_config(
    page_title="🏃‍♂️ Running Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 커스텀 CSS (Strava 스타일 + 애니메이션) ---
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 메인 컨테이너 - 여백 줄임 */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    
    /* 커스텀 메트릭 카드 - 크기 줄임 */
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: transform 0.3s ease;
        margin-bottom: 10px;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(45deg, #FF6B6B, #FFD93D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.2;
    }
    
    .metric-label {
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.85rem;
        font-weight: 500;
        margin-top: 5px;
    }
    
    .metric-delta {
        color: #6BCF7F;
        font-size: 0.9rem;
        margin-top: 5px;
    }
    
    /* 헤더 스타일 - 크기 줄임 */
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-bottom: 5px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .hero-subtitle {
        font-size: 1rem;
        color: rgba(255, 255, 255, 0.8);
        text-align: center;
        margin-bottom: 15px;
    }
    
    /* 프로그레스 바 */
    .progress-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    
    .progress-bar {
        height: 25px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        transition: width 1s ease;
    }
    
    /* 뱃지 스타일 */
    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        font-weight: 600;
        margin: 5px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2C3E50 0%, #34495E 100%);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
        font-weight: 600;
        padding: 8px 16px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 섹션 제목 크기 줄임 */
    h2 {
        font-size: 1.5rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    h3 {
        font-size: 1.2rem !important;
        margin-top: 0.3rem !important;
        margin-bottom: 0.3rem !important;
    }
    
    /* Plotly 차트 여백 줄임 */
    .js-plotly-plot {
        margin-bottom: 10px !important;
    }
    
    /* 구분선 여백 줄임 */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 토큰 및 데이터 관리 함수 ---
@st.cache_data(ttl=3600)
def get_access_token():
    """Refresh Token을 이용해 새로운 Access Token을 발급받습니다."""
    payload = {
        'client_id': st.secrets["strava"]["client_id"],
        'client_secret': st.secrets["strava"]["client_secret"],
        'refresh_token': st.secrets["strava"]["refresh_token"],
        'grant_type': 'refresh_token',
        'f': 'json'
    }
    auth_url = "https://www.strava.com/oauth/token"
    res = requests.post(auth_url, data=payload, verify=False)
    res.raise_for_status()
    access_token = res.json()['access_token']
    return access_token

@st.cache_data(ttl=1800)
def fetch_strava_data(limit=200):
    """Strava API에서 모든 데이터 가져오기
    
    페이지네이션을 사용하여 모든 활동 데이터를 가져옵니다.
    Strava API는 한 번에 최대 200개까지만 반환하므로,
    데이터가 없을 때까지 계속 요청합니다.
    """
    token = get_access_token()
    headers = {'Authorization': f"Bearer {token}"}
    
    all_activities = []
    page = 1
    per_page = 200  # Strava API 최대값
    
    # 모든 데이터를 가져올 때까지 반복
    while True:
        param = {'per_page': per_page, 'page': page}
        dataset_url = "https://www.strava.com/api/v3/athlete/activities"
        
        res = requests.get(dataset_url, headers=headers, params=param, verify=False)
        data = res.json()
        
        if not data:  # 더 이상 데이터가 없으면 중단
            break
        
        all_activities.extend(data)
        
        if len(data) < per_page:  # 마지막 페이지면 중단
            break
        
        page += 1
        
        # API 제한 확인 (안전장치)
        if page > 100:  # 20,000개가 넘어가면 중단 (비정상적인 경우)
            break
    
    return all_activities

def process_data(data):
    """데이터 전처리 및 추가 계산"""
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        return pd.DataFrame()
    
    cols = ['name', 'distance', 'moving_time', 'start_date_local', 'total_elevation_gain', 
            'type', 'average_heartrate', 'max_heartrate', 'average_speed', 'max_speed']
    available_cols = [c for c in cols if c in df.columns]
    df = df[available_cols]

    df['start_date_local'] = pd.to_datetime(df['start_date_local'])
    
    # 중요: date 컬럼 생성 (CSV 저장/로드 시에도 유지되도록)
    df['date'] = pd.to_datetime(df['start_date_local']).dt.date
    df['hour'] = df['start_date_local'].dt.hour
    df['weekday'] = df['start_date_local'].dt.day_name()
    df['week'] = df['start_date_local'].dt.isocalendar().week
    df['month'] = df['start_date_local'].dt.month
    df['year'] = df['start_date_local'].dt.year
    
    df['distance_km'] = df['distance'] / 1000
    df['moving_time_min'] = df['moving_time'] / 60
    df['pace'] = df.apply(lambda x: x['moving_time_min'] / x['distance_km'] if x['distance_km'] > 0 else 0, axis=1)
    
    # 페이스 존 분류
    df['pace_zone'] = df['pace'].apply(classify_pace_zone)
    
    # 시간대 분류
    df['time_of_day'] = df['hour'].apply(classify_time_of_day)
    
    return df

def classify_pace_zone(pace):
    """페이스 존 분류"""
    if pace == 0:
        return "Unknown"
    elif pace < 4.5:
        return "🔥 Speed (< 4:30)"
    elif pace < 5.5:
        return "⚡ Tempo (4:30-5:30)"
    elif pace < 6.5:
        return "🏃 Easy (5:30-6:30)"
    else:
        return "🚶 Recovery (> 6:30)"

def classify_time_of_day(hour):
    """시간대 분류"""
    if 5 <= hour < 12:
        return "🌅 Morning"
    elif 12 <= hour < 18:
        return "☀️ Afternoon"
    else:
        return "🌙 Evening"

def format_pace(pace_minutes):
    """페이스를 분:초 형식으로 변환 (예: 5.5 -> 5:30)"""
    if pace_minutes == 0 or pd.isna(pace_minutes):
        return "-"
    minutes = int(pace_minutes)
    seconds = int((pace_minutes - minutes) * 60)
    return f"{minutes}:{seconds:02d}"

CSV_FILE = 'running_data.csv'
CONFIG_FILE = 'app_config.json'

def load_config():
    """설정 파일 로드"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'monthly_goal': 100,
        'last_update': None
    }

def save_config(config):
    """설정 파일 저장"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def should_update_data(config):
    """데이터를 업데이트해야 하는지 확인 (매일 08시)"""
    if not config.get('last_update'):
        return True
    
    last_update = datetime.fromisoformat(config['last_update'])
    now = datetime.now()
    
    # 마지막 업데이트가 오늘 08시 이전이고, 현재 시간이 08시 이후면 업데이트
    today_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
    
    if last_update < today_8am <= now:
        return True
    
    # 또는 마지막 업데이트가 어제 이전이면 업데이트
    if last_update.date() < now.date():
        return True
    
    return False

def load_data():
    """CSV가 있으면 CSV를 읽고, 없으면 API를 호출"""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df['start_date_local'] = pd.to_datetime(df['start_date_local'])
        
        # date 컬럼이 없으면 생성
        if 'date' not in df.columns:
            df['date'] = pd.to_datetime(df['start_date_local']).dt.date
        else:
            df['date'] = pd.to_datetime(df['date']).dt.date
        
        # 필요한 컬럼들 재생성 (CSV에 없을 수 있음)
        if 'hour' not in df.columns:
            df['hour'] = df['start_date_local'].dt.hour
        if 'weekday' not in df.columns:
            df['weekday'] = df['start_date_local'].dt.day_name()
        if 'week' not in df.columns:
            df['week'] = df['start_date_local'].dt.isocalendar().week
        if 'month' not in df.columns:
            df['month'] = df['start_date_local'].dt.month
        if 'year' not in df.columns:
            df['year'] = df['start_date_local'].dt.year
        if 'pace_zone' not in df.columns and 'pace' in df.columns:
            df['pace_zone'] = df['pace'].apply(classify_pace_zone)
        if 'time_of_day' not in df.columns and 'hour' in df.columns:
            df['time_of_day'] = df['hour'].apply(classify_time_of_day)
        
        return df
    else:
        raw_data = fetch_strava_data()
        df = process_data(raw_data)
        df.to_csv(CSV_FILE, index=False)
        return df

def update_data():
    """강제로 API를 호출하여 CSV를 업데이트"""
    with st.spinner('🔄 Strava에서 모든 데이터 동기화 중...'):
        try:
            raw_data = fetch_strava_data()
            df = process_data(raw_data)
            df.to_csv(CSV_FILE, index=False)
            
            # 설정 파일에 업데이트 시간 저장
            config = load_config()
            config['last_update'] = datetime.now().isoformat()
            save_config(config)
            
            st.cache_data.clear()
            st.success(f"✅ 데이터 업데이트 완료! (총 {len(df)}개 활동)")
            st.rerun()
        except Exception as e:
            st.error(f"❌ 업데이트 실패: {e}")
            return None

def auto_update_if_needed():
    """필요시 자동 업데이트 (매일 08시)"""
    config = load_config()
    if should_update_data(config):
        st.info("🔄 일일 자동 업데이트 중...")
        try:
            raw_data = fetch_strava_data()
            df = process_data(raw_data)
            df.to_csv(CSV_FILE, index=False)
            
            config['last_update'] = datetime.now().isoformat()
            save_config(config)
            
            st.cache_data.clear()
            st.success(f"✅ 자동 업데이트 완료! (총 {len(df)}개 활동)")
            return df
        except Exception as e:
            st.warning(f"자동 업데이트 실패: {e}")
            return None
    return None

# --- 히트맵 생성 함수 ---
def create_activity_heatmap(df):
    """GitHub 스타일 활동 히트맵 생성"""
    # date 컬럼이 없으면 생성
    if 'date' not in df.columns:
        df = df.copy()
        df['date'] = pd.to_datetime(df['start_date_local']).dt.date
    
    # 최근 365일 데이터
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=364)
    
    # 날짜별 거리 집계
    daily_km = df.groupby('date')['distance_km'].sum().reset_index()
    
    # 전체 날짜 범위 생성
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    full_df = pd.DataFrame({'date': date_range.date})
    full_df = full_df.merge(daily_km, on='date', how='left').fillna(0)
    
    # 주차와 요일 계산
    full_df['week'] = full_df['date'].apply(lambda x: (x - start_date).days // 7)
    full_df['weekday'] = pd.to_datetime(full_df['date']).dt.dayofweek
    
    # 피벗 테이블 생성
    heatmap_data = full_df.pivot(index='weekday', columns='week', values='distance_km')
    
    # Plotly 히트맵
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        colorscale=[[0, '#0d47a1'], [0.5, '#ffa726'], [1, '#d32f2f']],  # 파란색 → 주황색 → 빨간색
        showscale=True,
        hovertemplate='Week %{x}<br>%{y}<br>%{z:.1f} km<extra></extra>'
    ))
    
    fig.update_layout(
        title="📅 Annual Activity Heatmap",
        xaxis_title="Week",
        yaxis_title="",
        height=200,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        margin=dict(l=50, r=50, t=50, b=30)
    )
    
    return fig

# --- 메인 앱 ---
def main():
    # 설정 로드
    config = load_config()
    
    # 헤더
    st.markdown('<h1 class="hero-title">🏃‍♂️ @run.seob Running Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Track, Analyze, and Improve Your Running Performance</p>', unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        # 마지막 업데이트 시간 표시
        if config.get('last_update'):
            last_update_time = datetime.fromisoformat(config['last_update'])
            st.caption(f"마지막 업데이트: {last_update_time.strftime('%Y-%m-%d %H:%M')}")
        
        st.info("💡 Strava API는 15분당 100회, 일일 1,000회 제한이 있습니다. 자동으로 매일 08시에 업데이트됩니다.")
        
        if st.button("🔄 Sync Strava Data", use_container_width=True):
            update_data()
        
        st.markdown("---")
        
        # 필터 옵션
        st.markdown("### 📊 Data Filter")
        date_filter = st.selectbox(
            "기간 선택",
            ["This Month", "All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year"],
            index=0  # This Month가 기본값
        )
        
        st.markdown("---")
        
        # 목표 설정 - 저장된 값 불러오기
        st.markdown("### 🎯 Monthly Goal")
        monthly_goal = st.number_input(
            "목표 거리 (km)", 
            min_value=0, 
            max_value=1000, 
            value=config.get('monthly_goal', 100), 
            step=10
        )
        
        # 목표 거리가 변경되면 저장
        if monthly_goal != config.get('monthly_goal', 100):
            config['monthly_goal'] = monthly_goal
            save_config(config)
    
    # 자동 업데이트 체크
    auto_df = auto_update_if_needed()
    
    # 데이터 로드
    df = load_data()
    
    if df is None or df.empty:
        st.info("데이터가 없습니다. 사이드바의 업데이트 버튼을 눌러주세요.")
        return
    
    # Run만 필터링
    if 'type' in df.columns:
        df = df[df['type'] == 'Run']
    
    # 날짜 필터 적용
    today = datetime.now()
    
    # date 컬럼이 없으면 생성
    if 'date' not in df.columns:
        df['date'] = pd.to_datetime(df['start_date_local']).dt.date
    
    if date_filter == "This Month":
        df_filtered = df[
            (df['start_date_local'].dt.year == today.year) & 
            (df['start_date_local'].dt.month == today.month)
        ]
        period_label = f"{today.year}년 {today.month}월"
    elif date_filter == "Last 7 Days":
        cutoff_date = (today - timedelta(days=7)).date()
        df_filtered = df[df['date'] >= cutoff_date]
        period_label = "최근 7일"
    elif date_filter == "Last 30 Days":
        cutoff_date = (today - timedelta(days=30)).date()
        df_filtered = df[df['date'] >= cutoff_date]
        period_label = "최근 30일"
    elif date_filter == "Last 90 Days":
        cutoff_date = (today - timedelta(days=90)).date()
        df_filtered = df[df['date'] >= cutoff_date]
        period_label = "최근 90일"
    elif date_filter == "This Year":
        df_filtered = df[df['start_date_local'].dt.year == today.year]
        period_label = f"{today.year}년"
    else:  # All Time
        df_filtered = df
        period_label = "전체 기간"
    
    # --- 히어로 메트릭 섹션 ---
    st.markdown(f"## 📈 Key Metrics - {period_label}")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_km = df_filtered['distance_km'].sum()
    total_runs = len(df_filtered)
    avg_pace = df_filtered[df_filtered['pace'] > 0]['pace'].mean()
    total_elevation = df_filtered['total_elevation_gain'].sum() if 'total_elevation_gain' in df_filtered.columns else 0
    
    # 최장 거리
    longest_run = df_filtered['distance_km'].max() if not df_filtered.empty else 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_km:.1f}</div>
            <div class="metric-label">Total Distance (km)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_runs}</div>
            <div class="metric-label">Total Runs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pace_formatted = format_pace(avg_pace)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{pace_formatted}</div>
            <div class="metric-label">Avg Pace (min/km)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{longest_run:.1f}</div>
            <div class="metric-label">Longest Run (km)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{int(total_elevation)}</div>
            <div class="metric-label">Total Elevation (m)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- 월간 목표 진행률 ---
    current_month_km = df[
        (df['start_date_local'].dt.year == today.year) & 
        (df['start_date_local'].dt.month == today.month)
    ]['distance_km'].sum()
    
    progress_pct = min((current_month_km / monthly_goal * 100), 100) if monthly_goal > 0 else 0
    
    st.markdown("---")
    st.markdown("## 🎯 Monthly Goal Progress")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(progress_pct / 100)
    with col2:
        st.metric("Progress", f"{progress_pct:.1f}%", f"{current_month_km:.1f} / {monthly_goal} km")
    
    if progress_pct >= 100:
        st.success("🎉 축하합니다! 이번 달 목표를 달성했습니다!")
    
    # --- 히트맵 ---
    st.markdown("---")
    heatmap_fig = create_activity_heatmap(df)
    st.plotly_chart(heatmap_fig, use_container_width=True)
    
    # --- 탭 섹션 ---
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Trends & Stats", 
        "⚡ Pace Analysis", 
        "🏆 Personal Records", 
        "🕒 Activity Patterns",
        "📝 Raw Data"
    ])
    
    with tab1:
        st.markdown("### 📊 Running Trends")
        
        # 월별 거리
        col1, col2 = st.columns(2)
        
        with col1:
            monthly_data = df.groupby([df['start_date_local'].dt.to_period('M')])['distance_km'].sum().reset_index()
            monthly_data['start_date_local'] = monthly_data['start_date_local'].astype(str)
            
            fig_monthly = px.bar(
                monthly_data, 
                x='start_date_local', 
                y='distance_km',
                title="Monthly Distance",
                labels={'distance_km': 'Distance (km)', 'start_date_local': 'Month'},
                color='distance_km',
                color_continuous_scale='Blues_r'  # 적을수록 파란색, 많을수록 빨간색
            )
            fig_monthly.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=300,
                margin=dict(l=50, r=50, t=50, b=50)
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col2:
            # 주간 거리 트렌드
            weekly_data = df.groupby([df['start_date_local'].dt.to_period('W')])['distance_km'].sum().reset_index()
            weekly_data['start_date_local'] = weekly_data['start_date_local'].astype(str)
            
            # X축 레이블을 '년도-주차' 형식으로 변경
            weekly_data['week_label'] = weekly_data['start_date_local'].apply(
                lambda x: f"{x[:4]}-W{x[5:7]}" if len(x) >= 7 else x
            )
            
            fig_weekly = px.line(
                weekly_data,
                x='week_label',
                y='distance_km',
                title="Weekly Distance Trend",
                labels={'distance_km': 'Distance (km)', 'week_label': 'Week'},
                markers=True
            )
            fig_weekly.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                height=300,
                margin=dict(l=50, r=50, t=50, b=50),
                xaxis=dict(
                    tickangle=-45,
                    tickmode='linear',
                    dtick=4  # 4주마다 표시
                )
            )
            st.plotly_chart(fig_weekly, use_container_width=True)
        
        # 페이스 트렌드
        pace_trend = df[df['pace'] > 0].copy()
        pace_trend = pace_trend.sort_values('start_date_local')
        
        fig_pace_trend = px.scatter(
            pace_trend,
            x='start_date_local',
            y='pace',
            size='distance_km',
            color='pace',
            title="Pace Improvement Over Time",
            labels={'pace': 'Pace (min/km)', 'start_date_local': 'Date'},
            color_continuous_scale='RdYlGn'  # 빠를수록(낮은 값) 빨간색, 느릴수록(높은 값) 초록색
        )
        fig_pace_trend.update_yaxes(autorange="reversed")
        fig_pace_trend.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=350,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        st.plotly_chart(fig_pace_trend, use_container_width=True)
    
    with tab2:
        st.markdown("### ⚡ Pace Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 페이스 존 분포
            if 'pace_zone' in df.columns:
                pace_zone_counts = df['pace_zone'].value_counts().reset_index()
                pace_zone_counts.columns = ['pace_zone', 'count']
                
                fig_pace_zone = px.pie(
                    pace_zone_counts,
                    values='count',
                    names='pace_zone',
                    title="Pace Zone Distribution",
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                fig_pace_zone.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_pace_zone, use_container_width=True)
        
        with col2:
            # 거리 vs 페이스
            fig_dist_pace = px.scatter(
                df[df['pace'] > 0],
                x='distance_km',
                y='pace',
                size='distance_km',
                color='pace',
                title="Distance vs Pace",
                labels={'distance_km': 'Distance (km)', 'pace': 'Pace (min/km)'},
                color_continuous_scale='RdYlGn'  # 빠를수록(낮은 값) 빨간색
            )
            fig_dist_pace.update_yaxes(autorange="reversed")
            fig_dist_pace.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_dist_pace, use_container_width=True)
        
        # 심박수 분석
        if 'average_heartrate' in df.columns and df['average_heartrate'].notna().any():
            st.markdown("### ❤️ Heart Rate Analysis")
            
            hr_data = df[df['average_heartrate'].notna()].copy()
            
            fig_hr = px.scatter(
                hr_data,
                x='pace',
                y='average_heartrate',
                size='distance_km',
                color='average_heartrate',
                title="Pace vs Heart Rate",
                labels={'pace': 'Pace (min/km)', 'average_heartrate': 'Avg Heart Rate (bpm)'},
                color_continuous_scale='Reds'  # 심박수 높을수록 빨간색
            )
            fig_hr.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_hr, use_container_width=True)
    
    with tab3:
        st.markdown("### 🏆 Personal Records & Achievements")
        
        # 개인 기록 카드
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🥇 Best Pace")
            best_pace_run = df[df['pace'] > 0].nsmallest(1, 'pace')
            if not best_pace_run.empty:
                pace_formatted = format_pace(best_pace_run.iloc[0]['pace'])
                st.metric(
                    "Fastest Run",
                    f"{pace_formatted} /km",
                    f"{best_pace_run.iloc[0]['distance_km']:.1f} km"
                )
                st.caption(f"📅 {best_pace_run.iloc[0]['start_date_local'].strftime('%Y-%m-%d')}")
        
        with col2:
            st.markdown("#### 🥈 Longest Distance")
            longest_run = df.nlargest(1, 'distance_km')
            if not longest_run.empty:
                pace_formatted = format_pace(longest_run.iloc[0]['pace'])
                st.metric(
                    "Longest Run",
                    f"{longest_run.iloc[0]['distance_km']:.2f} km",
                    f"{pace_formatted} /km"
                )
                st.caption(f"📅 {longest_run.iloc[0]['start_date_local'].strftime('%Y-%m-%d')}")
        
        with col3:
            st.markdown("#### 🥉 Most Active Month")
            monthly_totals = df.groupby(df['start_date_local'].dt.to_period('M'))['distance_km'].sum()
            best_month = monthly_totals.idxmax()
            if best_month:
                st.metric(
                    "Best Month",
                    str(best_month),
                    f"{monthly_totals[best_month]:.1f} km"
                )
        
        # 연속 러닝 기록 (스트릭)
        st.markdown("---")
        st.markdown("#### 🔥 Running Streak")
        
        dates = sorted(df['date'].unique())
        current_streak = 0
        max_streak = 0
        temp_streak = 1
        
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                temp_streak += 1
            else:
                max_streak = max(max_streak, temp_streak)
                temp_streak = 1
        
        max_streak = max(max_streak, temp_streak)
        
        # 현재 스트릭 계산
        if len(dates) > 0 and (datetime.now().date() - dates[-1]).days <= 1:
            for i in range(len(dates)-1, 0, -1):
                if (dates[i] - dates[i-1]).days == 1:
                    current_streak += 1
                else:
                    break
            current_streak += 1
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Streak", f"{current_streak} days")
        with col2:
            st.metric("Longest Streak", f"{max_streak} days")
        
        # Top 5 Runs
        st.markdown("---")
        st.markdown("#### 🌟 Top 5 Runs by Distance")
        top_runs = df.nlargest(5, 'distance_km')[['start_date_local', 'distance_km', 'pace', 'moving_time_min']].copy()
        top_runs['date'] = top_runs['start_date_local'].dt.strftime('%Y-%m-%d')
        top_runs['pace_formatted'] = top_runs['pace'].apply(format_pace)
        top_runs = top_runs[['date', 'distance_km', 'pace_formatted', 'moving_time_min']]
        top_runs.columns = ['Date', 'Distance (km)', 'Pace (/km)', 'Duration (min)']
        st.dataframe(top_runs, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown("### 🕒 Activity Patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 요일별 분석
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_data = df.groupby('weekday')['distance_km'].sum().reindex(weekday_order)
            
            fig_weekday = px.bar(
                x=weekday_data.index,
                y=weekday_data.values,
                title="Distance by Day of Week",
                labels={'x': 'Day', 'y': 'Total Distance (km)'},
                color=weekday_data.values,
                color_continuous_scale=[[0, '#1976d2'], [0.5, '#ff9800'], [1, '#d32f2f']]  # 파란색 → 주황색 → 빨간색
            )
            fig_weekday.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_weekday, use_container_width=True)
        
        with col2:
            # 시간대별 분석
            if 'time_of_day' in df.columns:
                time_data = df['time_of_day'].value_counts()
                
                fig_time = px.pie(
                    values=time_data.values,
                    names=time_data.index,
                    title="Preferred Time of Day",
                    color_discrete_sequence=px.colors.sequential.Sunset
                )
                fig_time.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white')
                )
                st.plotly_chart(fig_time, use_container_width=True)
        
        # 시간별 히트맵
        if 'hour' in df.columns and 'weekday' in df.columns:
            st.markdown("#### 📊 Activity Heatmap by Hour and Day")
            
            hourly_weekly = df.groupby(['weekday', 'hour']).size().reset_index(name='count')
            hourly_weekly_pivot = hourly_weekly.pivot(index='weekday', columns='hour', values='count').fillna(0)
            hourly_weekly_pivot = hourly_weekly_pivot.reindex(weekday_order)
            
            fig_heatmap = px.imshow(
                hourly_weekly_pivot,
                labels=dict(x="Hour of Day", y="Day of Week", color="Runs"),
                x=hourly_weekly_pivot.columns,
                y=hourly_weekly_pivot.index,
                color_continuous_scale=[[0, '#0d47a1'], [0.5, '#ffa726'], [1, '#d32f2f']]  # 파란색 → 주황색 → 빨간색
            )
            fig_heatmap.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white')
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    with tab5:
        st.markdown("### 📝 Raw Data")
        
        # 검색 및 필터
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 Search by name", "")
        with col2:
            sort_by = st.selectbox("Sort by", ["date", "distance", "pace"], index=0)
        
        # 데이터 표시
        display_df = df.copy()
        if search:
            display_df = display_df[display_df['name'].str.contains(search, case=False, na=False)]
        
        if sort_by == "date":
            display_df = display_df.sort_values('start_date_local', ascending=False)
        elif sort_by == "distance":
            display_df = display_df.sort_values('distance_km', ascending=False)
        elif sort_by == "pace":
            display_df = display_df[display_df['pace'] > 0].sort_values('pace', ascending=True)
        
        # 컬럼 선택
        display_cols = ['start_date_local', 'name', 'distance_km', 'pace', 'moving_time_min']
        if 'average_heartrate' in display_df.columns:
            display_cols.append('average_heartrate')
        
        display_df_final = display_df[display_cols].copy()
        display_df_final['pace_formatted'] = display_df_final['pace'].apply(format_pace)
        
        # 컬럼 순서 재정렬
        final_cols = ['start_date_local', 'name', 'distance_km', 'pace_formatted', 'moving_time_min']
        if 'average_heartrate' in display_df_final.columns:
            final_cols.append('average_heartrate')
        
        display_df_final = display_df_final[final_cols]
        display_df_final.columns = ['Date', 'Name', 'Distance (km)', 'Pace (/km)', 'Duration (min)'] + (['Avg HR'] if 'average_heartrate' in display_df.columns else [])
        
        st.dataframe(display_df_final, use_container_width=True, height=600)
        
        # CSV 다운로드
        csv = display_df_final.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"running_data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: rgba(255,255,255,0.6);'>
        <p>💪 Keep Running, Keep Improving!</p>
        <p style='font-size: 0.8rem;'>Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M')), unsafe_allow_html=True)

if __name__ == "__main__":
    main()