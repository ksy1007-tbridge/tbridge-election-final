import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 브랜딩 색상 정의
# ==========================================
st.set_page_config(page_title="T-Bridge Election Dashboard", page_icon="🌉", layout="wide")

# 정당 상징색 (절대 변하지 않는 기준색)
COLOR_MINJU = "#004EA2"  # 블루
COLOR_GUKHIM = "#E61E2B" # 레드
COLOR_OTHER = "#808080"  # 그레이

BRAND_INDIGO = "#1A237E" 
GRAY_LIGHT = "#F5F5F5"   
SEL_FILL = "#E3F2FD"     
SEL_LINE = "#1565C0"     

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    button[kind="primary"] {{
        background-color: {BRAND_INDIGO} !important;
        border-color: {BRAND_INDIGO} !important;
        color: white !important;
        font-weight: bold !important;
    }}
    .main-header {{
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 12px solid {BRAND_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;
    }}
    .main-header h1 {{ color: {BRAND_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

# 2. 고정 매핑 데이터
HEX_MAP = {'경기': (1, 6), '강원': (2, 6), '인천': (0, 5), '서울': (1, 5), '충북': (2, 5), '대전': (1, 4), '세종': (2, 4), '경북': (3, 4), '전북': (0, 3), '충남': (1, 3), '대구': (2, 3), '울산': (3, 3), '전남': (0, 2), '광주': (1, 2), '경남': (2, 2), '부산': (3, 2), '제주': (0, 1)}
NAME_MAPPING = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '세종시': '세종', '경기도': '경기', '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}

# 3. 도움 함수: 데이터 기반 동적 색상 지도 생성
def get_dynamic_color_map(df):
    """후보별로 정당을 확인하여 블루/레드 색상을 매핑한 딕셔너리 반환"""
    color_map = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            cand = row['후보']
            party = str(row['정당'])
            if '민주' in party: color_map[cand] = COLOR_MINJU
            elif '국힘' in party or '국민의힘' in party: color_map[cand] = COLOR_GUKHIM
            else: color_map[cand] = COLOR_OTHER
    return color_map

# 4. 지도 렌더링 엔진
def get_hexagon_path(col, row, radius=1):
    cx, cy = col * math.sqrt(3) * radius + (row % 2 == 1) * (math.sqrt(3)/2) * radius, row * 1.5 * radius
    x, y = [], []
    for i in range(6):
        a = math.pi / 6 + i * math.pi / 3
        x.append(cx + radius * math.cos(a)); y.append(cy + radius * math.sin(a))
    return cx, cy, x + [x[0]], y + [y[0]]

def final_visual_map_engine(df, title_text, highlight_region="", mode="normal", active_regions=None):
    if active_regions is None: active_regions = []
    fig = go.Figure()
    for region, (col, row) in HEX_MAP.items():
        cx, cy, x_coords, y_coords = get_hexagon_path(col, row)
        f_color, t_color, l_color, l_width = '#F8F9FA', BRAND_INDIGO, "#DEE2E6", 1.2
        h_text = f"<b>{region}</b>"

        if region == highlight_region:
            f_color, l_color, l_width = SEL_FILL, SEL_LINE, 5
            t_color, h_text = BRAND_INDIGO, f"<b>{region} (선택됨)</b>"
        elif mode == "status":
            is_active = region in active_regions
            f_color, t_color, l_color = (BRAND_INDIGO, "white", "white") if is_active else (GRAY_LIGHT, "#ADB5BD", "white")
        else:
            if df is not None and not df.empty:
                r_all = df[df['지역'] == region].sort_values(by='지지율', ascending=False)
                if not r_all.empty:
                    win = r_all.iloc[0]
                    gap = win.get('지지율', 0) - r_all.iloc[1].get('지지율', 0) if len(r_all) > 1 else 0
                    alpha = max(0.2, min(gap / 25.0, 1.0))
                    p_str = str(win.get('정당', ''))
                    if '민주' in p_str: f_color = f'rgba(0, 78, 162, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    elif '국힘' in p_str or '국민의힘' in p_str: f_color = f'rgba(230, 30, 43, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    else: f_color = f'rgba(128, 128, 128, {alpha})'; t_color = 'white'
                    h_text += f"<br>1위: {win['후보']} ({gap:.1f}%p 차)"

        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, fill='toself', fillcolor=f_color, mode='lines', line=dict(color=l_color, width=l_width), name=region, text=h_text, hoverinfo='text'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=t_color, size=15, family="Noto Sans KR"), hoverinfo='skip'))

    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", font=dict(size=22, color=BRAND_INDIGO), x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=550, plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
    return fig

# 5. 데이터 로드
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read() 
        if df is None or df.empty: return None, None, None
        df.columns = ['조사일자', '지역', '기초지역', '후보', '지지율', '정당']
        df['지역'] = df['지역'].astype(str).str.strip().replace(NAME_MAPPING)
        df['기초지역'] = df['기초지역'].fillna('전체').astype(str).str.strip()
        df['지지율'] = pd.to_numeric(df['지지율'].astype(str).str.replace('%',''), errors='coerce').fillna(0)
        df['조사일자'] = pd.to_datetime(df['조사일자']).dt.date
        df_latest = df.sort_values('조사일자').drop_duplicates(subset=['지역', '기초지역', '후보'], keep='last')
        df_prov_latest = df_latest[df_latest['기초지역'] == '전체']
        return df, df_latest, df_prov_latest
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return None, None, None

df_all, df_latest, df_prov = load_data()

# 6. 사이드바
with st.sidebar:
    st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드 선택", ["현행 판세 분석", "시군구 판세 분석", "2025 대선 비교 분석", "🎛️ 가상 시나리오 시뮬레이터"])
    st.divider()
    if st.button("🧹 전체 캐시 강제 삭제", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
        st.rerun()

st.markdown("""<div class='main-header'><h1>T-Bridge 헥사곤 판세 분석 솔루션 (Live)</h1></div>""", unsafe_allow_html=True)

if 'selected_region' not in st.session_state:
    st.session_state['selected_region'] = '서울'

# 7. 모드별 상세 구현
if app_mode == "현행 판세 분석":
    st.subheader("📈 실시간 전국 광역 시·도별 판세")
    cols = st.columns(6); all_regs = sorted(HEX_MAP.keys())
    for i, reg in enumerate(all_regs):
        with cols[i % 6]:
            if st.button(f"{reg}", key=f"p_btn_{reg}", use_container_width=True,
                         type="primary" if st.session_state['selected_region'] == reg else "secondary"):
                st.session_state['selected_region'] = reg
                st.rerun()

    sel_reg = st.session_state['selected_region']
    st.plotly_chart(final_visual_map_engine(df_prov, "전국 광역 지지율 현황", highlight_region=sel_reg), use_container_width=True)

    st.divider()
    st.markdown(f"### 🚩 {sel_reg} 광역 상세 분석")
    
    reg_hist = df_all[(df_all['지역'] == sel_reg) & (df_all['기초지역'] == '전체')].sort_values('조사일자')
    # 동적 색상 매핑 생성
    dynamic_colors = get_dynamic_color_map(reg_hist)

    if len(reg_hist['조사일자'].unique()) > 1:
        fig_trend = px.line(reg_hist, x='조사일자', y='지지율', color='후보', markers=True,
                            title=f"[{sel_reg}] 지지율 추세 변화", color_discrete_map=dynamic_colors)
        st.plotly_chart(fig_trend, use_container_width=True)
    
    reg_latest = df_prov[df_prov['지역'] == sel_reg]
    if not reg_latest.empty:
        fig_bar = px.bar(reg_latest, x='후보', y='지지율', color='후보', text=reg_latest['지지율'].apply(lambda x: f"{x:.1f}%"),
                         title=f"[{sel_reg}] 최신 지지율 현황", color_discrete_map=dynamic_colors)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.dataframe(reg_latest[['후보', '정당', '지지율']].sort_values('지지율', ascending=False), hide_index=True, use_container_width=True)

elif app_mode == "시군구 판세 분석":
    st.subheader("📍 기초자치단체별 상세 판세 분석")
    if df_latest is not None:
        active_regions = df_latest[df_latest['기초지역'] != '전체']['지역'].unique().tolist()
        cols = st.columns(6); all_regs = sorted(HEX_MAP.keys())
        for i, reg in enumerate(all_regs):
            with cols[i % 6]:
                prefix = "🔵 " if reg in active_regions else "⚪ "
                if st.button(f"{prefix}{reg}", key=f"m_btn_{reg}", use_container_width=True,
                             type="primary" if st.session_state['selected_region'] == reg else "secondary"):
                    st.session_state['selected_region'] = reg
                    st.rerun() 

        sel_reg = st.session_state['selected_region']
        st.plotly_chart(final_visual_map_engine(None, f"🔍 {sel_reg} 시군구 분석", mode="status", active_regions=active_regions, highlight_region=sel_reg), use_container_width=True)

        st.divider()
        reg_hist = df_all[(df_all['지역'] == sel_reg) & (df_all['기초지역'] == '전체')].sort_values('조사일자')
        dynamic_colors = get_dynamic_color_map(reg_hist)

        if len(reg_hist['조사일자'].unique()) > 1:
            st.markdown(f"### 📈 {sel_reg} 광역 지지율 추세 변화")
            fig_trend = px.line(reg_hist, x='조사일자', y='지지율', color='후보', markers=True, color_discrete_map=dynamic_colors)
            st.plotly_chart(fig_trend, use_container_width=True)

        sub_df = df_latest[(df_latest['지역'] == sel_reg) & (df_latest['기초지역'] != '전체')]
        if not sub_df.empty:
            st.markdown(f"### 🚩 {sel_reg} 시군구별 상세 분석")
            # 시군구 바 차트도 후보별로 색상 매핑
            dynamic_sub_colors = get_dynamic_color_map(sub_df)
            fig_sub = px.bar(sub_df, x='기초지역', y='지지율', color='후보', text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"), barmode='group', color_discrete_map=dynamic_sub_colors)
            st.plotly_chart(fig_sub, use_container_width=True)
            st.dataframe(sub_df[['기초지역', '후보', '정당', '지지율']].sort_values(['기초지역', '지지율'], ascending=[True, False]), hide_index=True, use_container_width=True)

# 2025 대선 비교 및 시뮬레이터 로직 동일...
