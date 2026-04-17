import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import os
import io
from streamlit_gsheets import GSheetsConnection  # 구글 시트 연결용 추가

# ==========================================
# 1. 페이지 설정 및 브랜딩
# ==========================================
st.set_page_config(page_title="T-Bridge Election Dashboard", page_icon="🌉", layout="wide")

BRAND_INDIGO = "#1A237E"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .main-header {{
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 12px solid {BRAND_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;
    }}
    .main-header h1 {{ color: {BRAND_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

# 2. 17개 시도 좌표 및 맵핑
HEX_MAP = {'경기': (1, 6), '강원': (2, 6), '인천': (0, 5), '서울': (1, 5), '충북': (2, 5), '대전': (1, 4), '세종': (2, 4), '경북': (3, 4), '전북': (0, 3), '충남': (1, 3), '대구': (2, 3), '울산': (3, 3), '전남': (0, 2), '광주': (1, 2), '경남': (2, 2), '부산': (3, 2), '제주': (0, 1)}
NAME_MAPPING = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '세종시': '세종', '경기도': '경기', '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}

# 3. 2025 대선 데이터 내장 (비교용)
past_data_list = [['서울', '이재명', '민주당', 52.0], ['서울', '김문수', '국힘', 45.0], ['경기', '이재명', '민주당', 54.0], ['경기', '김문수', '국힘', 43.0], ['인천', '이재명', '민주당', 53.0], ['인천', '김문수', '국힘', 42.0], ['강원', '김문수', '국힘', 55.0], ['강원', '이재명', '민주당', 40.0], ['충북', '김문수', '국힘', 49.0], ['충북', '이재명', '민주당', 47.0], ['충남', '이재명', '민주당', 50.0], ['충남', '김문수', '국힘', 46.0], ['대전', '이재명', '민주당', 51.0], ['대전', '김문수', '국힘', 45.0], ['세종', '이재명', '민주당', 53.0], ['세종', '김문수', '국힘', 41.0], ['전북', '이재명', '민주당', 85.0], ['전북', '김문수', '국힘', 10.0], ['광주', '이재명', '민주당', 88.0], ['광주', '김문수', '국힘', 8.0], ['전남', '이재명', '민주당', 86.0], ['전남', '김문수', '국힘', 9.0], ['경북', '김문수', '국힘', 75.0], ['경북', '이재명', '민주당', 20.0], ['대구', '김문수', '국힘', 72.0], ['대구', '이재명', '민주당', 23.0], ['경남', '김문수', '국힘', 58.0], ['경남', '이재명', '민주당', 38.0], ['부산', '김문수', '국힘', 56.0], ['부산', '이재명', '민주당', 40.0], ['울산', '김문수', '국힘', 53.0], ['울산', '이재명', '민주당', 43.0], ['제주', '이재명', '민주당', 55.0], ['제주', '김문수', '국힘', 41.0]]
df_2025 = pd.DataFrame(past_data_list, columns=['지역', '후보', '정당', '지지율'])

# 4. 육각형 계산 함수
def get_hexagon_path(col, row, radius=1):
    cx, cy = col * math.sqrt(3) * radius + (row % 2 == 1) * (math.sqrt(3)/2) * radius, row * 1.5 * radius
    x, y = [], []
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        x.append(cx + radius * math.cos(a)); y.append(cy + radius * math.sin(a))
    return cx, cy, x + [x[0]], y + [y[0]]

# 5. 지도 렌더링 함수
def draw_hexagon_map(df, title_text, highlight_regions=None):
    if highlight_regions is None: highlight_regions = []
    fig = go.Figure()
    for region, (col, row) in HEX_MAP.items():
        cx, cy, x_coords, y_coords = get_hexagon_path(col, row)
        color, text_color = '#F0F2F6', BRAND_INDIGO
        hover_text = f"<b>{region}</b><br>데이터 없음"
        is_highlight = region in highlight_regions
        line_color, line_width = ('#FFD700', 5) if is_highlight else ('white', 2)
        
        if df is not None and '지역' in df.columns:
            region_all = df[df['지역'] == region].sort_values(by='지지율', ascending=False)
            if not region_all.empty:
                win = region_all.iloc[0]
                party_orig = str(win.get('정당', '')).strip()
                gap = win.get('지지율', 0) - region_all.iloc[1].get('지지율', 0) if len(region_all) > 1 else 0
                
                if '민주' in party_orig:
                    alpha = max(0.3, min(gap / 25.0, 1.0))
                    color, text_color = f'rgba(0, 78, 162, {alpha})', 'white' if alpha >= 0.5 else BRAND_INDIGO
                elif '국힘' in party_orig or '국민의힘' in party_orig: color, text_color = '#E61E2B', 'white'
                else: color, text_color = '#808080', 'white'
                
                cand_list = [f"• {r['후보']}({str(r['정당']).split('(')[0].strip()}): {r['지지율']:.1f}%" for _, r in region_all.iterrows()]
                hover_text = f"{'🔥 <b>[역전!] ' + region + '</b>' if is_highlight else '<b>[' + region + ']</b>'}<br>{'<br>'.join(cand_list)}<br>------------------<br><b>격차: {gap:.1f}%p</b>"

        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, fill='toself', fillcolor=color, mode='lines', line=dict(color=line_color, width=line_width), name=region, text=hover_text, hoverinfo='text'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=text_color, size=15, family="Noto Sans KR"), hoverinfo='skip'))

    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", font=dict(size=22, color=BRAND_INDIGO), x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=600, plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
    return fig

# ==========================================
# 6. 메인 UI 및 데이터 로드 (구글 시트 연동 버전)
# ==========================================
with st.sidebar:
    if os.path.exists("logo.png"): st.image("logo.png", use_container_width=True)
    else: st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:gray; font-size:14px; margin-bottom:20px;'>Live Analysis Solution V6.0</div>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드 선택", ["현행 판세 분석", "2025 대선 비교 분석", "🎛️ 가상 시나리오 시뮬레이터"])
    st.divider()
    st.info("✅ 데이터가 구글 시트와 실시간 연동 중입니다.")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

@st.cache_data(ttl=60) # 캐시를 1분으로 줄여서 즉각 반영되게 합니다.
def load_data_from_gsheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # [수정 핵심] worksheet 옵션을 아예 빼버립니다. 
        # 그러면 자동으로 첫 번째 탭(Sheet1)을 읽어옵니다.
        df = conn.read() 
        
        if df is None or df.empty: return None, None
        
        # 컬럼명 강제 지정 (시트의 1행이 영어든 한글이든 상관없이 덮어씌움)
        # 데이터가 5개 열(A~E)인지 꼭 확인하세요!
        df.columns = ['조사일자', '지역', '후보', '지지율', '정당']
        
        df['지역'] = df['지역'].astype(str).str.strip().replace(NAME_MAPPING)
        df['지지율'] = pd.to_numeric(df['지지율'], errors='coerce').fillna(0)
        
        df_all = df.sort_values(by=['지역', '후보', '조사일자'])
        df_latest = df_all.drop_duplicates(subset=['지역', '후보'], keep='last').copy()
        return df_all, df_latest
    except Exception as e:
        # 에러가 나면 화면에 아주 상세하게 뿌려줍니다.
        st.error(f"상세 에러 내용: {e}")
        return None, None
        
# 데이터 로드 실행
df_current_all, df_current_latest = load_data_from_gsheets()
is_valid = df_current_latest is not None and not df_current_latest.empty and '지역' in df_current_latest.columns

st.markdown("""<div class='main-header'><h1>T-Bridge 헥사곤 판세 분석 솔루션 (Live)</h1></div>""", unsafe_allow_html=True)

df_sim = None 

if app_mode == "현행 판세 분석":
    st.plotly_chart(draw_hexagon_map(df_current_latest if is_valid else None, "현행 전국 판세 실시간 데이터"), use_container_width=True)

elif app_mode == "2025 대선 비교 분석":
    col1, col2 = st.columns(2)
    with col1: st.plotly_chart(draw_hexagon_map(df_2025, "🗳️ 2025년 대선 결과"), use_container_width=True)
    with col2: st.plotly_chart(draw_hexagon_map(df_current_latest if is_valid else None, "📈 구글 시트 실시간 데이터"), use_container_width=True)

elif app_mode == "🎛️ 가상 시나리오 시뮬레이터":
    if not is_valid: st.warning("데이터를 불러오는 중입니다...")
    else:
        col_s1, col_s2 = st.columns(2)
        with col_s1: adj_minju = st.slider("🔵 민주당 지지율 일괄 조정 (%p)", -10.0, 10.0, 0.0, 0.5)
        with col_s2: adj_gukhim = st.slider("🔴 국민의힘 지지율 일괄 조정 (%p)", -10.0, 10.0, 0.0, 0.5)

        df_sim = df_current_latest.copy().reset_index(drop=True)
        for idx, row in df_sim.iterrows():
            party = str(row.get('정당', ''))
            if '민주' in party: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_minju)
            elif '국힘' in party or '국민의힘' in party: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_gukhim)

        flipped_regions = []
        for r in HEX_MAP.keys():
            orig_data = df_current_latest[df_current_latest['지역'] == r].sort_values(by='지지율', ascending=False)
            sim_data = df_sim[df_sim['지역'] == r].sort_values(by='지지율', ascending=False)
            if not orig_data.empty and not sim_data.empty:
                if orig_data.iloc[0]['후보'] != sim_data.iloc[0]['후보']: flipped_regions.append(r)

        st.plotly_chart(draw_hexagon_map(df_sim, "가상 시나리오 반영 후 판세", highlight_regions=flipped_regions), use_container_width=True)

