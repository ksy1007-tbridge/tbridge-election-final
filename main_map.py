import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 브랜딩 컬러 강제 고정
st.set_page_config(page_title="T-Bridge Dashboard", page_icon="🌉", layout="wide")
C_MINJU, C_GUKHIM, C_OTHER = "#004EA2", "#E61E2B", "#808080"
B_INDIGO, S_FILL, S_LINE = "#1A237E", "#E3F2FD", "#1565C0"

# CSS: 버튼 색상 및 헤더 스타일 강제 지정
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    /* 버튼 빨간색 변신 방지 및 인디고 고정 */
    div.stButton > button:first-child {{
        background-color: white; color: {B_INDIGO}; border: 1px solid {B_INDIGO};
    }}
    div.stButton > button[kind="primary"] {{
        background-color: {B_INDIGO} !important; color: white !important; border: none !important;
    }}
    .main-header {{
        background: white; padding: 20px; border-radius: 10px;
        border-left: 12px solid {B_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px;
    }}
    .main-header h1 {{ color: {B_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

HEX_MAP = {'경기':(1,6),'강원':(2,6),'인천':(0,5),'서울':(1,5),'충북':(2,5),'대전':(1,4),'세종':(2,4),'경북':(3,4),'전북':(0,3),'충남':(1,3),'대구':(2,3),'울산':(3,3),'전남':(0,2),'광주':(1,2),'경남':(2,2),'부산':(3,2),'제주':(0,1)}
NAME_MAP = {'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','세종시':'세종','경기도':'경기','강원도':'강원','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전라북도':'전북','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','제주도':'제주'}

# 2. 도움 함수
def get_colors(df):
    m = {}
    if df is not None:
        for _, r in df.iterrows():
            c, p = r['후보'], str(r['정당'])
            if '민주' in p: m[c] = C_MINJU
            elif '국민' in p or '국힘' in p: m[c] = C_GUKHIM
            else: m[c] = C_OTHER
    return m

def get_order(df):
    if df is None or df.empty: return []
    plist = []
    # 현재 데이터프레임에 실제 존재하는 후보만 리스트업
    for c in df['후보'].unique():
        p = str(df[df['후보']==c]['정당'].iloc[0])
        pri = 1 if '민주' in p else (2 if '국민' in p or '국힘' in p else 99)
        plist.append({'후보':c, 'pri':pri})
    return pd.DataFrame(plist).sort_values('pri')['후보'].tolist()

def get_hex(col, row, r=1):
    cx, cy = col*math.sqrt(3)*r + (row%2==1)*(math.sqrt(3)/2)*r, row*1.5*r
    x, y = [], []
    for i in range(6):
        a = math.pi/6 + i*math.pi/3
        x.append(cx + r*math.cos(a)); y.append(cy + r*math.sin(a))
    return cx, cy, x+[x[0]], y+[y[0]]

def draw_map(df, title, highlight="", mode="normal", active=[]):
    fig = go.Figure()
    for reg, (col, row) in HEX_MAP.items():
        cx, cy, x_pts, y_pts = get_hex(col, row)
        fc, tc, lc, lw = '#F8F9FA', B_INDIGO, "#DEE2E6", 1.2
        if reg == highlight: fc, lc, lw = S_FILL, S_LINE, 5
        elif mode == "status": fc, tc = (B_INDIGO, "white") if reg in active else ("#F5F5F5", "#ADB5BD")
        elif df is not None and not df.empty:
            r = df[df['지역']==reg].sort_values('지지율', ascending=False)
            if not r.empty:
                w = r.iloc[0]; gap = w['지지율'] - r.iloc[1]['지지율'] if len(r)>1 else 0
                a = max(0.2, min(gap/25.0, 1.0)); p = str(w['정당'])
                if '민주' in p: fc = f'rgba(0,78,162,{a})'
                elif '국민' in p or '국힘' in p: fc = f'rgba(230,30,43,{a})'
        fig.add_trace(go.Scatter(x=x_pts, y=y_pts, fill='toself', fillcolor=fc, mode='lines', line=dict(color=lc, width=lw), name=reg, hoverinfo='none'))
        fig.add_trace(go.Scatter(x=[cx], y=[cy], mode='text', text=[f"<b>{reg}</b>"], textfont=dict(color=tc, size=15), hoverinfo='skip'))
    fig.update_layout(title=dict(text=f"<b>{title}</b>", x=0.5), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), height=520, showlegend=False, margin=dict(l=0,r=0,t=60,b=0), plot_bgcolor='rgba(0,0,0,0)')
    return fig

@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read()
        df.columns = ['조사일자','지역','기초지역','후보','지지율','정당']
        df['지역'] = df['지역'].astype(str).str.strip().replace(NAME_MAP)
        df['기초지역'] = df['기초지역'].fillna('전체').astype(str).str.strip()
        df['지지율'] = pd.to_numeric(df['지지율'].astype(str).str.replace('%',''), errors='coerce').fillna(0)
        df['조사일자'] = pd.to_datetime(df['조사일자']).dt.date
        d_avg = df.groupby(['조사일자','지역','기초지역','후보','정당'], as_index=False)['지지율'].mean()
        d_lat = d_avg.sort_values('조사일자').drop_duplicates(subset=['지역','기초지역','후보'], keep='last')
        return d_avg, d_lat
    except: return None, None

d_all, d_lat = load_data()

# 3. 사이드바 및 메인
with st.sidebar:
    st.markdown(f"## T-Bridge")
    mode = st.radio("메뉴", ["현행 판세", "시군구 판세", "대선 비교"])
    if st.button("🔄 새로고침"): st.cache_data.clear(); st.rerun()

st.markdown("<div class='main-header'><h1>T-Bridge 판세 분석 (Live)</h1></div>", unsafe_allow_html=True)
if 'sel_reg' not in st.session_state: st.session_state.sel_reg = '서울'
sel = st.session_state.sel_reg

# [모드 1] 현행 판세
if mode == "현행 판세":
    d_prov = d_lat[d_lat['기초지역']=='전체']
    c = st.columns(6); all_regs = sorted(HEX_MAP.keys())
    for i, r in enumerate(all_regs):
        if c[i%6].button(r, key=f"p{r}", use_container_width=True, type="primary" if sel==r else "secondary"):
            st.session_state.sel_reg = r; st.rerun()
    st.plotly_chart(draw_map(d_prov, "전국 광역 현황", highlight=sel), use_container_width=True)
    st.divider()
    reg_lat = d_prov[d_prov['지역']==sel].copy()
    reg_lat = reg_lat[reg_lat['지지율']>0]
    if not reg_lat.empty:
        colors, order = get_colors(reg_lat), get_order(reg_lat)
        fig = px.bar(reg_lat, x='후보', y='지지율', color='후보', text=reg_lat['지지율'].apply(lambda x:f"{x:.1f}%"), color_discrete_map=colors, category_orders={'후보':order})
        fig.update_layout(bargap=0.2, bargroupgap=0.0); st.plotly_chart(fig, use_container_width=True)

# [모드 2] 시군구 판세 (유령 슬롯 박멸)
elif mode == "시군구 판세":
    act = d_lat[d_lat['기초지역']!='전체']['지역'].unique()
    c = st.columns(6); all_regs = sorted(HEX_MAP.keys())
    for i, r in enumerate(all_regs):
        p = "🔵 " if r in act else "⚪ "
        if c[i%6].button(f"{p}{r}", key=f"m{r}", use_container_width=True, type="primary" if sel==r else "secondary"):
            st.session_state.sel_reg = r; st.rerun()
    st.plotly_chart(draw_map(None, f"{sel} 시군구", mode="status", active=act, highlight=sel), use_container_width=True)
    
    # [V11.0] 데이터 필터링 시점부터 유령 후보를 완전히 배제
    sub = d_lat[d_lat['지역']==sel].copy()
    if not sub.empty:
        sub = sub[sub['지지율'] > 0]
        # 후보 이름을 문자열로 다시 저장하여 카테고리 속성 초기화
        sub['후보'] = sub['후보'].astype(str)
        
        colors = get_colors(sub)
        order = get_order(sub)
        sorted_m = ['전체'] + sorted([m for m in sub['기초지역'].unique() if m != '전체'])
        
        # px.bar 생성 시 category_orders에 유령 후보가 포함되지 않도록 order 리스트를 sub에 있는 후보로만 한정
        fig = px.bar(sub, x='기초지역', y='지지율', color='후보', text=sub['지지율'].apply(lambda x:f"{x:.1f}%"), barmode='group', color_discrete_map=colors, category_orders={'후보':order, '기초지역':sorted_m})
        
        # bargroupgap=0.0 으로 막대 사이 틈 완전 제거, bargap으로 막대 굵기 확보
        fig.update_layout(bargap=0.15, bargroupgap=0.0)
        st.plotly_chart(fig, use_container_width=True)
        
        # 상세 데이터 표
        sub['m_key'] = sub['기초지역'].apply(lambda x: 0 if x == '전체' else 1)
        sub['p_key'] = sub['정당'].apply(lambda x: 1 if '민주' in str(x) else (2 if '국민' in str(x) or '국힘' in str(x) else 99))
        st.dataframe(sub.sort_values(['m_key', '기초지역', 'p_key'])[['기초지역', '후보', '정당', '지지율']], hide_index=True, use_container_width=True)

# [모드 3] 대선 비교
elif mode == "대선 비교":
    p_list = [['서울','이재명','민주당',52],['서울','김문수','국힘',45],['경기','이재명','민주당',54],['경기','김문수','국힘',43]]
    d_25 = pd.DataFrame(p_list, columns=['지역','후보','정당','지지율'])
    d_prov = d_lat[d_lat['기초지역']=='전체']
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(draw_map(d_25, "2025 대선"), use_container_width=True)
    with c2: st.plotly_chart(draw_map(d_prov, "현재 실시간"), use_container_width=True)
