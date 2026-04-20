import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
import io
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. 페이지 설정 및 브랜딩 (CSS)
# ==========================================
st.set_page_config(page_title="T-Bridge Election Dashboard", page_icon="🌉", layout="wide")

BRAND_INDIGO = "#1A237E" 
GRAY_LIGHT = "#F5F5F5"   
SEL_FILL = "#E3F2FD"     # 선택 지역 배경
SEL_LINE = "#1565C0"     # 선택 지역 테두리

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    
    /* 선택된 버튼(Primary) 디자인 고정 */
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

# 2. 고정 데이터 (맵 좌표 및 2025 대선)
HEX_MAP = {'경기': (1, 6), '강원': (2, 6), '인천': (0, 5), '서울': (1, 5), '충북': (2, 5), '대전': (1, 4), '세종': (2, 4), '경북': (3, 4), '전북': (0, 3), '충남': (1, 3), '대구': (2, 3), '울산': (3, 3), '전남': (0, 2), '광주': (1, 2), '경남': (2, 2), '부산': (3, 2), '제주': (0, 1)}
NAME_MAPPING = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '세종시': '세종', '경기도': '경기', '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}

past_data_list = [['서울', '이재명', '민주당', 52.0], ['서울', '김문수', '국힘', 45.0], ['경기', '이재명', '민주당', 54.0], ['경기', '김문수', '국힘', 43.0], ['인천', '이재명', '민주당', 53.0], ['인천', '김문수', '국힘', 42.0], ['강원', '김문수', '국힘', 55.0], ['강원', '이재명', '민주당', 40.0], ['충북', '김문수', '국힘', 49.0], ['충북', '이재명', '민주당', 47.0], ['충남', '이재명', '민주당', 50.0], ['충남', '김문수', '국힘', 46.0], ['대전', '이재명', '민주당', 51.0], ['대전', '김문수', '국힘', 45.0], ['세종', '이재명', '민주당', 53.0], ['세종', '김문수', '국힘', 41.0], ['전북', '이재명', '민주당', 85.0], ['전북', '김문수', '국힘', 10.0], ['광주', '이재명', '민주당', 88.0], ['광주', '김문수', '국힘', 8.0], ['전남', '이재명', '민주당', 86.0], ['전남', '김문수', '국힘', 9.0], ['경북', '김문수', '국힘', 75.0], ['경북', '이재명', '민주당', 20.0], ['대구', '김문수', '국힘', 72.0], ['대구', '이재명', '민주당', 23.0], ['경남', '김문수', '국힘', 58.0], ['경남', '이재명', '민주당', 38.0], ['부산', '김문수', '국힘', 56.0], ['부산', '이재명', '민주당', 40.0], ['울산', '김문수', '국힘', 53.0], ['울산', '이재명', '민주당', 43.0], ['제주', '이재명', '민주당', 55.0], ['제주', '김문수', '국힘', 41.0]]
df_2025 = pd.DataFrame(past_data_list, columns=['지역', '후보', '정당', '지지율'])

# 3. 지도 시각화 엔진
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
                    party = str(win.get('정당', ''))
                    if '민주' in party: f_color = f'rgba(0, 78, 162, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    elif '국힘' in party: f_color = f'rgba(230, 30, 43, {alpha})'; t_color = 'white' if alpha > 0.4 else BRAND_INDIGO
                    else: f_color = f'rgba(128, 128, 128, {alpha})'; t_color = 'white'
                    h_text += f"<br>1위: {win['후보']} ({gap:.1f}%p 차)"

        fig.add_trace(go.Scatter(x=x_coords, y=y_coords, fill='toself', fillcolor=f_color, mode='lines', line=dict(color=l_color, width=l_width), name=region, text=h_text, hoverinfo='text'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=t_color, size=15, family="Noto Sans KR"), hoverinfo='skip'))

    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", font=dict(size=22, color=BRAND_INDIGO), x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x", scaleratio=1), height=550, plot_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0, r=0, t=60, b=0))
    return fig

# ==========================================
# 4. 데이터 로드 및 사이드바 (업로드 메뉴 복구)
# ==========================================
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
        st.error(f"구글 시트 연결 에러: {e}")
        return None, None

df_all, df_latest = load_data_from_gsheets()

