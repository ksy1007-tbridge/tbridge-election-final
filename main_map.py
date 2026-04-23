# [시군구 판세 분석 모드 코드 수정본]
elif app_mode == "시군구 판세 분석":
    active_regs = df_latest[df_latest['기초지역'] != '전체']['지역'].unique()
    cols = st.columns(6)
    for i, reg in enumerate(sorted(HEX_MAP.keys())):
        p = "🔵 " if reg in active_regs else "⚪ "
        if cols[i%6].button(f"{p}{reg}", key=f"m_{reg}", use_container_width=True, type="primary" if sel_reg == reg else "secondary"):
            st.session_state['selected_region'] = reg; st.rerun()
    
    st.plotly_chart(final_visual_map_engine(None, f"🔍 {sel_reg} 시군구 분석", mode="status", active_regions=active_regs, highlight_region=sel_reg), use_container_width=True)
    
    # 1. 데이터 필터링
    sub_df = df_latest[df_latest['지역'] == sel_reg].copy()
    
    if not sub_df.empty:
        # [V9.6 핵심] 현재 지역(예: 서울)에서 지지율이 0보다 큰 후보만 남김 (유령 후보 제거)
        present_candidates = sub_df[sub_df['지지율'] > 0]['후보'].unique().tolist()
        sub_df = sub_df[sub_df['후보'].isin(present_candidates)]
        
        # 2. 정렬 로직 (이재명-김문수 순서 유지)
        f_order = [c for c in get_sorted_candidate_order(sub_df) if c in present_candidates]
        d_colors = get_dynamic_color_map(sub_df)
        sorted_muni = ['전체'] + sorted([m for m in sub_df['기초지역'].unique() if m != '전체'])
        
        # 3. 차트 생성
        fig_sub = px.bar(
            sub_df, 
            x='기초지역', 
            y='지지율', 
            color='후보', 
            text=sub_df['지지율'].apply(lambda x: f"{x:.1f}%"), 
            barmode='group', 
            color_discrete_map=d_colors, 
            category_orders={'후보': f_order, '기초지역': sorted_muni}
        )
        
        # 4. [V9.6 디자인 설정] 막대를 굵게 만들고 딱 붙임
        fig_sub.update_layout(
            bargap=0.1,        # 구(District) 사이의 간격 (줄일수록 막대가 굵어짐)
            bargroupgap=0.0,    # 후보자(Candidate) 사이의 간격 (0으로 설정하여 밀착)
            xaxis=dict(type='category')
        )
        
        # 텍스트 위치 및 가독성 설정
        fig_sub.update_traces(textposition='outside', textfont_size=12)
        
        st.plotly_chart(fig_sub, use_container_width=True)
        
        # 5. 하단 상세 데이터 표 (이재명-김문수 순 정렬 고정)
        st.write("### 📋 상세 데이터 (전체 포함)")
        sub_df['m_key'] = sub_df['기초지역'].apply(lambda x: 0 if x == '전체' else 1)
        sub_df['p_key'] = sub_df['정당'].apply(lambda x: 1 if '민주' in str(x) else (2 if '국민' in str(x) or '국힘' in str(x) else 99))
        
        # 표에서도 유령 후보 제외하고 출력
        final_table = sub_df.sort_values(['m_key', '기초지역', 'p_key'])[['기초지역', '후보', '정당', '지지율']]
        st.dataframe(final_table, hide_index=True, use_container_width=True)

# 2025 대선 비교 및 시뮬레이터 로직은 이전과 동일하게 유지
elif app_mode == "2025 대선 비교 분석":
    df_prov = df_latest[df_latest['기초지역'] == '전체']
    past_list = [['서울', '이재명', '민주당', 52.0], ['서울', '김문수', '국민의힘', 45.0], ['경기', '이재명', '민주당', 54.0], ['경기', '김문수', '국민의힘', 43.0]]
    df_2025_sub = pd.DataFrame(past_list, columns=['지역', '후보', '정당', '지지율'])
    c1, c2 = st.columns(2)
    with c1: st.plotly_chart(final_visual_map_engine(df_2025_sub, "🗳️ 2025년 대선 결과"), use_container_width=True)
    with c2: st.plotly_chart(final_visual_map_engine(df_prov, "📈 현재 실시간 판세"), use_container_width=True)

elif app_mode == "🎛️ 가상 시나리오 시뮬레이터":
    df_prov = df_latest[df_latest['기초지역'] == '전체'].copy()
    c1, c2 = st.columns(2)
    m_adj, g_adj = c1.slider("🔵 민주당 조정", -15.0, 15.0, 0.0), c2.slider("🔴 국힘 조정", -15.0, 15.0, 0.0)
    for i, r in df_prov.iterrows():
        p = str(r['정당'])
        if '민주' in p: df_prov.at[i, '지지율'] = max(0, r['지지율'] + m_adj)
        elif '국민' in p or '국힘' in p: df_prov.at[i, '지지율'] = max(0, r['지지율'] + g_adj)
    st.plotly_chart(final_visual_map_engine(df_prov, "시뮬레이션 결과 반영"), use_container_width=True)
