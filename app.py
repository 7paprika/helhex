import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json
import datetime

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")
st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# =========================================================
# [A] 글로벌 상태(Session State) 초기화
# =========================================================
init_state = {
    'tag_no': 'HE-101', 
    'tube_fluid_name': 'Process Slurry',
    'shell_fluid_name': 'Cooling Water',
    'fluid_type': "Liquid (뉴턴 유체 - 물, 오일 등)",
    't_rho': 998.0, 't_cp': 4180.0, 't_k': 0.6, 't_mu': 1.0, 
    's_rho': 998.0, 's_mu': 1.0, 's_cp': 4180.0, 's_k': 0.6,
    'rheology_model': "Power-law (멱법칙)",
    'tau_y': 5.0, 'plastic_visc': 0.05,
    'consistency_k': 0.1, 'flow_index_n': 0.8,
    'm_hot': 5000.0, 'm_cold': 8000.0,
    'T_hot_in': 150.0, 'T_hot_out': 80.0,
    'T_cold_in': 30.0, 'T_cold_out': 60.0,
    'allowable_dp_tube': 1.5, 'allowable_dp_shell': 0.5,
    'N_p': 3, 
    'd_o': 25.4, 't_thick': 2.11, 'D_c': 400.0, 'pitch': 50.0, 'D_s': 500.0,
    'D_mandrel': 350.0, 
    'tube_material': 'Stainless Steel 316 (k = 16 W/m·K)', 'tube_k_wall': 16.0,
    'R_fi': 0.000176, 'R_fo': 0.000176
}

for k, v in init_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

def apply_json():
    try:
        parsed_data = json.loads(st.session_state['json_input_text'])
        for k, v in parsed_data.items():
            if k in init_state:
                st.session_state[k] = v
        st.success(f"✅ 설계 데이터(Tag: {st.session_state.get('tag_no')}) 로드 완료.")
    except Exception as e:
        st.error(f"🚨 데이터 로드 실패: {e}")

# =========================================================
# [B] 환경설정 및 사이드바
# =========================================================
with st.sidebar:
    st.header("📋 Document Control")
    st.text_input("Item Tag No.", key='tag_no')
    st.markdown("---")
    st.header("💾 설계 시나리오 (Save/Load)")
    current_tag = st.session_state.get('tag_no', 'HE-101')
    filename = f"{current_tag}_design.json"
    current_data = {k: st.session_state[k] for k in init_state.keys()}
    st.download_button(f"📥 '{filename}' 다운로드", json.dumps(current_data, indent=4), file_name=filename, mime="application/json")
    st.text_area("JSON 로드:", value=json.dumps(init_state, indent=4), key='json_input_text', height=150)
    st.button("시나리오 적용 (Load)", on_click=apply_json, use_container_width=True)

st.subheader(f"🏷️ Equipment Tag: **{st.session_state['tag_no']}**")

# =========================================================
# [C] 1. 유체 식별 및 물성치
# =========================================================
st.subheader("1. 유체 식별 및 물성치")
st.radio("튜브 측 유체 상(Phase) 선택", ["Liquid (뉴턴 유체 - 물, 오일 등)", "Slurry (비뉴턴 유체 - 고농도 혼합물)"], key='fluid_type', horizontal=True)

col_tube, col_shell = st.columns(2)
with col_tube:
    st.markdown("#### **Tube-side (Inner)**")
    st.text_input("유체 명칭", key='tube_fluid_name')
    st.number_input("혼합 밀도 (kg/m³)", key='t_rho')
    st.number_input("비열 (J/kg·K)", key='t_cp')
    st.number_input("열전도도 (W/m·K)", key='t_k')
    if "Liquid" in st.session_state['fluid_type']:
        st.number_input("동점성 계수 (cP)", format="%.2f", key='t_mu')
    else:
        st.selectbox("유변학 모델", ["Power-law (멱법칙)", "Bingham Plastic (빙햄 가소성)"], key='rheology_model')
        if "Bingham" in st.session_state['rheology_model']:
            st.number_input("항복 응력 (Pa)", key='tau_y')
            st.number_input("가소성 점도 (Pa·s)", format="%.4f", key='plastic_visc')
        else:
            st.number_input("점조도 지수 K (Pa·sⁿ)", format="%.4f", key='consistency_k')
            st.number_input("유동 지수 n", step=0.1, key='flow_index_n')

with col_shell:
    st.markdown("#### **Shell-side (Outer)**")
    st.text_input("유체 명칭", key='shell_fluid_name')
    st.number_input("밀도 (kg/m³)", key='s_rho')
    st.number_input("비열 (J/kg·K)", key='s_cp')
    st.number_input("열전도도 (W/m·K)", key='s_k')
    st.number_input("점도 (cP)", format="%.2f", key='s_mu')