# ==========================================
# 7. 하단 상세 분석
# ==========================================
if is_valid:
    st.divider()
    target_df = df_sim if (app_mode == "🎛️ 가상 시나리오 시뮬레이터" and df_sim is not None) else df_current_latest
    
    if target_df is not None and '지역' in target_df.columns:
        valid_regions = [r for r in HEX_MAP.keys() if r in target_df['지역'].unique()]
        
        if valid_regions:
            selected = st.selectbox("🎯 상세 정보를 확인할 지역을 선택하세요", valid_regions)
            
            rd_latest = target_df[target_df['지역'] == selected].copy()
            rd_latest = rd_latest.sort_values(by='지지율', ascending=False).reset_index(drop=True)
            if not rd_latest.empty:
                rd_latest['텍스트표시'] = rd_latest['지지율'].apply(lambda x: f"{float(x):.1f}%")
            
            cmap = {p: ('#004EA2' if '민주' in str(p) else '#E61E2B' if '국힘' in str(p) else '#808080') for p in rd_latest.get('정당', pd.Series()).unique()}

            tab1, tab2 = st.tabs(["📊 지지율 요약", "📈 시계열 지지율 추이"])
            with tab1:
                c1, c2, c3 = st.columns([2.5, 1, 1.5])
                with c1: 
                    st.plotly_chart(px.bar(rd_latest, x='후보', y='지지율', color='정당', text='텍스트표시', color_discrete_map=cmap, title=f"[{selected}] 지지율 현황"), use_container_width=True)
                with c2:
                    st.write("### 판세 요약")
                    if len(rd_latest) > 1:
                        st.metric(label="1-2위 격차", value=f"{rd_latest.iloc[0]['지지율'] - rd_latest.iloc[1]['지지율']:.1f}%p")
                        st.write(f"🏆 **1위:** {rd_latest.iloc[0]['후보']}")
                        st.write(f"🥈 **2위:** {rd_latest.iloc[1]['후보']}")
                    elif len(rd_latest) == 1:
                        st.metric(label="1-2위 격차", value="단독 출마")
                        st.write(f"🏆 **1위:** {rd_latest.iloc[0]['후보']}")
                with c3: 
                    display_df = rd_latest[['후보', '정당', '지지율']].copy()
                    display_df['지지율'] = display_df['지지율'].round(1)
                    st.dataframe(display_df, hide_index=True, use_container_width=True)
            
            with tab2:
                if app_mode == "🎛️ 가상 시나리오 시뮬레이터":
                    st.info("💡 시뮬레이터 모드에서는 시계열 그래프가 비활성화됩니다.")
                else:
                    st.write(f"### {selected} 후보별 지지율 변화 추이")
                    rd_all = df_current_all[df_current_all['지역'] == selected].copy().sort_values(by=['조사일자', '지지율']).reset_index(drop=True)
                    if len(rd_all['조사일자'].unique()) > 1:
                        st.plotly_chart(px.line(rd_all, x='조사일자', y='지지율', color='정당', markers=True, line_shape='spline', color_discrete_map=cmap), use_container_width=True)
                    else:
                        st.info("💡 구글 시트에 날짜가 다른 데이터를 쌓으면 추이 그래프가 그려집니다.")
