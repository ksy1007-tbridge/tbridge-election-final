import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import os
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 브랜딩 (CSS 강화)
# ==========================================
st.set_page_config(page_title="T-Bridge Election Dashboard", page_icon="🌉", layout="wide")

BRAND_INDIGO = "#1A237E" 
GRAY_LIGHT = "#F5F5F5"   
SEL_FILL = "#E3F2FD"     
SEL_LINE = "#1565C0"     

# [V6.9] CSS: 빨간색 버튼 문제를 완전히 뿌리 뽑는 강경 대응
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    
    /* 선택된 Primary 버튼의 빨간색을 브랜드 남색으로 강제 변경 */
    button[kind="primary"] {{
        background-color: {BRAND_INDIGO} !important;
        border-color: {BRAND_INDIGO} !important;
        color: white !important;
        box-shadow: none !important;
    }}
    button[kind="primary"]:focus {{
        box-shadow: 0 0 0 2px {SEL_FILL} !important;
    }}
    
    .main-header {{
        background-color: white; padding: 20px; border-radius: 10px;
        border-left: 12px solid {BRAND_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;
    }}
    .main-header h1 {{ color: {BRAND_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

# 2. 맵 데이터 설정
HEX_MAP = {'경기': (1, 6), '강원': (2, 6), '인천': (0, 5), '서울': (1, 5), '충북': (2, 5), '대전': (1, 4), '세종': (2, 4), '경북': (3, 4), '전북': (0, 3), '충남': (1, 3), '대구': (2, 3), '울산': (3, 3), '전남': (0, 2), '광주': (1, 2), '경남': (2, 2), '부산': (3, 2), '제주': (0, 1)}
NAME_MAPPING = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '세종시': '세종', '경기도': '경기', '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}

# 3. 육각형 엔진
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
            f_color, l_color, l_width = SEL_FILL, SEL_LINE, 4
            t_color, h_text = BRAND_INDIGO, f"<b>{region} (분석 중)</b>"
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
                    if '민주' in str(win.get('정당', '')): f_color = f'rgba(0, 78, 162, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    elif '국힘' in str(win.get('정당', '')): f_color = f'rgba(230, 30, 43, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    else: f_color = f'rgba(128, 128, 128, {alpha})'; t_color = 'white'

        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, fill='toself', fillcolor=f_color, mode='lines', line=dict(color=l_color, width=l_width), name=region, text=h_text, hoverinfo='text'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=t_color, size=15, family="Noto Sans KR"), hoverinfo='skip'))

    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", font=dict(size=22, color=BRAND_INDIGO), x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=550, plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
    return fig

# ==========================================
# 4. 사이드바 및 기능 버튼
# ==========================================
with st.sidebar:
    st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드 선택", ["현행 판세 분석", "시군구 판세 분석", "2025 대선 비교 분석", "🎛️ 가상 시나리오 시뮬레이터"])
    
    st.divider()
    # [V6.9] 사용자님이 못 찾으신 [Clear Cache]를 버튼으로 구현했습니다.
    if st.button("🧹 전체 캐시 강제 삭제", help="지도가 빨갛게 나오거나 데이터가 꼬일 때 사용하세요."):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("캐시가 완전히 삭제되었습니다!")
        st.rerun()

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
        df['기초지역'] = df['기초지역'].fillna('전체').astype(str).str.strip()
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
# 시군구 판세 분석 모드 (V6.9 적용)
# ------------------------------------------
if app_mode == "시군구 판세 분석":
    st.subheader("📍 기초자치단체별 상세 판세 분석")
    if is_valid:
        active_regions = df_current_latest[df_current_latest['기초지역'] != '전체']['지역'].unique().tolist()
        if 'selected_region' not in st.session_state: st.session_state['selected_region'] = '전남'
        
        st.write("분석할 지역을 클릭하세요:")
        cols = st.columns(6)
        all_regs = sorted(HEX_MAP.keys())
        for i, reg in enumerate(all_regs):
            with cols[i % 6]:
                prefix = "🔵 " if reg in active_regions else "⚪ "
                # 버튼을 누르면 브랜드 남색(Indigo)으로 변하도록 CSS가 적용되어 있습니다.
                if st.button(f"{prefix}{reg}", key=f"btn_{reg}", use_container_width=True,
                             type="primary" if st.session_state['selected_region'] == reg else "secondary"):
                    st.session_state['selected_region'] = reg
                    st.rerun() 
        
        st.divider()
        sel_reg = st.session_state['selected_region']
        st.plotly_chart(final_visual_map_engine(None, f"🔍 {sel_reg} 상세 분석 중", mode="status", active_regions=active_regions, highlight_region=sel_reg), use_container_width=True)

        sub_df = df_current_latest[(df_current_latest['지역'] == sel_reg) & (df_current_latest['기초지역'] != '전체')]
        if not sub_df.empty:
            st.markdown(f"### 🚩 {sel_reg} 상세 분석 결과")
            cmap = {'더불어민주당': '#004EA2', '국민의힘': '#E61E2B', '민주당': '#004EA2', '국힘': '#E61E2B'}
            fig_sub = px.bar(sub_df, x='기초지역', y='지지율', color='정당', text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"), barmode='group', color_discrete_map=cmap)
            st.plotly_chart(fig_sub, use_container_width=True)
            st.write("### 📋 상세 데이터 리스트")
            st.dataframe(sub_df[['기초지역', '후보', '정당', '지지율']].sort_values(['기초지역', '지지율'], ascending=[True, False]), hide_index=True, use_container_width=True)
        else:
            st.warning(f"🔔 {sel_reg} 지역의 기초 상세 데이터는 업데이트 대기 중입니다.")
# ... (다른 모드들은 V6.8과 동일)