st.markdown("---")

# =========================================================
# [D] 2. 공정 운전 조건 (에너지 수지 Estimation 연동)
# =========================================================
st.subheader("2. 공정 운전 조건 (Energy Balance)")

Q_kW = (st.session_state['m_hot'] / 3600.0) * (st.session_state['t_cp'] / 1000.0) * abs(st.session_state['T_hot_in'] - st.session_state['T_hot_out'])
delta_T_shell = abs(st.session_state['T_cold_out'] - st.session_state['T_cold_in'])
s_cp_kJ = st.session_state['s_cp'] / 1000.0
est_m_cold = (Q_kW * 3600.0) / (s_cp_kJ * max(0.1, delta_T_shell)) if delta_T_shell > 0 else 0.0
est_T_cold_out = st.session_state['T_cold_in'] + ((Q_kW * 3600.0) / (max(0.1, st.session_state['m_cold']) * s_cp_kJ))

col_pc1, col_pc2, col_pc3, col_pc4 = st.columns(4)
with col_pc1:
    st.number_input("Tube 유량 (kg/h)", step=100.0, key='m_hot')
    st.number_input("Shell 유량 (kg/h)", step=100.0, key='m_cold')
    st.caption(f"💡 필요 냉각 유량 추정치: **{est_m_cold:,.0f} kg/h**")
with col_pc2:
    st.number_input("Tube 입구 온도 (°C)", key='T_hot_in')
    st.number_input("Tube 목표 출구 온도 (°C)", key='T_hot_out')
    st.caption(f"🔥 Tube 열부하(Q): **{Q_kW:,.1f} kW**")
with col_pc3:
    st.number_input("Shell 입구 온도 (°C)", key='T_cold_in')
    st.number_input("Shell 목표 출구 온도 (°C)", key='T_cold_out')
    st.caption(f"💡 예상 출구 온도 추정치: **{est_T_cold_out:,.1f} °C**")
with col_pc4:
    st.number_input("Tube 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_tube')
    st.number_input("Shell 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_shell')

dT1 = st.session_state['T_hot_in'] - st.session_state['T_cold_out']
dT2 = st.session_state['T_hot_out'] - st.session_state['T_cold_in']
LMTD = (dT1 - dT2) / np.log(dT1 / dT2) if (dT1 != dT2 and dT1 > 0 and dT2 > 0) else (dT1 if dT1 > 0 else 1.0)

st.markdown("---")

# =========================================================
# [E] 3. 기하학적 설계 (직접 입력 및 가이드라인)
# =========================================================
st.subheader("3. 기하학적 설계 (직접 입력 및 가이드라인)")

col_g1, col_g2, col_g3, col_g4 = st.columns(4)

with col_g1:
    st.number_input("병렬 튜브 수 (N_p, 가닥)", 1, 50, step=1, key='N_p')
    st.number_input("튜브 외경 (d_o, mm)", 10.0, 100.0, step=0.1, key='d_o')
    # 튜브 외경 현실적 추천 가이드라인 추가
    st.caption("💡 추천: 일반 19.05 mm (3/4\"), 슬러리 25.4~38.1 mm (플러깅 방지)")
    
    st.number_input("튜브 두께 (t, mm)", 1.0, 10.0, step=0.1, key='t_thick')
    d_i = st.session_state['d_o'] - 2 * st.session_state['t_thick']
    
    mat_dict = {'Stainless Steel 316 (k=16)': 16.0, 'Titanium (k=22)': 22.0, 'Custom': st.session_state.get('tube_k_wall', 16.0)}
    selected_mat = st.selectbox("튜브 재질", list(mat_dict.keys()), key='tube_material')
    st.session_state['tube_k_wall'] = st.number_input("열전도도", value=mat_dict.get(selected_mat, 16.0)) if "Custom" in selected_mat else mat_dict[selected_mat]

with col_g2:
    rec_Dc = st.session_state['d_o'] * 10.0
    st.number_input("코일 중심 직경 (D_c, mm)", step=10.0, key='D_c')
    st.caption(f"💡 추천 최소값: **{rec_Dc:.1f} mm** (벤딩 파열 방지)")
    
    rec_mandrel = max(10.0, st.session_state['D_c'] - st.session_state['d_o'] - 10.0)
    st.number_input("Mandrel 외경 (D_m, mm)", step=5.0, key='D_mandrel')
    st.caption(f"💡 추천 최적값: **{rec_mandrel:.1f} mm** (내측 간섭 여유)")

with col_g3:
    rec_pitch = st.session_state['d_o'] * 1.25
    st.number_input("코일 피치 (p, mm)", step=1.0, key='pitch')
    st.caption(f"💡 추천 최소값: **{rec_pitch:.1f} mm** (외경의 1.25배)")
    
    rec_Ds = st.session_state['D_c'] + st.session_state['d_o'] + 40.0
    st.number_input("쉘 내경 (D_s, mm)", step=10.0, key='D_s')
    st.caption(f"💡 추천 최소값: **{rec_Ds:.1f} mm** (외부 클리어런스 확보)")

with col_g4:
    st.number_input("Tube 오염계수 R_fi", 0.0, 0.02, format="%.6f", key='R_fi')
    st.number_input("Shell 오염계수 R_fo", 0.0, 0.02, format="%.6f", key='R_fo')

# =========================================================
# [F] 4. 수력학 코어 연산 (백그라운드 선행 연산)
# =========================================================
# 이 부분의 연산 결과를 3번 섹션 하단 대시보드에서 쓰기 위해 조기 실행합니다.
t_mu_pa = st.session_state.get('t_mu', 1.0) / 1000.0
s_mu_pa = st.session_state.get('s_mu', 1.0) / 1000.0
curvature_ratio = d_i / st.session_state['D_c'] if st.session_state['D_c'] > 0 else 0

m_hot_per_tube = (st.session_state['m_hot'] / 3600.0) / max(1, st.session_state['N_p'])
A_c = np.pi * ((d_i / 1000.0) ** 2) / 4.0
v_tube = m_hot_per_tube / (st.session_state['t_rho'] * A_c) if A_c > 0 else 0

if "Liquid" in st.session_state['fluid_type']:
    Re = (st.session_state['t_rho'] * v_tube * (d_i / 1000.0)) / max(1e-6, t_mu_pa)
    Pr = (st.session_state['t_cp'] * t_mu_pa) / max(1e-6, st.session_state['t_k'])
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    f_c = (64.0 / max(Re, 1.0) * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)) if Re < Re_crit else (0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio))
    Nu_straight = 4.36 if Re < Re_crit else 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
