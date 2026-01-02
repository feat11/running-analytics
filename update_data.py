#!/usr/bin/env python3
"""
GitHub Actions에서 실행할 Strava 데이터 업데이트 스크립트
"""
import os
import json
import requests
import pandas as pd
from datetime import datetime

def get_access_token(client_id, client_secret, refresh_token):
    """Refresh Token을 이용해 새로운 Access Token을 발급받습니다."""
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'f': 'json'
    }
    auth_url = "https://www.strava.com/oauth/token"
    res = requests.post(auth_url, data=payload, verify=False)
    res.raise_for_status()
    access_token = res.json()['access_token']
    return access_token

def fetch_strava_data(access_token):
    """Strava API에서 모든 데이터 가져오기"""
    headers = {'Authorization': f"Bearer {access_token}"}
    
    all_activities = []
    page = 1
    per_page = 200
    
    # 모든 데이터를 가져올 때까지 반복
    while True:
        param = {'per_page': per_page, 'page': page}
        dataset_url = "https://www.strava.com/api/v3/athlete/activities"
        
        print(f"📄 페이지 {page} 가져오는 중...")
        res = requests.get(dataset_url, headers=headers, params=param, verify=False)
        data = res.json()
        
        if not data:
            break
        
        all_activities.extend(data)
        print(f"   ✓ {len(data)}개 활동 추가 (누적: {len(all_activities)}개)")
        
        if len(data) < per_page:
            break
        
        page += 1
        
        # 안전장치
        if page > 100:
            print(f"⚠️ 100페이지 제한 도달 (총 {len(all_activities)}개)")
            break
    
    return all_activities

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
    
    # date 컬럼 생성
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

def main():
    print("🏃 Strava 데이터 업데이트 시작...")
    
    # 환경변수에서 credentials 가져오기
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    refresh_token = os.environ.get('STRAVA_REFRESH_TOKEN')
    
    if not all([client_id, client_secret, refresh_token]):
        print("❌ Strava credentials가 설정되지 않았습니다.")
        exit(1)
    
    try:
        # Access Token 발급
        print("🔑 Access Token 발급 중...")
        access_token = get_access_token(client_id, client_secret, refresh_token)
        
        # 데이터 가져오기
        print("📥 Strava에서 데이터 가져오는 중...")
        raw_data = fetch_strava_data(access_token)
        print(f"📊 총 {len(raw_data)}개 활동 가져옴")
        
        # 데이터 처리
        print("⚙️ 데이터 처리 중...")
        df = process_data(raw_data)
        
        # CSV 저장
        csv_file = 'running_data.csv'
        df.to_csv(csv_file, index=False)
        print(f"💾 {csv_file} 저장 완료")
        
        # 설정 파일 업데이트
        config_file = 'app_config.json'
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        config['last_update'] = datetime.now().isoformat()
        
        with open(config_file, 'w') as f:
            json.dump(config, f)
        print(f"⚙️ {config_file} 업데이트 완료")
        
        print("✅ 모든 업데이트 완료!")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        exit(1)

if __name__ == "__main__":
    main()
