import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import os
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 브랜딩
# ==========================================
st.set_page_config(page_title="T-Bridge Election Dashboard", page_icon="🌉", layout="wide")

BRAND_INDIGO = "#1A237E"
GRAY_LIGHT = "#E0E0E0" 
HIGHLIGHT_COLOR = "#FFD700" # 하이라이트용 금색

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

# 3. 2025 대선 데이터 (비교용)
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
def draw_hexagon_map(df, title_text, highlight_regions=None, mode="normal", active_regions=None):
    if highlight_regions is None: highlight_regions = []
    if active_regions is None: active_regions = []
    
    fig = go.Figure()
    for region, (col, row) in HEX_MAP.items():
        cx, cy, x_coords, y_coords = get_hexagon_path(col, row)
        
        if mode == "status":
            is_active = region in active_regions
            color = BRAND_INDIGO if is_active else GRAY_LIGHT
            text_color = "white" if is_active else "#9E9E9E"
            hover_text = f"<b>{region}</b><br>{'데이터 분석 가능' if is_active else '데이터 업데이트 대기 중'}"
        else:
            color, text_color = '#F0F2F6', BRAND_INDIGO
            hover_text = f"<b>{region}</b><br>데이터 없음"
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
                    hover_text = f"<b>[{region}]</b><br>{'<br>'.join(cand_list)}<br>------------------<br><b>격차: {gap:.1f}%p</b>"

        # 하이라이트(금색 테두리) 처리
        is_highlight = region in highlight_regions
        line_color, line_width = (HIGHLIGHT_COLOR, 6) if is_highlight else ('white', 2)

        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, fill='toself', fillcolor=color, mode='lines', line=dict(color=line_color, width=line_width), name=region, text=hover_text, hoverinfo='text'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=text_color, size=15, family="Noto Sans KR"), hoverinfo='skip'))

    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", font=dict(size=22, color=BRAND_INDIGO), x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=550, plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
    return fig

# ==========================================
# 6. 데이터 로드 및 사이드바
# ==========================================
with st.sidebar:
    st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드 선택", ["현행 판세 분석", "시군구 판세 분석", "2025 대선 비교 분석", "🎛️ 가상 시나리오 시뮬레이터"])
    st.divider()
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("⚠️ **법적 고지**")
    st.caption("인용된 조사의 자세한 내용은 중앙선거여론조사심의위원회 홈페이지를 참조하시기 바랍니다.")

@st.cache_data(ttl=60)
def load_data_from_gsheets():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read() 
        if df is None or df.empty: return None, None
        df.columns = ['조사일자', '지역', '기초지역', '후보', '지지율', '정당']
        df['지역'] = df['지역'].astype(str).str.strip().replace(NAME_MAPPING)
        df['기초지역'] = df['기초지역'].fillna('전체').astype(str).str.strip().replace('', '전체')
        df['지지율'] = pd.to_numeric(df['지지율'].astype(str).str.replace('%',''), errors='coerce').fillna(0)
        df_all = df.sort_values(by=['조사일자', '지역', '기초지역'])
        df_latest = df_all.drop_duplicates(subset=['지역', '기초지역', '후보'], keep='last').copy()
        return df_all, df_latest
    except Exception as e:
        st.error(f"데이터 연동 에러: {e}")
        return None, None

df_current_all, df_current_latest = load_data_from_gsheets()
is_valid = df_current_latest is not None and not df_current_latest.empty

st.markdown("""<div class='main-header'><h1>T-Bridge 헥사곤 판세 분석 솔루션 (Live)</h1></div>""", unsafe_allow_html=True)

