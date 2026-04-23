import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 브랜딩
st.set_page_config(page_title="T-Bridge Dashboard", page_icon="🌉", layout="wide")

COLOR_MINJU, COLOR_GUKHIM, COLOR_OTHER = "#004EA2", "#E61E2B", "#808080"
BRAND_INDIGO, SEL_FILL, SEL_LINE = "#1A237E", "#E3F2FD", "#1565C0"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    button[kind="primary"] {{ background-color: {BRAND_INDIGO} !important; border-color: {BRAND_INDIGO} !important; color: white !important; font-weight: bold !important; }}
    .main-header {{ background-color: white; padding: 20px; border-radius: 10px; border-left: 12px solid {BRAND_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    .main-header h1 {{ color: {BRAND_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

HEX_MAP = {'경기': (1, 6), '강원': (2, 6), '인천': (0, 5), '서울': (1, 5), '충북': (2, 5), '대전': (1, 4), '세종': (2, 4), '경북': (3, 4), '전북': (0, 3), '충남': (1, 3), '대구': (2, 3), '울산': (3, 3), '전남': (0, 2), '광주': (1, 2), '경남': (2, 2), '부산': (3, 2), '제주': (0, 1)}
NAME_MAPPING = {'서울특별시': '서울', '부산광역시': '부산', '대구광역시': '대구', '인천광역시': '인천', '광주광역시': '광주', '대전광역시': '대전', '울산광역시': '울산', '세종특별자치시': '세종', '세종시': '세종', '경기도': '경기', '강원도': '강원', '강원특별자치도': '강원', '충청북도': '충북', '충청남도': '충남', '전라북도': '전북', '전북특별자치도': '전북', '전라남도': '전남', '경상북도': '경북', '경상남도': '경남', '제주특별자치도': '제주', '제주도': '제주'}

# 2. 헬퍼 함수
def get_dynamic_color_map(df):
    c_map = {}
    if df is not None and not df.empty:
        for _, row in df.iterrows():
            cand, party = row['후보'], str(row['정당']).strip()
            if '민주' in party: c_map[cand] = COLOR_MINJU
            elif '국민' in party or '국힘' in party: c_map[cand] = COLOR_GUKHIM
            else: c_map[cand] = COLOR_OTHER
    return c_map

def get_sorted_candidate_order(df):
    if df is None or df.empty: return []
    plist = []
    for c in df['후보'].unique():
        p_str = str(df[df['후보'] == c]['정당'].iloc[0])
        pri = 1 if '민주' in p_str else (2 if '국민' in p_str or '국힘' in p_str else 99)
        plist.append({'후보': c, 'priority': pri})
    return pd.DataFrame(plist).sort_values('priority')['후보'].tolist()

def get_hexagon_path(col, row, radius=1):
    cx, cy = col * math.sqrt(3) * radius + (row % 2 == 1) * (math.sqrt(3)/2) * radius, row * 1.5 * radius
    x_pts, y_pts = [], []
    for i in range(6):
        a = math.pi/6 + i*math.pi/3
        x_pts.append(cx + radius*math.cos(a))
        y_pts.append(cy + radius*math.sin(a))
    return cx, cy, x_pts + [x_pts[0]], y_pts + [y_pts[0]]

def final_visual_map_engine(df, title_text, highlight_region="", mode="normal", active_regions=None):
    if active_regions is None: active_regions = []
    fig = go.Figure()
    for region, (col, row) in HEX_MAP.items():
        cx, cy, x_pts, y_pts = get_hexagon_path(col, row)
        f_color, t_color, l_color, l_width = '#F8F9FA', BRAND_INDIGO, "#DEE2E6", 1.2
        if region == highlight_region: f_color, l_color, l_width = SEL_FILL, SEL_LINE, 5
        elif mode == "status":
            f_color = BRAND_INDIGO if region in active_regions else "#F5F5F5"
            t_color = "white" if region in active_regions else "#ADB5BD"
        elif df is not None and not df.empty:
            r = df[df['지역'] == region].sort_values('지지율', ascending=False)
            if not r.empty:
                win = r.iloc[0]
                gap = win['지지율'] - r.iloc[1]['지지율'] if len(r) > 1 else 0
                alpha = max(0.2, min(gap/25.0, 1.0))
                p = str(win.get('정당', ''))
                if '민주' in p: f_color = f'rgba(0, 78, 162, {alpha})'
                elif '국민' in p or '국힘' in p: f_color = f'rgba(230, 30, 43, {alpha})'
        fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill='toself', fillcolor=f_color, mode='lines', line=dict(color=l_color, width=l_width), name=region, hoverinfo='none'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{region}</b>"], textfont=dict(color=t_color, size=15), hoverinfo='skip'))
    fig.update_layout(title=dict(text=f"<b>{title_text}</b>", x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), height=550, showlegend=False, margin=dict(l=0, r=0, t=60, b=0), plot_bgcolor='rgba(0,0,0,0)')
    return fig

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read()
        df.columns = ['조사일자', '지역', '기초지역', '후보', '지지율', '정당']
        df['지역'] = df['지역'].astype(str).str.strip().replace(NAME_MAPPING)
        df['기초지역'] = df['기초지역'].fillna('전체').astype(str).str.strip()
        df['지지율'] = pd.to_numeric(df['지지율'].astype(str).str.replace('%',''), errors='coerce').fillna(0)
        df['조사일자'] = pd.to_datetime(df['조사일자']).dt.date
        df_avg = df.groupby(['조사일자', '지역', '기초지역', '후보', '정당'], as_index=False)['지지율'].mean()
        df_latest = df_avg.sort_values('조사일자').drop_duplicates(subset=['지역', '기초지역', '후보'], keep='last')
        return df_avg, df_latest
    except Exception as e:
        st.error(f"Error: {e}"); return None, None

df_all, df_latest = load_data()

with st.sidebar:
    st.markdown(f"<h2 style='text-align: center; color: {BRAND_INDIGO};'>T-Bridge</h2>", unsafe_allow_html=True)
    app_mode = st.radio("📊 보기 모드", ["현행 판세 분석", "시군구 판세 분석", "2025 대선 비교 분석"])
    if st.button("🔄 새로고침", use_container_width=True): st.cache_data.clear(); st.rerun()

st.markdown("<div class='main-header'><h1>T-Bridge 판세 분석 (Live)</h1></div>", unsafe_allow_html=True)
if 'selected_region' not in st.session_state: st.session_state['selected_region'] = '서울'
sel_reg = st.session_state['selected_region']

if app_mode == "현행 판세 분석":
    df_prov = df_latest[df_latest['기초지역'] == '전체']
    cols = st.columns(6)
    for i, reg in enumerate(sorted(HEX_MAP.keys())):
        if cols[i%6].button(reg, key=f"p_{reg}", use_container_width=True, type="primary" if sel_reg == reg else "secondary"):
            st.session_state['selected_region'] = reg; st.rerun()
    st.plotly_chart(final_visual_map_engine(df_prov, "전국 광역 지지율", highlight_region=sel_reg), use_container_width=True)
    st.divider()
    reg_latest = df_prov[df_prov['지역'] == sel_reg].copy()
    reg_latest = reg_latest[reg_latest['지지율'] > 0]
    if not reg_latest.empty:
        d_colors = get_dynamic_color_map(reg_latest)
        f_order = get_sorted_candidate_order(reg_latest)
        fig = px.bar(reg_latest, x='후보', y='지지율', color='후보', text=reg_latest['지지율'].apply(lambda x: f"{x:.1f}%"), color_discrete_map=d_colors, category_orders={'후보': f_order})
        fig.update_layout(bargap=0.2, bargroupgap=0.0)
        st.plotly_chart(fig, use_container_width=True)

elif app_mode == "시군구 판세 분석":
    active_regs = df_latest[df_latest['기초지역'] != '전체']['지역'].unique()
    cols = st.columns(6)
    for i, reg in enumerate(sorted(HEX_MAP.keys())):
        p = "🔵 " if reg in active_regs else "⚪ "
        if cols[i%6].button(f"{p}{reg}", key=f"m_{reg}", use_container_width=True, type="primary" if sel_reg == reg else "secondary"):
            st.session_state['selected_region'] = reg; st.rerun()
    sub_df = df_latest[df_latest['지역'] == sel_reg].copy()
    if not sub_df.empty:
        # [핵심] 현재 지역에 지지율 0보다 큰 후보만 남겨서 유령 슬롯 제거
        sub_df = sub_df[sub_df['지지율'] > 0]
        sub_df['후보'] = sub_df['후보'].astype(str)
        d_colors = get_dynamic_color_map(sub_df)
        f_order = get_sorted_candidate_order(sub_df)
        sorted_muni = ['전체'] + sorted([m for m in sub_df['기초지역'].unique() if m != '전체'])
        fig_sub = px.bar(sub_df, x='기초지역', y='지지율', color='후보', text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"), barmode='group', color_discrete_map=d_colors, category_orders={'후보': f_order, '기초지역': sorted_muni})
        fig_sub.update_layout(bargap=0.15, bargroupgap=0.0)
        st.plotly_chart(fig_sub, use_container_width=True)
        sub_df['m_key'] = sub_df['기초지역'].apply(lambda x: 0 if x == '전체' else 1)
        sub_df['p_key'] = sub_df['정당'].apply(lambda x: 1 if '민주' in str(x) else (2 if '국민' in str(x) or '국힘' in str(x) else 99))
        st.dataframe(sub_df.sort_values(['m_key', '기초지역', 'p_key'])[['기초지역', '후보', '정당', '지지율']], hide_index=True, use_container_width=True)

elif app_mode == "2025 대선 비교 분석":
    past_list = [['서울', '이재명', '민주당', 52.0], ['서울', '김문수', '국민의힘', 45.0], ['경기', '이재명', '민주당', 54.0], ['경기', '김문수', '국민의힘', 43.0]]
    df_2025_sub = pd.DataFrame(past_list, columns=['지역', '후보', '정당', '지지율'])
    df_prov = df_latest[df_latest['기초지역'] == '전체']
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(final