else:
    n_val = st.session_state['flow_index_n'] if "Power" in st.session_state['rheology_model'] else 1.0
    K_val = st.session_state['consistency_k'] if "Power" in st.session_state['rheology_model'] else st.session_state['plastic_visc']
    D_m_tube = d_i / 1000.0
    term1 = st.session_state['t_rho'] * (v_tube ** (2.0 - n_val)) * (D_m_tube ** n_val)
    term2 = (8.0 ** (n_val - 1.0)) * max(K_val, 0.0001) * (((3.0 * n_val + 1.0) / (4.0 * n_val)) ** n_val)
    Re = term1 / term2 if term2 > 0 else 0.0
    mu_app = term1 / (Re * v_tube) if (Re * v_tube) > 0 else 0.001
    Pr = (st.session_state['t_cp'] * mu_app) / max(1e-6, st.session_state['t_k'])
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    f_c = (64.0 / max(Re, 1.0) * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)) if Re < Re_crit else (0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio))
    Nu_straight = 4.36 if Re < Re_crit else 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)

Nu_calc = Nu_straight * (1.0 + 3.5 * curvature_ratio)
h_i = (Nu_calc * st.session_state['t_k']) / (d_i / 1000.0)

m_cold_kg_s = st.session_state['m_cold'] / 3600.0
D_s_m = st.session_state['D_s'] / 1000.0
D_man_m = st.session_state['D_mandrel'] / 1000.0
d_o_m = st.session_state['d_o'] / 1000.0

A_annulus = (np.pi / 4.0) * (D_s_m**2 - D_man_m**2)
A_free_flow = A_annulus * 0.5 
v_shell = m_cold_kg_s / (st.session_state['s_rho'] * A_free_flow) if A_free_flow > 0 else 0.0

D_e_shell = D_s_m - D_man_m
Re_shell = (st.session_state['s_rho'] * v_shell * D_e_shell) / max(1e-6, s_mu_pa)
Pr_shell = (st.session_state['s_cp'] * s_mu_pa) / max(1e-6, st.session_state['s_k'])
Nu_shell = 0.33 * (max(Re_shell, 1.0) ** 0.6) * (Pr_shell ** 0.33)
h_o = (Nu_shell * st.session_state['s_k']) / d_o_m

