import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json
import datetime

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")
st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# =========================================================
# [A] 글로벌 상태(Session State) 초기화 (Full Spec)
# =========================================================
init_state = {
    'tag_no': 'HE-101', 
    'tube_fluid_name': 'Process Slurry',
    'shell_fluid_name': 'Cooling Water',
    # 1. 유체 물성 (단위: cP)
    'fluid_type': "Liquid (뉴턴 유체 - 물, 오일 등)",
    't_rho': 998.0, 't_cp': 4180.0, 't_k': 0.6, 't_mu': 1.0, 
    's_rho': 998.0, 's_mu': 1.0, 's_cp': 4180.0, 's_k': 0.6,
    'rheology_model': "Power-law (멱법칙)",
    'tau_y': 5.0, 'plastic_visc': 0.05,
    'consistency_k': 0.1, 'flow_index_n': 0.8,
    # 2. 공정 운전 조건
    'm_hot': 5000.0, 'm_cold': 8000.0,
    'T_hot_in': 150.0, 'T_hot_out': 80.0,
    'T_cold_in': 30.0, 'T_cold_out': 60.0,
    'allowable_dp_tube': 1.5, 'allowable_dp_shell': 0.5,
    # 3. 기하학적 변수 (병렬 튜브 N_p, Mandrel D_m)
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
    st.text_input("Item Tag No. (장비 번호)", key='tag_no')
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
# [C] 1. 유체 식별 및 물성치 (단위: cP 주의, 툴팁 취소선 버그 수정)
# =========================================================
st.subheader("1. 유체 식별 및 물성치")
st.radio("튜브 측 유체 상(Phase) 선택", ["Liquid (뉴턴 유체 - 물, 오일 등)", "Slurry (비뉴턴 유체 - 고농도 혼합물)"], key='fluid_type', horizontal=True)

col_tube, col_shell = st.columns(2)
with col_tube:
    st.markdown("#### **Tube-side (Inner)**")
    st.text_input("유체 명칭", key='tube_fluid_name')
    st.number_input("혼합 밀도 (kg/m³)", key='t_rho', help="일반 액체: 700 - 1000, 슬러리: 1100 - 1800 이상")
    st.number_input("비열 (J/kg·K)", key='t_cp', help="물: 4180, 일반 오일류: 1800 - 2400")
    st.number_input("열전도도 (W/m·K)", key='t_k', help="물: 0.6, 일반 오일류: 0.1 - 0.2")
    if "Liquid" in st.session_state['fluid_type']:
        st.number_input("동점성 계수 (cP)", format="%.2f", key='t_mu', help="물(20°C): 1.0 cP, 경질유: 2.0 - 10.0")
    else:
        st.selectbox("유변학 모델", ["Power-law (멱법칙)", "Bingham Plastic (빙햄 가소성)"], key='rheology_model')
        if st.session_state['rheology_model'] == "Bingham Plastic (빙햄 가소성)":
            st.number_input("항복 응력 (Pa)", key='tau_y', help="펄프/고농도 슬러리: 5 - 50 Pa")
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
# [D] 2. 공정 운전 조건 (툴팁 취소선 버그 수정)
# =========================================================
st.subheader("2. 공정 운전 조건")
col_pc1, col_pc2, col_pc3, col_pc4 = st.columns(4)
with col_pc1:
    st.number_input("Tube 유량 (kg/h)", step=100.0, key='m_hot')
    st.number_input("Shell 유량 (kg/h)", step=100.0, key='m_cold')
with col_pc2:
    st.number_input("Tube 입구 온도 (°C)", key='T_hot_in')
    st.number_input("Tube 목표 출구 온도 (°C)", key='T_hot_out')
with col_pc3:
    st.number_input("Shell 입구 온도 (°C)", key='T_cold_in')
    st.number_input("Shell 목표 출구 온도 (°C)", key='T_cold_out')
with col_pc4:
    st.number_input("Tube 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_tube', help="TEMA 가이드: 0.5 - 0.7 bar 권장")
    st.number_input("Shell 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_shell', help="코일 외부 유동 특성상 0.3 - 0.5 bar 이내 설계 요망 (Baffle 없음)")

Q_kW = (st.session_state['m_hot'] / 3600.0) * (st.session_state['t_cp'] / 1000.0) * abs(st.session_state['T_hot_in'] - st.session_state['T_hot_out'])
dT1 = st.session_state['T_hot_in'] - st.session_state['T_cold_out']
dT2 = st.session_state['T_hot_out'] - st.session_state['T_cold_in']
LMTD = (dT1 - dT2) / np.log(dT1 / dT2) if (dT1 != dT2 and dT1 > 0 and dT2 > 0) else (dT1 if dT1 > 0 else 1.0)

st.markdown("---")

# =========================================================
# [E] 3. 기하학, 재질 및 핵심 부속 (툴팁 취소선 버그 수정)
# =========================================================
st.subheader("3. 기하학적 설계 (병렬 튜브 및 Mandrel 포함)")

col_g1, col_g2, col_g3, col_g4 = st.columns(4)
with col_g1:
    st.number_input("병렬 튜브 수 (N_p, 가닥)", 1, 50, step=1, key='N_p', help="유량을 N_p개로 분산시켜 내부 ΔP를 낮춥니다. 3D 상에서 색상 구분됨.")
    st.slider("튜브 외경 (d_o, mm)", 10.0, 50.0, step=0.1, key='d_o', help="표준: 19.05 mm 또는 25.4 mm")
    st.number_input("튜브 두께 (t, mm)", 1.0, 5.0, step=0.1, key='t_thick', help="BWG 14 (2.11 mm) 또는 BWG 16 (1.65 mm)")
    d_i = st.session_state['d_o'] - 2 * st.session_state['t_thick']
    
    mat_dict = {'Stainless Steel 316 (k = 16 W/m·K)': 16.0, 'Titanium (k = 22 W/m·K)': 22.0, 'Custom': st.session_state.get('tube_k_wall', 16.0)}
    selected_mat = st.selectbox("튜브 재질", list(mat_dict.keys()), key='tube_material')
    st.session_state['tube_k_wall'] = st.number_input("열전도도", value=mat_dict.get(selected_mat, 16.0)) if "Custom" in selected_mat else mat_dict[selected_mat]

with col_g2:
    st.slider("코일 중심 직경 (D_c, mm)", float(st.session_state['d_o']*5), 2000.0, step=10.0, key='D_c')
    curvature_ratio = d_i / st.session_state['D_c']
    
    # Mandrel 자동 계산
    max_mandrel = st.session_state['D_c'] - st.session_state['d_o']
    rec_mandrel = max(10.0, max_mandrel - 10.0)
    st.session_state['D_mandrel'] = min(st.session_state['D_mandrel'], max_mandrel)
    st.number_input("Mandrel 외경 (D_m, mm)", 10.0, float(max_mandrel), value=float(rec_mandrel), key='D_mandrel', help="코일 내측(D_c - d_o)보다 약간 작게 설계.")

with col_g3:
    st.slider("코일 피치 (p, mm)", float(st.session_state['d_o']*1.25), 300.0, step=1.0, key='pitch', help="최소 외경의 1.25배 이상")
    min_Ds = st.session_state['D_c'] + st.session_state['d_o'] + 10.0
    st.session_state['D_s'] = max(st.session_state['D_s'], min_Ds)
    st.number_input("쉘 내경 (D_s, mm)", float(min_Ds), 3000.0, step=10.0, key='D_s', help="코일 외경 대비 최소 20 - 50 mm 여유 공간 요망.")

with col_g4:
    R_fi_help = "청정수: 0.0001, 해수: 0.0007, 슬러리: 0.0010 - 0.0020"
    st.number_input("Tube 오염계수 R_fi (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fi', help=R_fi_help)
    
    R_fo_help = "가스: 0.0004, 오일: 0.0015 - 0.0025\n* 쉘 측은 세척 불가로 보수적 접근 요망."
    st.number_input("Shell 오염계수 R_fo (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fo', help=R_fo_help)

# =========================================================
# [F] 4. 수력학 코어 연산 (N_p 분산 및 Shell ΔP)
# =========================================================
t_mu_pa = st.session_state.get('t_mu', 1.0) / 1000.0
s_mu_pa = st.session_state.get('s_mu', 1.0) / 1000.0

m_hot_per_tube = (st.session_state['m_hot'] / 3600.0) / st.session_state['N_p']
A_c = np.pi * ((d_i / 1000.0) ** 2) / 4.0
v_tube = m_hot_per_tube / (st.session_state['t_rho'] * A_c) if A_c > 0 else 0

if "Liquid" in st.session_state['fluid_type']:
    Re = (st.session_state['t_rho'] * v_tube * (d_i / 1000.0)) / t_mu_pa
    Pr = (st.session_state['t_cp'] * t_mu_pa) / st.session_state['t_k']
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    f_c = (64.0 / Re * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)) if Re < Re_crit else (0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio))
    Nu_straight = 4.36 if Re < Re_crit else 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
else:
    n_val = st.session_state['flow_index_n'] if "Power" in st.session_state['rheology_model'] else 1.0
    K_val = st.session_state['consistency_k'] if "Power" in st.session_state['rheology_model'] else st.session_state['plastic_visc']
    D_m_tube = d_i / 1000.0
    term1 = st.session_state['t_rho'] * (v_tube ** (2.0 - n_val)) * (D_m_tube ** n_val)
    term2 = (8.0 ** (n_val - 1.0)) * max(K_val, 0.0001) * (((3.0 * n_val + 1.0) / (4.0 * n_val)) ** n_val)
    Re = term1 / term2 if term2 > 0 else 0.0
    mu_app = term1 / (Re * v_tube) if (Re * v_tube) > 0 else 0.001
    Pr = (st.session_state['t_cp'] * mu_app) / st.session_state['t_k']
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
Re_shell = (st.session_state['s_rho'] * v_shell * D_e_shell) / s_mu_pa
Pr_shell = (st.session_state['s_cp'] * s_mu_pa) / st.session_state['s_k']
Nu_shell = 0.33 * (max(Re_shell, 1.0) ** 0.6) * (Pr_shell ** 0.33)
h_o = (Nu_shell * st.session_state['s_k']) / d_o_m

R_wall = (d_o_m * np.log(st.session_state['d_o'] / d_i)) / (2.0 * st.session_state['tube_k_wall'])
U_calc = 1.0 / ((1.0 / max(h_o, 0.1)) + st.session_state['R_fo'] + R_wall + st.session_state['R_fi'] * (st.session_state['d_o'] / d_i) + (st.session_state['d_o'] / d_i) * (1.0 / max(h_i, 0.1)))

Area = (Q_kW * 1000.0) / (U_calc * LMTD) if LMTD > 0 else 0.0
Total_Tube_Length = Area / (np.pi * d_o_m)
Length_per_Tube = Total_Tube_Length / st.session_state['N_p']
Turns_per_Tube = Length_per_Tube / (np.pi * (st.session_state['D_c'] / 1000.0))

dp_tube_bar = (f_c * (Length_per_Tube / (d_i / 1000.0)) * (st.session_state['t_rho'] * (v_tube ** 2) / 2.0)) / 100000.0
L_shell = Turns_per_Tube * (st.session_state['pitch'] / 1000.0)
f_s = 0.316 / (max(Re_shell, 1.0)**0.25) 
dp_shell_bar = (f_s * (L_shell / D_e_shell) * (st.session_state['s_rho'] * (v_shell ** 2) / 2.0)) / 100000.0

# =========================================================
# [G] 5. 상업용 데이터시트 (Datasheet)
# =========================================================
st.markdown("---")
st.subheader("📄 Commercial HTHE Datasheet")
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
| Viscosity (cP) | {st.session_state.get('t_mu', 'N/A')} | {st.session_state.get('s_mu', 'N/A')} | |
| Velocity (m/s) | {v_tube:.2f} (per tube) | {v_shell:.2f} (Annulus) | |
| Calc. Press. Drop (bar)| **{dp_tube_bar:.3f}** (Allow: {st.session_state['allowable_dp_tube']}) | **{dp_shell_bar:.3f}** (Allow: {st.session_state['allowable_dp_shell']}) | |
| **Mechanical Design** | | | |
| Tube OD x Thick. (mm) | {st.session_state['d_o']} x {st.session_state['t_thick']} | Tube Material | {st.session_state['tube_material']} |
| Parallel Coils (N_p) | **{st.session_state['N_p']} ea** | Coil Pitch (mm) | {st.session_state['pitch']} |
| Coil Center Dia. (mm) | {st.session_state['D_c']} | Shell ID / Mandrel OD | {st.session_state['D_s']} mm / {st.session_state['D_mandrel']} mm |
| Turns per Tube | {Turns_per_Tube:,.1f} | Length per Tube (m) | {Length_per_Tube:,.1f} |
"""
st.markdown(datasheet_md)

err_msg = []
if dp_tube_bar > st.session_state['allowable_dp_tube']: err_msg.append(f"Tube 측 ΔP 초과 ({dp_tube_bar:.2f} bar)")
if dp_shell_bar > st.session_state['allowable_dp_shell']: err_msg.append(f"Shell 측 ΔP 초과 ({dp_shell_bar:.2f} bar)")

if err_msg:
    st.error("🚨 **Datasheet Warning:** " + " / ".join(err_msg) + " -> N_p 수를 늘리거나 직경 조정을 고려하십시오.")
else:
    st.success("✅ **Datasheet Validated:** 모든 수력학적 제약 조건을 통과했습니다.")

# =========================================================
# [H] 6. 3D 형상 렌더링 (**제작 이해도를 위한 투명도 및 노즐/지지대 추가**)
# =========================================================
st.markdown("---")
st.subheader("5. 3D 코일 형상 (Schematic Representation - 제작 및 배관 인터페이스 확인)")
st.info("💡 **Engineer Note:** Mandrel(반투명 그레이)과 Shell(초반투명 블루)을 시각화하여 간섭 여부를 확인하십시오. 도식적인 노즐 위치와 코일 지지대를 추가했습니다.")

if Turns_per_Tube > 0 and Turns_per_Tube < 2000:
    fig = go.Figure()
    
    # 기본 변수
    N_p = st.session_state['N_p']
    turns = Turns_per_Tube
    d_c = st.session_state['D_c']
    p = st.session_state['pitch']
    t_max = turns * 2 * np.pi
    
    t_base = np.linspace(0, t_max, int(max(turns * 60, 150)))
    z = (p / (2 * np.pi)) * t_base
    coil_height = max(z)
    
    # 1. 병렬 코일 렌더링 (색상 구분 유지)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    for i in range(N_p):
        angle_offset = i * (2 * np.pi / N_p)
        x = (d_c / 2) * np.cos(t_base + angle_offset)
        y = (d_c / 2) * np.sin(t_base + angle_offset)
        
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='lines',
            line=dict(color=colors[i % len(colors)], width=6),
            name=f'Tube-side Coil {i+1}'
        ))
        
    # 2. Mandrel 가이드라인 (투명도 그레이 유지)
    z_surf = np.linspace(0, coil_height, 20)
    theta_surf = np.linspace(0, 2*np.pi, 25)
    theta_grid, z_grid = np.meshgrid(theta_surf, z_surf)
    
    # Mandrel (opacity 0.2 -> 0.15로 하향하여 가독성 증대)
    x_man = (st.session_state['D_mandrel'] / 2) * np.cos(theta_grid)
    y_man = (st.session_state['D_mandrel'] / 2) * np.sin(theta_grid)
    fig.add_trace(go.Surface(
        x=x_man, y=y_man, z=z_grid, 
        opacity=0.15, colorscale='Greys', showscale=False, 
        name='Mandrel', hoverinfo='skip'
    ))
    
    # 3. 쉘(Shell) 추가 (가장 높은 투명도 블루)
    x_shell = (st.session_state['D_s'] / 2) * np.cos(theta_grid)
    y_shell = (st.session_state['D_s'] / 2) * np.sin(theta_grid)
    fig.add_trace(go.Surface(
        x=x_shell, y=y_shell, z=z_grid, 
        opacity=0.08, colorscale='Blues', showscale=False, 
        name='Shell', hoverinfo='skip'
    ))
    
    # 4. [추가] 유체 입/출구 노즐 도식적 표현 (Nozzles)
    # 노즐 크기는 코일 크기에 비례하여 도식적으로 설정
    noz_r = d_c / 10.0
    noz_h = st.session_state['d_o'] * 3.0
    
    # Tube-side Inlet (Top, Red Cylinder)
    st_angle = 0
    in_x = (d_c / 2) * np.cos(st_angle)
    in_y = (d_c / 2) * np.sin(st_angle)
    fig.add_trace(go.Scatter3d(
        x=[in_x, in_x], y=[in_y, in_y], z=[coil_height, coil_height + noz_h],
        mode='lines', line=dict(color='red', width=12), name='Tube Inlet'
    ))
    
    # Tube-side Outlet (Bottom, Red Cylinder)
    end_angle = t_max % (2 * np.pi)
    out_x = (d_c / 2) * np.cos(end_angle)
    out_y = (d_c / 2) * np.sin(end_angle)
    fig.add_trace(go.Scatter3d(
        x=[out_x, out_x], y=[out_y, out_y], z=[0, -noz_h],
        mode='lines', line=dict(color='red', width=12), name='Tube Outlet'
    ))
    
    # Shell-side Inlet (Bottom side, Blue Cylinder)
    sh_in_r = st.session_state['D_s'] / 2.0
    fig.add_trace(go.Scatter3d(
        x=[sh_in_r, sh_in_r + noz_h], y=[0, 0], z=[p/2.0, p/2.0],
        mode='lines', line=dict(color='blue', width=12), name='Shell Inlet'
    ))
    
    # Shell-side Outlet (Top side, Blue Cylinder)
    fig.add_trace(go.Scatter3d(
        x=[-sh_in_r, -sh_in_r - noz_h], y=[0, 0], z=[coil_height - p/2.0, coil_height - p/2.0],
        mode='lines', line=dict(color='blue', width=12), name='Shell Outlet'
    ))
    
    # 5. [추가] 코일 지지대 (Support Structure - 도식적 원기둥 바)
        # 5. [추가] 코일 지지대 (Support Structure - 도식적 원기둥 바)
    sup_r = noz_r / 2.0
    sup_lx = (st.session_state['D_mandrel'] / 2.0)
    sup_rx = (st.session_state['D_s'] / 2.0)
    
    supports_angles = [0, np.pi/2, np.pi, 3*np.pi/2]
    support_levels = [coil_height * 0.25, coil_height * 0.5, coil_height * 0.75]
    
    # 수정된 부분: 네이티브 Boolean 플래그 도입 및 부동소수점 비교 제거
    show_support_legend = True 
    
    for lvl in support_levels:
        for ang in supports_angles:
            s_x = sup_lx * np.cos(ang)
            s_y = sup_lx * np.sin(ang)
            e_x = sup_rx * np.cos(ang)
            e_y = sup_rx * np.sin(ang)
            
            fig.add_trace(go.Scatter3d(
                x=[s_x, e_x], y=[s_y, e_y], z=[lvl, lvl],
                mode='lines', line=dict(color='black', width=4), 
                name='Coil Support', hoverinfo='skip', 
                showlegend=show_support_legend
            ))
            # 첫 번째 지지대를 그린 후에는 레전드 표출을 끕니다.
            show_support_legend = False

    fig.update_layout(
        scene=dict(xaxis_title='X (mm)', yaxis_title='Y (mm)', zaxis_title='Height (mm)', aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=0),
        height=700,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("형상을 렌더링할 수 없습니다. 온도 조건(Temperature Cross) 또는 물리적 변수를 다시 확인하십시오.")