# ------------------------------------------
# [수정된 모드] 시군구 판세 분석
# ------------------------------------------
if app_mode == "시군구 판세 분석":
    st.subheader("📍 기초자치단체별 상세 판세 분석")
    
    if is_valid:
        # 데이터가 있는 지역 리스트
        active_regions = df_current_latest[df_current_latest['기초지역'] != '전체']['지역'].unique().tolist()
        
        # 세션 상태 초기화
        if 'selected_region' not in st.session_state:
            st.session_state['selected_region'] = '전남' if '전남' in active_regions else '서울'

        # --- [변경] 버튼을 먼저 배치하여 선택값을 먼저 받습니다 ---
        st.write("분석할 지역을 클릭하세요:")
        all_regions_list = sorted(HEX_MAP.keys())
        cols = st.columns(6)
        for i, reg in enumerate(all_regions_list):
            with cols[i % 6]:
                prefix = "🔵 " if reg in active_regions else "⚪ "
                if st.button(f"{prefix}{reg}", key=f"btn_{reg}", use_container_width=True,
                             type="primary" if st.session_state['selected_region'] == reg else "secondary"):
                    st.session_state['selected_region'] = reg
                    st.rerun() # 클릭 즉시 화면 갱신
        
        st.divider()
        
        # --- [변경] 지도를 버튼 아래에 배치하고 현재 선택된 지역을 하이라이트합니다 ---
        sel_reg = st.session_state['selected_region']
        st.plotly_chart(draw_hexagon_map(None, f"🔍 {sel_reg} 분석 중 (금색 테두리)", 
                                         mode="status", 
                                         active_regions=active_regions,
                                         highlight_regions=[sel_reg]), use_container_width=True)

        # 상세 결과 출력
        sub_df = df_current_latest[(df_current_latest['지역'] == sel_reg) & (df_current_latest['기초지역'] != '전체')]
        
        if not sub_df.empty:
            st.markdown(f"### 🚩 {sel_reg} 상세 분석 결과")
            cmap = {'더불어민주당': '#004EA2', '국민의힘': '#E61E2B', '민주당': '#004EA2', '국힘': '#E61E2B'}
            fig_sub = px.bar(sub_df, x='기초지역', y='지지율', color='정당', text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"),
                             title=f"[{sel_reg}] 기초자치단체별 지지율", barmode='group', color_discrete_map=cmap)
            st.plotly_chart(fig_sub, use_container_width=True)
        else:
            st.warning(f"🔔 {sel_reg} 지역의 상세 데이터는 현재 업데이트 대기 중입니다.")

# (나머지 모드들은 기존과 동일)
elif app_mode == "현행 판세 분석":
    df_prov = df_current_latest[df_current_latest['기초지역'] == '전체'] if is_valid else None
    st.plotly_chart(draw_hexagon_map(df_prov, "현행 전국 판세 실시간 데이터"), use_container_width=True)

elif app_mode == "2025 대선 비교 분석":
    col1, col2 = st.columns(2)
    df_prov = df_current_latest[df_current_latest['기초지역'] == '전체'] if is_valid else None
    with col1: st.plotly_chart(draw_hexagon_map(df_2025, "🗳️ 2025년 대선 결과"), use_container_width=True)
    with col2: st.plotly_chart(draw_hexagon_map(df_prov, "📈 현재 판세 실시간 데이터"), use_container_width=True)

elif app_mode == "🎛️ 가상 시나리오 시뮬레이터":
    if not is_valid: st.warning("데이터를 불러오는 중입니다...")
    else:
        df_prov = df_current_latest[df_current_latest['기초지역'] == '전체'].copy()
        col_s1, col_s2 = st.columns(2)
        with col_s1: adj_minju = st.slider("🔵 민주당 조정", -10.0, 10.0, 0.0, 0.5)
        with col_s2: adj_gukhim = st.slider("🔴 국힘 조정", -10.0, 10.0, 0.0, 0.5)
        df_sim = df_prov.reset_index(drop=True)
        for idx, row in df_sim.iterrows():
            p = str(row['정당'])
            if '민주' in p: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_minju)
            elif '국힘' in p or '국민의힘' in p: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_gukhim)
        st.plotly_chart(draw_hexagon_map(df_sim, "시뮬레이션 결과"), use_container_width=True)