R_wall = (d_o_m * np.log(st.session_state['d_o'] / max(1e-6, d_i))) / (2.0 * max(1e-6, st.session_state['tube_k_wall']))
U_calc = 1.0 / ((1.0 / max(h_o, 0.1)) + st.session_state['R_fo'] + R_wall + st.session_state['R_fi'] * (st.session_state['d_o'] / max(1e-6, d_i)) + (st.session_state['d_o'] / max(1e-6, d_i)) * (1.0 / max(h_i, 0.1)))

Area = (Q_kW * 1000.0) / (U_calc * LMTD) if LMTD > 0 else 0.0
Total_Tube_Length = Area / (np.pi * d_o_m) if d_o_m > 0 else 0.0
Length_per_Tube = Total_Tube_Length / max(1, st.session_state['N_p'])
Turns_per_Tube = Length_per_Tube / (np.pi * (st.session_state['D_c'] / 1000.0)) if st.session_state['D_c'] > 0 else 0.0

dp_tube_bar = (f_c * (Length_per_Tube / (d_i / 1000.0)) * (st.session_state['t_rho'] * (v_tube ** 2) / 2.0)) / 100000.0
L_shell_m = (Turns_per_Tube * (st.session_state['pitch'] / 1000.0))
f_s = 0.316 / (max(Re_shell, 1.0)**0.25) 
dp_shell_bar = (f_s * (L_shell_m / max(1e-6, D_e_shell)) * (st.session_state['s_rho'] * (v_shell ** 2) / 2.0)) / 100000.0

# =========================================================
# [G] 실시간 Bounding Box 표시 (섹션 3 하단)
# =========================================================
st.markdown("#### 📐 실시간 장비 예상 규격 (Estimated Bounding Box)")
st.info("💡 튜브 외경과 피치를 변경함에 따라 장비의 실제 크기가 어떻게 변하는지 직관적으로 확인하십시오.")

# 헤더 공간(입출구 노즐 여유)을 고려하여 총 높이는 코일 높이 + 2*D_s 로 보수적 산정
Estimated_Total_Height = L_shell_m + (2.0 * D_s_m) 
Footprint_Area = (np.pi / 4.0) * (D_s_m ** 2)

col_dim1, col_dim2, col_dim3, col_dim4 = st.columns(4)
col_dim1.metric("Shell 내부 직경 (D_s)", f"{st.session_state['D_s']:,.0f} mm")
col_dim2.metric("코일부 순수 높이 (L_shell)", f"{L_shell_m:,.2f} m")
# 장비 높이가 10m를 넘어가면 붉은색 경고 표시
if Estimated_Total_Height > 10.0:
    col_dim3.metric("🚨 예상 장비 총 높이", f"{Estimated_Total_Height:,.2f} m", delta="과도한 높이! 배관/수리 불가", delta_color="inverse")
else:
    col_dim3.metric("예상 장비 총 높이 (H_total)", f"{Estimated_Total_Height:,.2f} m", delta="안정적 구조", delta_color="normal")
col_dim4.metric("장비 바닥 면적 (Footprint)", f"{Footprint_Area:,.2f} m²")

st.markdown("---")

# =========================================================
# [H] 4. 상업용 데이터시트 및 수력학 결과 표출
# =========================================================
st.subheader("4. 열전달 및 수력학 검증 (Thermodynamics & Hydraulics)")
st.caption(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

datasheet_md = f"""
| **Item Tag No.** | **{st.session_state['tag_no']}** | **Type** | Helical Coil Heat Exchanger |
| :--- | :--- | :--- | :--- |
| **Performance Data** | | | |
| Heat Duty (kW) | {Q_kW:,.2f} | Overall U-value (W/m²K) | {U_calc:,.1f} |
| Required Total Area (m²)| {Area:,.2f} | LMTD (°C) | {LMTD:,.1f} |
| **Process Conditions** | **Tube Side (Inner)** | **Shell Side (Outer)** | |
| Fluid Name | **{st.session_state['tube_fluid_name']}** | **{st.session_state['shell_fluid_name']}** | |
| Total Flow Rate (kg/h) | {st.session_state['m_hot']:,.0f} | {st.session_state['m_cold']:,.0f} | |
| Temp. In / Out (°C) | {st.session_state['T_hot_in']} / {st.session_state['T_hot_out']} | {st.session_state['T_cold_in']} / {st.session_state['T_cold_out']} | |
| Viscosity (cP) | {st.session_state.get('t_mu', 'N/A')} | {st.session_state.get('s_mu', 'N/A')} | |
| Velocity (m/s) | {v_tube:.2f} (per tube) | {v_shell:.2f} (Annulus) | |
| Calc. Press. Drop (bar)| **{dp_tube_bar:.3f}** (Allow: {st.session_state['allowable_dp_tube']}) | **{dp_shell_bar:.3f}** (Allow: {st.session_state['allow