with st.sidebar:
    st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드 선택", ["현행 판세 분석", "시군구 판세 분석", "2025 대선 비교 분석", "🎛️ 가상 시나리오 시뮬레이터"])
    
    st.divider()
    st.write("📂 **데이터 관리**")
    
    # 1. 새로고침 버튼 복구
    if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # 2. 캐시 삭제 버튼 유지
    if st.button("🧹 시스템 캐시 삭제", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    # 3. CSV 업로드 기능 추가 (혹시 모를 상황 대비)
    uploaded_file = st.file_uploader("📁 CSV 데이터 업로드", type="csv")
    if uploaded_file is not None:
        try:
            df_up = pd.read_csv(uploaded_file)
            df_up.columns = ['조사일자', '지역', '기초지역', '후보', '지지율', '정당']
            df_up['지역'] = df_up['지역'].astype(str).str.strip().replace(NAME_MAPPING)
            df_up['기초지역'] = df_up['기초지역'].fillna('전체')
            df_latest = df_up.drop_duplicates(subset=['지역', '기초지역', '후보'], keep='last').copy()
            st.success("임시 데이터 업로드 완료!")
        except:
            st.error("파일 형식이 맞지 않습니다.")

    st.divider()
    st.caption("⚠️ 인용 조사는 중앙선거여론조사심의위원회 참조")

st.markdown("""<div class='main-header'><h1>T-Bridge 헥사곤 판세 분석 솔루션 (Live)</h1></div>""", unsafe_allow_html=True)

# ==========================================
# 5. 메인 화면 구현 (전체 복구)
# ==========================================
is_valid = df_latest is not None and not df_latest.empty

if app_mode == "현행 판세 분석":
    df_prov = df_latest[df_latest['기초지역'] == '전체'] if is_valid else None
    st.plotly_chart(final_visual_map_engine(df_prov, "실시간 전국 광역 시·도별 판세"), use_container_width=True)

elif app_mode == "시군구 판세 분석":
    if is_valid:
        active_regions = df_latest[df_latest['기초지역'] != '전체']['지역'].unique().tolist()
        if 'selected_region' not in st.session_state: st.session_state['selected_region'] = '전남'
        
        st.write("분석할 지역을 클릭하세요:")
        cols = st.columns(6)
        all_regs = sorted(HEX_MAP.keys())
        for i, reg in enumerate(all_regs):
            with cols[i % 6]:
                prefix = "🔵 " if reg in active_regions else "⚪ "
                if st.button(f"{prefix}{reg}", key=f"btn_{reg}", use_container_width=True,
                             type="primary" if st.session_state['selected_region'] == reg else "secondary"):
                    st.session_state['selected_region'] = reg
                    st.rerun() 
        
        st.divider()
        sel_reg = st.session_state['selected_region']
        st.plotly_chart(final_visual_map_engine(None, f"🔍 {sel_reg} 상세 분석 중", mode="status", active_regions=active_regions, highlight_region=sel_reg), use_container_width=True)

        sub_df = df_latest[(df_latest['지역'] == sel_reg) & (df_latest['기초지역'] != '전체')]
        if not sub_df.empty:
            st.markdown(f"### 🚩 {sel_reg} 상세 분석 결과")
            cmap = {'더불어민주당': '#004EA2', '국민의힘': '#E61E2B', '민주당': '#004EA2', '국힘': '#E61E2B'}
            fig_sub = px.bar(sub_df, x='기초지역', y='지지율', color='정당', text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"), barmode='group', color_discrete_map=cmap)
            st.plotly_chart(fig_sub, use_container_width=True)
            st.write("### 📋 상세 데이터")
            st.dataframe(sub_df[['기초지역', '후보', '정당', '지지율']].sort_values(['기초지역', '지지율'], ascending=[True, False]), hide_index=True, use_container_width=True)

elif app_mode == "2025 대선 비교 분석":
    col1, col2 = st.columns(2)
    df_prov = df_latest[df_latest['기초지역'] == '전체'] if is_valid else None
    with col1: st.plotly_chart(final_visual_map_engine(df_2025, "🗳️ 2025년 대선 결과"), use_container_width=True)
    with col2: st.plotly_chart(final_visual_map_engine(df_prov, "📈 현재 실시간 판세"), use_container_width=True)

elif app_mode == "🎛️ 가상 시나리오 시뮬레이터":
    if is_valid:
        df_prov = df_latest[df_latest['기초지역'] == '전체'].copy()
        col_s1, col_s2 = st.columns(2)
        with col_s1: adj_minju = st.slider("🔵 민주당 조정 (%p)", -15.0, 15.0, 0.0, 0.5)
        with col_s2: adj_gukhim = st.slider("🔴 국힘 조정 (%p)", -15.0, 15.0, 0.0, 0.5)
        df_sim = df_prov.reset_index(drop=True)
        for idx, row in df_sim.iterrows():
            p = str(row['정당'])
            if '민주' in p: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_minju)
            elif '국힘' in p or '국민의힘' in p: df_sim.loc[idx, '지지율'] = max(0, row['지지율'] + adj_gukhim)
        st.plotly_chart(final_visual_map_engine(df_sim, "시뮬레이션 결과 반영"), use_container_width=True)
