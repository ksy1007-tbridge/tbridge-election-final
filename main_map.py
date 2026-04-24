import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 브랜딩 컬러
st.set_page_config(page_title="T-Bridge Dashboard", page_icon="🌉", layout="wide")
C_MINJU, C_GUKHIM, C_OTHER = "#004EA2", "#E61E2B", "#808080"
B_INDIGO, S_FILL, S_LINE = "#1A237E", "#E3F2FD", "#1565C0"

# CSS: 스타일 강제 고정
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
    html, body, [class*="css"] {{ font-family: 'Noto Sans KR', sans-serif; }}
    div.stButton > button {{ background-color: white !important; color: {B_INDIGO} !important; border: 1px solid {B_INDIGO} !important; }}
    div.stButton > button[kind="primary"] {{ background-color: {B_INDIGO} !important; color: white !important; border: none !important; }}
    .main-header {{ background: white; padding: 20px; border-radius: 10px; border-left: 12px solid {B_INDIGO}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    .main-header h1 {{ color: {B_INDIGO}; margin: 0; font-weight: 900; font-size: 28px; }}
</style>
""", unsafe_allow_html=True)

HEX_MAP = {'경기':(1,6),'강원':(2,6),'인천':(0,5),'서울':(1,5),'충북':(2,5),'대전':(1,4),'세종':(2,4),'경북':(3,4),'전북':(0,3),'충남':(1,3),'대구':(2,3),'울산':(3,3),'전남':(0,2),'광주':(1,2),'경남':(2,2),'부산':(3,2),'제주':(0,1)}
NAME_MAP = {'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','광주광역시':'광주','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','세종시':'세종','경기도':'경기','강원도':'강원','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전라북도':'전북','전북특별자치도':'전북','전라남도':'전남','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','제주도':'제주'}

# 도움 함수들
def get_party_pri(p):
    p = str(p)
    return 1 if '민주' in p else (2 if '국민' in p or '국힘' in p else 99)

def get_colors(df):
    m = {}
    for _, r in df.iterrows():
        c, p = r['후보'], str(r['정당'])
        m[c] = C_MINJU if '민주' in p else (C_GUKHIM if '국민' in p or '국힘' in p else C_OTHER)
    return m

def get_hex(col, row, r=1):
    cx, cy = col*math.sqrt(3)*r + (row%2==1)*(math.sqrt(3)/2)*r, row*1.5*r
    x_pts, y_pts = [], []
    for i in range(6):
        a = math.pi/6 + i*math.pi/3
        x_pts.append(cx + r*math.cos(a)); y_pts.append(cy + r*math.sin(a))
    return cx, cy, x+[x[0]], y+[y[0]]

def draw_map(df, title, highlight="", mode="normal", active=[]):
    fig = go.Figure()
    if df is not None:
        df = df.copy()
        df['지역'] = df['지역'].replace(NAME_MAP)
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
    fig.update_layout(title=dict(text=f"<b>{title}</b>", x=0.5, font=dict(color=B_INDIGO, size=22)), xaxis=dict(visible=False), yaxis=dict(visible=False, scaleanchor="x"), height=520, showlegend=False, margin=dict(l=0,r=0,t=60,b=0), plot_bgcolor='rgba(0,0,0,0)')
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

# 4. 사이드바 메뉴
with st.sidebar:
    st.markdown("## T-Bridge")
    mode = st.radio("📊 분석 메뉴", ["현행 판세", "시군구 판세", "대선 비교"])
    if st.button("🔄 데이터 새로고침"): st.cache_data.clear(); st.rerun()

st.markdown("<div class='main-header'><h1>T-Bridge 판세 분석 솔루션 (Live)</h1></div>", unsafe_allow_html=True)

# 5. [중요] 공통 지역 선택 내비게이션 (상단 배치)
if 'sel_reg' not in st.session_state: st.session_state.sel_reg = '서울'
sel = st.session_state.sel_reg

# 시군구 데이터가 있는 지역에 파란 점 표시를 위한 리스트
act_regs = d_lat[d_lat['기초지역']!='전체']['지역'].unique()

st.write("### 📍 지역 선택")
nav_cols = st.columns(6)
all_regs = sorted(HEX_MAP.keys())
for i, r in enumerate(all_regs):
    prefix = "🔵 " if r in act_regs else ""
    if nav_cols[i%6].button(f"{prefix}{r}", key=f"nav_{r}", use_container_width=True, type="primary" if sel == r else "secondary"):
        st.session_state.sel_reg = r
        st.rerun()

st.divider()

# 6. 모드별 콘텐츠 출력
if mode == "현행 판세":
    d_prov = d_lat[d_lat['기초지역']=='전체']
    st.plotly_chart(draw_map(d_prov, f"전국 광역 지지율 현황 (선택: {sel})", highlight=sel), use_container_width=True)
    
    st.divider()
    # 추세 그래프 (상위 2인 기준)
    reg_hist = d_all[(d_all['지역'] == sel) & (d_all['기초지역'] == '전체')].sort_values('조사일자')
    if not reg_hist.empty:
        st.write(f"### 📈 {sel} 지지율 추세")
        fig_line = px.line(reg_hist, x='조사일자', y='지지율', color='후보', markers=True, color_discrete_map=get_colors(reg_hist))
        st.plotly_chart(fig_line, use_container_width=True)

    # 현황 막대 (상위 2인)
    reg_lat = d_prov[d_prov['지역']==sel].copy()
    reg_lat = reg_lat[reg_lat['지지율'] > 0].sort_values('지지율', ascending=False).head(2)
    if not reg_lat.empty:
        st.write(f"### 📊 {sel} 최신 지지율 현황 (Top 2)")
        fig_bar = go.Figure()
        reg_lat['p_pri'] = reg_lat['정당'].apply(get_party_pri)
        for cand in reg_lat.sort_values(['p_pri', '지지율'], ascending=[True, False])['후보'].unique():
            df_c = reg_lat[reg_lat['후보'] == cand]
            party = str(df_c['정당'].iloc[0])
            color = C_MINJU if '민주' in party else (C_GUKHIM if '국민' in party or '국힘' in party else C_OTHER)
            offset = -0.35 if '민주' in party else 0.0
            fig_bar.add_trace(go.Bar(name=cand, x=df_c['기초지역'], y=df_c['지지율'], text=df_c['지지율'].apply(lambda x: f"{x:.1f}%"), textposition='outside', marker_color=color, offset=offset, width=0.35))
        fig_bar.update_layout(barmode='overlay', yaxis=dict(range=[0, 105]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='white', bargap=0.1)
        st.plotly_chart(fig_bar, use_container_width=True)

elif mode == "시군구 판세":
    st.plotly_chart(draw_map(None, f"🔍 {sel} 시군구 판세 상세 분석", mode="status", active=act_regs, highlight=sel), use_container_width=True)
    
    sub = d_lat[d_lat['지역']==sel].copy()
    if not sub.empty:
        # 상위 2명 로직 적용 (유령 슬롯 제거)
        sub = sub[sub['지지율'] > 0]
        sub = sub.sort_values(['기초지역', '지지율'], ascending=[True, False]).groupby('기초지역').head(2).reset_index(drop=True)
        
        fig = go.Figure()
        muni_list = ['전체'] + sorted([m for m in sub['기초지역'].unique() if m != '전체'])
        sub['p_pri'] = sub['정당'].apply(get_party_pri)
        for cand in sub.sort_values(['p_pri', '지지율'], ascending=[True, False])['후보'].unique():
            df_c = sub[sub['후보'] == cand]
            party = str(df_c['정당'].iloc[0])
            color = C_MINJU if '민주' in party else (C_GUKHIM if '국민' in party or '국힘' in party else C_OTHER)
            offset = -0.35 if '민주' in party else 0.0
            fig.add_trace(go.Bar(name=cand, x=df_c['기초지역'], y=df_c['지지율'], text=df_c['지지율'].apply(lambda x: f"{x:.1f}%"), textposition='outside', marker_color=color, offset=offset, width=0.35))
        fig.update_layout(barmode='overlay', xaxis=dict(categoryorder='array', categoryarray=muni_list), yaxis=dict(range=[0, 105]), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), plot_bgcolor='white', bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### 📋 상세 데이터 (상위 2인 기준)")
        sub['m_key'] = sub['기초지역'].apply(lambda x: 0 if x == '전체' else 1)
        table_df = sub.sort_values(['m_key', '기초지역', 'p_pri'])[['기초지역', '후보', '정당', '지지율']]
        st.dataframe(table_df, hide_index=True, use_container_width=True)

elif mode == "대선 비교":
    # 2025 대선 실제 데이터
    p_list = [['서울특별시','이재명','더불어민주당',47.13],['서울특별시','김문수','국민의힘',41.55],['인천광역시','이재명','더불어민주당',51.67],['인천광역시','김문수','국민의힘',38.44],['경기도','이재명','더불어민주당',52.20],['경기도','김문수','국민의힘',37.95],['강원특별자치도','이재명','더불어민주당',43.95],['강원특별자치도','김문수','국민의힘',47.30],['대전광역시','이재명','더불어민주당',48.50],['대전광역시','김문수','국민의힘',40.58],['세종특별자치시','이재명','더불어민주당',55.62],['세종특별자치시','김문수','국민의힘',33.21],['충청북도','이재명','더불어민주당',47.47],['충청북도','김문수','국민의힘',43.22],['충청남도','이재명','더불어민주당',47.68],['충청남도','김문수','국민의힘',43.26],['광주광역시','이재명','더불어민주당',84.77],['광주광역시','김문수','국민의힘',8.02],['전북특별자치도','이재명','더불어민주당',82.65],['전북특별자치도','김문수','국민의힘',10.90],['전라남도','이재명','더불어민주당',85.87],['전라남도','김문수','국민의힘',8.54],['대구광역시','이재명','더불어민주당',23.22],['대구광역시','김문수','국민의힘',67.62],['경상북도','이재명','더불어민주당',25.52],['경상북도','김문수','국민의힘',66.87],['부산광역시','이재명','더불어민주당',40.14],['부산광역시','김문수','국민의힘',51.39],['울산광역시','이재명','더불어민주당',42.54],['울산광역시','김문수','국민의힘',47.57],['경상남도','이재명','더불어민주당',39.40],['경상남도','김문수','국민의힘',51.99],['제주특별자치도','이재명','더불어민주당',54.76],['제주특별자치도','김문수','국민의힘',34.78]]
    d_25 = pd.DataFrame(p_list, columns=['지역','후보','정당','지지율'])
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(draw_map(d_25, "🗳️ 2025 대선 결과 (확정)"), use_container_width=True)
    with c2: st.plotly_chart(draw_map(d_lat[d_lat['기초지역']=='전체'], "📈 현재 실시간 판세 (Live)"), use_container_width=True)
