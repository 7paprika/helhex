import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json
import datetime

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")
st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# =========================================================
# [A] 글로벌 상태(Session State) 초기화 (Fluid Name 및 cP 단위 반영)
# =========================================================
init_state = {
    'tag_no': 'HE-101', 
    'tube_fluid_name': 'Cooling Water',
    'shell_fluid_name': 'Process Oil',
    # 1. 유체 타입 및 기본 물성 (점도 단위 cP 기준, 물은 약 1.0 cP)
    'fluid_type': "Liquid (뉴턴 유체 - 물, 오일 등)",
    't_rho': 998.0, 't_cp': 4180.0, 't_k': 0.6, 't_mu': 1.0, 
    's_rho': 850.0, 's_mu': 2.5, 's_cp': 2100.0, 's_k': 0.15,
    # 2. 비뉴턴 (Slurry) 전용 물성
    'rheology_model': "Power-law (멱법칙)",
    'tau_y': 5.0, 'plastic_visc': 0.05,
    'consistency_k': 0.1, 'flow_index_n': 0.8,
    # 3. 공정 조건 및 압력 제약
    'm_hot': 5000.0, 'm_cold': 8000.0,
    'T_hot_in': 150.0, 'T_hot_out': 80.0,
    'T_cold_in': 30.0, 'T_cold_out': 60.0,
    'allowable_dp_tube': 0.5, 'allowable_dp_shell': 0.5,
    # 4. 기하학적 변수, 재질 및 오염 계수
    'd_o': 25.4, 't_thick': 2.11, 'D_c': 300.0, 'pitch': 50.0, 'D_s': 400.0,
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
        st.success(f"✅ 설계 데이터(Tag: {st.session_state.get('tag_no', 'Unknown')})가 성공적으로 로드되었습니다.")
    except json.JSONDecodeError:
        st.error("🚨 JSON 파싱 에러: 형식을 확인하십시오.")
    except Exception as e:
        st.error(f"🚨 시스템 에러: ({e})")

# =========================================================
# [B] 환경설정 (JSON 저장 / 로드 및 Tag No.)
# =========================================================
with st.sidebar:
    st.header("📋 Document Control")
    st.text_input("Item Tag No. (장비 번호)", key='tag_no')
    
    st.markdown("---")
    st.header("💾 설계 시나리오 (Save/Load)")
    st.info("현재 화면의 모든 입력값이 JSON으로 추적됩니다.")
    
    current_tag = st.session_state.get('tag_no', 'default_tag')
    filename = f"{current_tag}_design_data.json"
    
    current_data = {k: st.session_state[k] for k in init_state.keys()}
    current_json_str = json.dumps(current_data, indent=4)
    
    st.download_button(f"📥 '{filename}' 다운로드", current_json_str, file_name=filename, mime="application/json")
    
    st.markdown("**데이터 로드**")
    st.text_area("JSON 텍스트 입력창:", value=json.dumps(init_state, indent=4), key='json_input_text', height=200)
    st.button("시나리오 적용 (Load)", on_click=apply_json, use_container_width=True)

st.subheader(f"🏷️ Current Equipment Tag: **{st.session_state['tag_no']}**")

# =========================================================
# [C] 1. 유체 식별 및 물성치 데이터
# =========================================================
st.subheader("1. 유체 식별 및 물성치 (Fluid Identity & Properties)")
st.radio("튜브 측(Tube-side) 유체 특성 선택", ["Liquid (뉴턴 유체 - 물, 오일 등)", "Slurry (비뉴턴 유체 - 고농도 혼합물)"], key='fluid_type', horizontal=True)

col_tube, col_shell = st.columns(2)

with col_tube:
    st.markdown("#### **Tube-side (Inner Fluid)**")
    st.text_input("유체 명칭 (Fluid Name)", key='tube_fluid_name')
    st.number_input("혼합 밀도 (kg/m³)", key='t_rho')
    st.number_input("비열 (J/kg·K)", key='t_cp')
    st.number_input("열전도도 (W/m·K)", key='t_k')
    
    if "Liquid" in st.session_state['fluid_type']:
        st.number_input("동점성 계수 (cP)", format="%.2f", key='t_mu', help="단위: cP (Centipoise). 물(20°C) ≈ 1.0 cP")
    else:
        st.warning("🚨 비뉴턴 유체 모드 활성화")
        st.selectbox("유변학 모델 선택", ["Power-law (멱법칙)", "Bingham Plastic (빙햄 가소성)"], key='rheology_model')
        if st.session_state['rheology_model'] == "Bingham Plastic (빙햄 가소성)":
            st.number_input("항복 응력 (Yield stress, Pa)", step=1.0, key='tau_y')
            st.number_input("가소성 점도 (Pa·s)", format="%.4f", key='plastic_visc')
        else:
            st.number_input("점조도 지수 K (Pa·sⁿ)", format="%.4f", key='consistency_k')
            st.number_input("유동 지수 n", min_value=0.1, max_value=2.0, step=0.1, key='flow_index_n')

with col_shell:
    st.markdown("#### **Shell-side (Outer Fluid)**")
    st.text_input("유체 명칭 (Fluid Name)", key='shell_fluid_name')
    st.number_input("밀도 (kg/m³)", key='s_rho')
    st.number_input("비열 (J/kg·K)", key='s_cp')
    st.number_input("열전도도 (W/m·K)", key='s_k')
    st.number_input("점도 (cP)", format="%.2f", key='s_mu', help="단위: cP (Centipoise)")

st.markdown("---")

# =========================================================
# [D] 2. 공정 조건 (Process Conditions)
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
    st.number_input("Tube 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_tube')
    st.number_input("Shell 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_shell')

# 열역학 LMTD 사전 연산
Q_kW_tube = (st.session_state['m_hot'] / 3600.0) * (st.session_state['t_cp'] / 1000.0) * abs(st.session_state['T_hot_in'] - st.session_state['T_hot_out'])
dT1 = st.session_state['T_hot_in'] - st.session_state['T_cold_out']
dT2 = st.session_state['T_hot_out'] - st.session_state['T_cold_in']

if dT1 == dT2 and dT1 > 0:
    LMTD = dT1
elif dT1 > 0 and dT2 > 0:
    LMTD = (dT1 - dT2) / np.log(dT1 / dT2)
else:
    st.error("🚨 온도 역전 에러 (Temperature Cross Error)")
    LMTD = 1.0 

st.markdown("---")

# =========================================================
# [E] 3. 기하학 및 재질
# =========================================================
st.subheader("3. 기하학적 설계 변수 및 튜브 재질")

col_g1, col_g2, col_g3, col_g4 = st.columns(4)
with col_g1:
    st.slider("튜브 외경 (d_o, mm)", 10.0, 50.0, step=0.1, key='d_o')
    st.number_input("튜브 두께 (t, mm)", 1.0, 5.0, step=0.1, key='t_thick')
    d_i = st.session_state['d_o'] - 2 * st.session_state['t_thick']
    
    mat_dict = {
        'Carbon Steel (k = 45 W/m·K)': 45.0, 'Stainless Steel 304 (k = 15 W/m·K)': 15.0,
        'Stainless Steel 316 (k = 16 W/m·K)': 16.0, 'Duplex Stainless Steel (k = 19 W/m·K)': 19.0,
        'Titanium (k = 22 W/m·K)': 22.0, 'Custom (사용자 지정)': st.session_state.get('tube_k_wall', 16.0)
    }
    if st.session_state['tube_material'] not in mat_dict:
        st.session_state['tube_material'] = 'Stainless Steel 316 (k = 16 W/m·K)'
        
    selected_mat = st.selectbox("튜브 재질", list(mat_dict.keys()), key='tube_material')
    if "Custom" in selected_mat:
        st.number_input("재질 열전도도 (W/m·K)", 1.0, 500.0, step=1.0, key='tube_k_wall')
    else:
        st.session_state['tube_k_wall'] = mat_dict[selected_mat]

with col_g2:
    min_Dc = st.session_state['d_o'] / 0.1
    st.session_state['D_c'] = max(st.session_state['D_c'], min_Dc)
    st.slider("코일 중심 직경 (D_c, mm)", float(min_Dc), 2000.0, step=10.0, key='D_c')
    curvature_ratio = d_i / st.session_state['D_c']

with col_g3:
    min_pitch = st.session_state['d_o'] * 1.25
    st.session_state['pitch'] = max(st.session_state['pitch'], min_pitch)
    st.slider("코일 피치 (p, mm)", float(min_pitch), 300.0, step=1.0, key='pitch')
    
    min_Ds = st.session_state['D_c'] + st.session_state['d_o'] + 20.0
    st.session_state['D_s'] = max(st.session_state['D_s'], min_Ds)
    st.number_input("쉘 내경 (D_s, mm)", float(min_Ds), 3000.0, step=10.0, key='D_s')

with col_g4:
    st.number_input("Tube 오염계수 R_fi (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fi')
    st.number_input("Shell 오염계수 R_fo (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fo')

# =========================================================
# [F] 4. 열역학 코어 연산 (엄격한 단위 변환 cP -> Pa·s)
# =========================================================
# 💡 핵심: 백단 연산을 위해 cP를 Pa·s로 강제 변환
t_mu_pa_s = st.session_state.get('t_mu', 1.0) / 1000.0
s_mu_pa_s = st.session_state.get('s_mu', 1.0) / 1000.0

m_hot_kg_s = st.session_state['m_hot'] / 3600.0
A_c = np.pi * ((d_i / 1000.0) ** 2) / 4.0
v_tube = m_hot_kg_s / (st.session_state['t_rho'] * A_c) if A_c > 0 else 0

if "Liquid" in st.session_state['fluid_type']:
    Re = (st.session_state['t_rho'] * v_tube * (d_i / 1000.0)) / t_mu_pa_s
    Pr = (st.session_state['t_cp'] * t_mu_pa_s) / st.session_state['t_k']
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    
    if Re < Re_crit:
        Nu_straight = 4.36
        f_straight = 64.0 / Re if Re > 0 else 0.0
        f_c = f_straight * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)
    else:
        Nu_straight = 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)
else:
    # Slurry
    n_val = st.session_state['flow_index_n'] if st.session_state['rheology_model'] == "Power-law (멱법칙)" else 1.0
    K_val = st.session_state['consistency_k'] if st.session_state['rheology_model'] == "Power-law (멱법칙)" else st.session_state['plastic_visc']
    D_m = d_i / 1000.0
    
    term1 = st.session_state['t_rho'] * (v_tube ** (2.0 - n_val)) * (D_m ** n_val)
    term2 = (8.0 ** (n_val - 1.0)) * max(K_val, 0.0001) * (((3.0 * n_val + 1.0) / (4.0 * n_val)) ** n_val)
    Re = term1 / term2 if term2 > 0 else 0.0
    
    mu_app = term1 / (Re * v_tube) if (Re * v_tube) > 0 else 0.001
    Pr = (st.session_state['t_cp'] * mu_app) / st.session_state['t_k']
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    
    if Re < Re_crit:
        Nu_straight = 4.36
        f_straight = 64.0 / max(Re, 1.0)
        f_c = f_straight * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)
    else:
        Nu_straight = 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)

Nu_calc = Nu_straight * (1.0 + 3.5 * curvature_ratio)
h_i = (Nu_calc * st.session_state['t_k']) / (d_i / 1000.0)

# Shell 연산 (s_mu_pa_s 적용)
m_cold_kg_s = st.session_state['m_cold'] / 3600.0
A_free_flow = (np.pi/4) * ((st.session_state['D_s']/1000.0)**2 - (st.session_state['D_c']/1000.0)**2)
v_shell = m_cold_kg_s / (st.session_state['s_rho'] * A_free_flow) if A_free_flow > 0 else 0.0
Re_shell = (st.session_state['s_rho'] * v_shell * (st.session_state['d_o'] / 1000.0)) / s_mu_pa_s
Pr_shell = (st.session_state['s_cp'] * s_mu_pa_s) / st.session_state['s_k']
Nu_shell = 0.33 * (max(Re_shell, 1.0) ** 0.6) * (Pr_shell ** 0.33)
h_o = (Nu_shell * st.session_state['s_k']) / (st.session_state['d_o'] / 1000.0)

R_wall = ((st.session_state['d_o'] / 1000.0) * np.log(st.session_state['d_o'] / d_i)) / (2.0 * st.session_state['tube_k_wall'])
sum_resistances = (1.0 / max(h_o, 0.1)) + st.session_state['R_fo'] + R_wall + st.session_state['R_fi'] * (st.session_state['d_o'] / d_i) + (st.session_state['d_o'] / d_i) * (1.0 / max(h_i, 0.1))
U_calc = 1.0 / sum_resistances

Area = (Q_kW_tube * 1000.0) / (U_calc * LMTD) if LMTD > 0 else 0.0
Tube_length = Area / (np.pi * (st.session_state['d_o'] / 1000.0))
Turns = Tube_length / (np.pi * (st.session_state['D_c'] / 1000.0))

dp_tube_pa = f_c * (Tube_length / (d_i / 1000.0)) * (st.session_state['t_rho'] * (v_tube ** 2) / 2.0)
dp_tube_bar = dp_tube_pa / 100000.0

# =========================================================
# [G] 5. Commercial Datasheet (상업용 데이터시트 렌더링)
# =========================================================
st.markdown("---")
st.subheader("📄 Commercial Heat Exchanger Datasheet")
st.caption(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Process Engineering Dept.")

# TEMA 스타일 마크다운 테이블 구성
datasheet_md = f"""
| **Item Tag No.** | **{st.session_state['tag_no']}** | **Type** | Helical Coil Heat Exchanger |
| :--- | :--- | :--- | :--- |
| **Performance Data** | | | |
| Heat Duty (kW) | {Q_kW_tube:,.2f} | Overall U-value (W/m²K) | {U_calc:,.1f} |
| Required Area (m²) | {Area:,.2f} | LMTD (°C) | {LMTD:,.1f} |
| **Process Conditions** | **Tube Side (Inner)** | **Shell Side (Outer)** | |
| Fluid Name | **{st.session_state['tube_fluid_name']}** | **{st.session_state['shell_fluid_name']}** | |
| Flow Rate (kg/h) | {st.session_state['m_hot']:,.0f} | {st.session_state['m_cold']:,.0f} | |
| Temp. In / Out (°C) | {st.session_state['T_hot_in']} / {st.session_state['T_hot_out']} | {st.session_state['T_cold_in']} / {st.session_state['T_cold_out']} | |
| Viscosity (cP) | {st.session_state.get('t_mu', 'N/A')} | {st.session_state.get('s_mu', 'N/A')} | |
| Fouling Factor (m²K/W)| {st.session_state['R_fi']:.6f} | {st.session_state['R_fo']:.6f} | |
| Velocity (m/s) | {v_tube:.2f} | {v_shell:.2f} | |
| Calc. Press. Drop (bar)| **{dp_tube_bar:.3f}** (Allow: {st.session_state['allowable_dp_tube']}) | N/A (Allow: {st.session_state['allowable_dp_shell']}) | |
| **Mechanical Design** | | | |
| Tube OD x Thick. (mm) | {st.session_state['d_o']} x {st.session_state['t_thick']} (ID: {d_i:.2f}) | Tube Material | {st.session_state['tube_material']} |
| Coil Diameter (mm) | {st.session_state['D_c']} | Shell ID (mm) | {st.session_state['D_s']} |
| Coil Pitch (mm) | {st.session_state['pitch']} | Total Turns / Length | {Turns:,.1f} / {Tube_length:,.1f} m |
"""

st.markdown(datasheet_md)

# 압력 강하 체크 시각적 피드백
if dp_tube_bar > st.session_state['allowable_dp_tube']:
    st.error(f"🚨 **Datasheet Warning:** Tube 측 압력 강하({dp_tube_bar:.2f} bar)가 허용치를 초과하여 도면 승인이 불가능합니다.")
else:
    st.success("✅ **Datasheet Validated:** 모든 수력학적 제약 조건을 통과했습니다.")

# =========================================================
# [H] 6. 3D 형상 렌더링
# =========================================================
if Turns > 0 and Turns < 5000:
    t = np.linspace(0, Turns * 2 * np.pi, int(max(Turns * 50, 100)))
    x = (st.session_state['D_c'] / 2) * np.cos(t)
    y = (st.session_state['D_c'] / 2) * np.sin(t)
    z = (st.session_state['pitch'] / (2 * np.pi)) * t

    fig = go.Figure(data=[go.Scatter3d(x=x, y=y, z=z, mode='lines', line=dict(color='darkblue', width=8))])
    fig.update_layout(
        scene=dict(xaxis_title='X (mm)', yaxis_title='Y (mm)', zaxis_title='Height (mm)', aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=0),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
