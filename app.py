import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")
st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# =========================================================
# [A] 글로벌 상태(Session State) 초기화 (모든 변수 + Tag No.)
# =========================================================
init_state = {
    'tag_no': 'HE-101', 
    # 1. 유체 타입 및 기본 물성
    'fluid_type': "Liquid (뉴턴 유체 - 물, 오일 등)",
    't_rho': 998.0, 't_cp': 4180.0, 't_k': 0.6, 't_mu': 0.001,
    's_rho': 998.0, 's_mu': 0.001, 's_cp': 4180.0, 's_k': 0.6,
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
        st.error("🚨 JSON 파싱 에러: 따옴표나 쉼표 등 형식을 확인하십시오.")
    except Exception as e:
        st.error(f"🚨 시스템 에러: 데이터 로드 중 문제 발생 ({e})")

# =========================================================
# [B] 환경설정 (JSON 저장 / 로드 및 Tag No.) -> 사이드바
# =========================================================
with st.sidebar:
    st.header("📋 Document Control")
    st.text_input("Item Tag No. (장비 번호)", key='tag_no', help="예: HE-101, E-205A. P&ID 상의 고유 식별 번호를 입력하세요.")
    
    st.markdown("---")
    st.header("💾 설계 시나리오 (Save/Load)")
    st.info("현재 화면의 모든 입력값이 JSON으로 추적됩니다.")
    
    current_tag = st.session_state.get('tag_no', 'default_tag')
    filename = f"{current_tag}_design_data.json"
    
    current_data = {k: st.session_state[k] for k in init_state.keys()}
    current_json_str = json.dumps(current_data, indent=4)
    
    st.download_button(f"📥 '{filename}' 다운로드", current_json_str, file_name=filename, mime="application/json")
    
    st.markdown("**데이터 로드 (JSON 텍스트 붙여넣기)**")
    st.text_area("JSON 텍스트 입력창:", value=json.dumps(init_state, indent=4), key='json_input_text', height=200)
    st.button("시나리오 적용 (Load)", on_click=apply_json, use_container_width=True)

st.subheader(f"🏷️ Current Equipment Tag: **{st.session_state['tag_no']}**")

# =========================================================
# [C] 1. 유체 물성치 데이터 (Fluid Properties)
# =========================================================
st.subheader("1. 유체 물성치 및 상(Phase) 정의")
st.radio("튜브 측(Tube-side) 유체 특성 선택", ["Liquid (뉴턴 유체 - 물, 오일 등)", "Slurry (비뉴턴 유체 - 고농도 혼합물)"], key='fluid_type', horizontal=True)

col_tube, col_shell = st.columns(2)

with col_tube:
    st.markdown("#### **Tube-side (Inner Fluid)**")
    st.number_input("혼합 밀도 (kg/m³)", key='t_rho', help="일반 액체: 700 - 1000, 슬러리: 1100 - 1800 이상")
    st.number_input("비열 (J/kg·K)", key='t_cp', help="물: 4180, 일반 오일류: 1800 - 2400")
    st.number_input("열전도도 (W/m·K)", key='t_k', help="물: 0.6, 일반 오일류: 0.1 - 0.2")
    
    if "Liquid" in st.session_state['fluid_type']:
        st.number_input("동점성 계수 (Pa·s)", format="%.4f", key='t_mu', help="물(20°C 기준): 0.001 Pa·s, 경질유: 0.002 - 0.010")
        st.success("✅ 뉴턴 유체 모드 (Dittus-Boelter / Ito 상관식)")
    else:
        st.warning("🚨 비뉴턴 유체 모드 (Metzner-Reed 일반화 수식 적용)")
        st.selectbox("유변학 모델 선택", ["Power-law (멱법칙)", "Bingham Plastic (빙햄 가소성)"], key='rheology_model')
        if st.session_state['rheology_model'] == "Bingham Plastic (빙햄 가소성)":
            st.number_input("항복 응력 (Yield stress, Pa)", step=1.0, key='tau_y', help="유동이 시작되기 위한 최소 응력. 펄프/고농도 슬러리: 5 - 50 Pa")
            st.number_input("가소성 점도 (Pa·s)", format="%.4f", key='plastic_visc')
        else:
            st.number_input("점조도 지수 K (Pa·sⁿ)", format="%.4f", key='consistency_k')
            st.number_input("유동 지수 n", min_value=0.1, max_value=2.0, step=0.1, key='flow_index_n', help="n < 1 (Shear-thinning, 페인트/고분자용액), n > 1 (Shear-thickening, 전분물)")

with col_shell:
    st.markdown("#### **Shell-side (Outer Fluid)**")
    st.number_input("밀도 (kg/m³)", key='s_rho')
    st.number_input("점도 (Pa·s)", format="%.4f", key='s_mu')
    st.number_input("비열 (J/kg·K)", key='s_cp')
    st.number_input("열전도도 (W/m·K)", key='s_k')

st.markdown("---")

# =========================================================
# [D] 2. 공정 조건 (Process Conditions)
# =========================================================
st.subheader("2. 공정 조건 및 허용 압력 강하")
col_pc1, col_pc2, col_pc3, col_pc4 = st.columns(4)

with col_pc1:
    st.number_input("Tube 유량 (kg/h)", step=100.0, key='m_hot')
    st.number_input("Shell 유량 (kg/h)", step=100.0, key='m_cold')
with col_pc2:
    st.number_input("Tube 입구 온도 (°C)", key='T_hot_in')
    st.number_input("Tube 목표 출구 온도 (°C)", key='T_hot_out')
with col_pc3:
    st.number_input("Shell 입구 온도 (°C)", key='T_cold_in')
    st.number_input("Shell 목표 출구 온도 (°C)", key='T_cold_out', help="주의: Tube 출구 온도와의 Temperature Cross(온도 역전)가 심하면 LMTD 보정계수(F)가 급감하여 설계가 불가능해질 수 있습니다.")
with col_pc4:
    st.number_input("Tube 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_tube', help="일반 유체: 0.5 - 0.7 bar, 점성 유체/슬러리: 1.0 - 1.5 bar 허용 권장")
    st.number_input("Shell 허용 ΔP (bar)", 0.1, 10.0, step=0.1, key='allowable_dp_shell', help="Shell 측은 코일 외부 환상 공간 유동의 특성을 고려하여 0.3 - 0.5 bar 이내 설계를 권장합니다.")

# LMTD 및 Q 사전 계산 (온도 역전 예외 처리 강화)
Q_kW_tube = (st.session_state['m_hot'] / 3600.0) * (st.session_state['t_cp'] / 1000.0) * abs(st.session_state['T_hot_in'] - st.session_state['T_hot_out'])
dT1 = st.session_state['T_hot_in'] - st.session_state['T_cold_out']
dT2 = st.session_state['T_hot_out'] - st.session_state['T_cold_in']

if dT1 == dT2 and dT1 > 0:
    LMTD = dT1
elif dT1 > 0 and dT2 > 0:
    LMTD = (dT1 - dT2) / np.log(dT1 / dT2)
else:
    st.error("🚨 열역학적 오류 (Temperature Cross Error): 입/출구 온도 조건이 물리적으로 불가능하거나 역전되었습니다. 온도를 재설정하십시오.")
    LMTD = 1.0  # ZeroDivision 방지용 임시값

st.markdown("---")

# =========================================================
# [E] 3. 기하학적 변수 및 오염 계수 (Geometry & Material)
# =========================================================
st.subheader("3. 기하학적 설계 변수 및 튜브 재질")

col_g1, col_g2, col_g3, col_g4 = st.columns(4)

with col_g1:
    st.slider("튜브 외경 (d_o, mm)", 10.0, 50.0, step=0.1, key='d_o', help="[표준 튜브 외경] 19.05 mm (3/4인치), 25.4 mm (1인치)를 가장 많이 사용합니다.")
    st.number_input("튜브 두께 (t, mm)", 1.0, 5.0, step=0.1, key='t_thick', help="BWG(Birmingham Wire Gauge) 기준: BWG 14 (2.11 mm), BWG 16 (1.65 mm) 권장.")
    d_i = st.session_state['d_o'] - 2 * st.session_state['t_thick']
    st.caption(f"✓ 내경 (d_i): **{d_i:.2f} mm**")
    
    mat_dict = {
        'Carbon Steel (k = 45 W/m·K)': 45.0,
        'Stainless Steel 304 (k = 15 W/m·K)': 15.0,
        'Stainless Steel 316 (k = 16 W/m·K)': 16.0,
        'Duplex Stainless Steel (k = 19 W/m·K)': 19.0,
        'Titanium (k = 22 W/m·K)': 22.0,
        'Inconel 600 (k = 15 W/m·K)': 15.0,
        'Copper (k = 400 W/m·K)': 400.0,
        'Custom (사용자 지정)': st.session_state.get('tube_k_wall', 16.0)
    }
    if st.session_state['tube_material'] not in mat_dict:
        st.session_state['tube_material'] = 'Stainless Steel 316 (k = 16 W/m·K)'
        
    selected_mat = st.selectbox("튜브 재질 (Material)", list(mat_dict.keys()), key='tube_material')
    if "Custom" in selected_mat:
        st.number_input("재질 열전도도 (W/m·K)", 1.0, 500.0, step=1.0, key='tube_k_wall')
    else:
        st.session_state['tube_k_wall'] = mat_dict[selected_mat]
        st.caption(f"✓ 벽면 열전도도: **{st.session_state['tube_k_wall']} W/m·K**")

with col_g2:
    min_Dc = st.session_state['d_o'] / 0.1
    current_Dc = max(st.session_state['D_c'], min_Dc)
    st.session_state['D_c'] = current_Dc
    st.slider("코일 중심 직경 (D_c, mm)", float(min_Dc), 2000.0, step=10.0, key='D_c', help="제작 한계성(Fabrication Limit): 코일 중심 직경이 외경의 10배보다 작으면 벤딩 시 튜브 파열 위험이 큽니다.")
    curvature_ratio = d_i / st.session_state['D_c']
    st.caption(f"✓ 곡률비: **{curvature_ratio:.4f}** (권장 < 0.1)")

with col_g3:
    min_pitch = st.session_state['d_o'] * 1.25
    current_pitch = max(st.session_state['pitch'], min_pitch)
    st.session_state['pitch'] = current_pitch
    st.slider("코일 피치 (p, mm)", float(min_pitch), 300.0, step=1.0, key='pitch', help="안정적인 조립 및 튜브 간 간섭을 막기 위해 최소 튜브 외경의 1.25배 이상이어야 합니다.")
    
    min_Ds = st.session_state['D_c'] + st.session_state['d_o'] + 20.0
    current_Ds = max(st.session_state['D_s'], min_Ds)
    st.session_state['D_s'] = current_Ds
    st.number_input("쉘 내경 (D_s, mm)", float(min_Ds), 3000.0, step=10.0, key='D_s', help="코일 외경 대비 최소 20 - 50 mm의 여유 공간(Clearance)이 필요합니다.")

with col_g4:
    R_fi_help = "[내부 오염계수 권장치]\n- 청정수/증류수: 0.0001\n- 일반 냉각수: 0.0003 - 0.0005\n- 해수: 0.0007\n- 점성 오일/슬러리: 0.0010 - 0.0020"
    st.number_input("Tube 오염계수 R_fi (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fi', help=R_fi_help)
    
    R_fo_help = "[외부 오염계수 권장치]\n- 압축공기/가스: 0.0004\n- 순환 냉각수: 0.0003\n- 크루드 오일: 0.0015 - 0.0025\n* 쉘 측은 세척이 어려우므로 보수적으로 접근 요망."
    st.number_input("Shell 오염계수 R_fo (m²K/W)", 0.0, 0.02, format="%.6f", key='R_fo', help=R_fo_help)

st.markdown("---")

# =========================================================
# [F] 4. 열역학 및 수력학 연산 (Core Math)
# =========================================================
st.subheader("4. 열전달 및 수력학 검증 (Thermodynamics & Hydraulics)")

m_hot_kg_s = st.session_state['m_hot'] / 3600.0
A_c = np.pi * ((d_i / 1000.0) ** 2) / 4.0
v_tube = m_hot_kg_s / (st.session_state['t_rho'] * A_c) if A_c > 0 else 0

if "Slurry" in st.session_state['fluid_type'] and v_tube > 2.5:
    st.error(f"🚨 침식 한계 초과: 슬러리 유속({v_tube:.2f} m/s)이 2.5 m/s를 초과했습니다. 외벽 마모가 우려되니 튜브 외경(d_o)을 키우십시오.")
elif v_tube > 5.0:
    st.warning(f"⚠️ 진동 경고 (FIV): 유속({v_tube:.2f} m/s)이 5.0 m/s를 초과했습니다. 튜브 파손 및 펌프 양정 부족 현상을 주의하십시오.")
elif v_tube < 0.5:
    st.info(f"💡 정체 경고: 유속({v_tube:.2f} m/s)이 너무 느려 스케일(Fouling)이 급속도로 퇴적될 수 있습니다. (권장: 1.0 m/s 이상)")

if "Liquid" in st.session_state['fluid_type']:
    Re = (st.session_state['t_rho'] * v_tube * (d_i / 1000.0)) / st.session_state['t_mu']
    Pr = (st.session_state['t_cp'] * st.session_state['t_mu']) / st.session_state['t_k']
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    
    if Re < Re_crit:
        Nu_straight = 4.36
        f_straight = 64.0 / Re if Re > 0 else 0.0
        f_c = f_straight * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)
        flow_regime = "층류 (Laminar)"
    else:
        Nu_straight = 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)
        flow_regime = "난류 (Turbulent)"
else:
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
        flow_regime = "슬러리 층류 (Laminar)"
    else:
        Nu_straight = 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)
        flow_regime = "슬러리 난류 (Turbulent)"

Nu_calc = Nu_straight * (1.0 + 3.5 * curvature_ratio)
h_i = (Nu_calc * st.session_state['t_k']) / (d_i / 1000.0)

m_cold_kg_s = st.session_state['m_cold'] / 3600.0
A_free_flow = (np.pi/4) * ((st.session_state['D_s']/1000.0)**2 - (st.session_state['D_c']/1000.0)**2)
v_shell = m_cold_kg_s / (st.session_state['s_rho'] * A_free_flow) if A_free_flow > 0 else 0.0
Re_shell = (st.session_state['s_rho'] * v_shell * (st.session_state['d_o'] / 1000.0)) / st.session_state['s_mu']
Pr_shell = (st.session_state['s_cp'] * st.session_state['s_mu']) / st.session_state['s_k']
Nu_shell = 0.33 * (max(Re_shell, 1.0) ** 0.6) * (Pr_shell ** 0.33)
h_o = (Nu_shell * st.session_state['s_k']) / (st.session_state['d_o'] / 1000.0)

R_wall = ((st.session_state['d_o'] / 1000.0) * np.log(st.session_state['d_o'] / d_i)) / (2.0 * st.session_state['tube_k_wall'])

sum_resistances = (1.0 / max(h_o, 0.1)) + st.session_state['R_fo'] + R_wall + st.session_state['R_fi'] * (st.session_state['d_o'] / d_i) + (st.session_state['d_o'] / d_i) * (1.0 / max(h_i, 0.1))
U_calc = 1.0 / sum_resistances

# =========================================================
# [G] 5. 결과 요약 및 압력 강하 시각화
# =========================================================
Area = (Q_kW_tube * 1000.0) / (U_calc * LMTD) if LMTD > 0 else 0.0
Tube_length = Area / (np.pi * (st.session_state['d_o'] / 1000.0))
Turns = Tube_length / (np.pi * (st.session_state['D_c'] / 1000.0))

dp_tube_pa = f_c * (Tube_length / (d_i / 1000.0)) * (st.session_state['t_rho'] * (v_tube ** 2) / 2.0)
dp_tube_bar = dp_tube_pa / 100000.0

st.markdown("#### 핵심 설계 결과 요약")
res1, res2, res3, res4 = st.columns(4)
res1.metric("총괄 열전달 계수 (U)", f"{U_calc:,.1f} W/m²K")
res2.metric("필요 전열 면적 (Area)", f"{Area:,.2f} m²")
res3.metric("필요 튜브 길이 (Length)", f"{Tube_length:,.1f} m")
res4.metric("코일 권선 수 (Turns)", f"{Turns:,.1f} 회")

dp1, dp2, dp3, dp4 = st.columns(4)
dp1.metric("Tube 유속", f"{v_tube:.2f} m/s")
dp2.metric("유동 상태", flow_regime)
dp3.metric("코일 마찰 계수 (f_c)", f"{f_c:.4f}")

allow_dp = st.session_state['allowable_dp_tube']
if dp_tube_bar > allow_dp:
    dp4.metric("Tube 측 예상 ΔP", f"{dp_tube_bar:.2f} bar", delta=f"초과: {dp_tube_bar - allow_dp:.2f} bar", delta_color="inverse")
else:
    dp4.metric("Tube 측 예상 ΔP", f"{dp_tube_bar:.2f} bar", delta=f"안전: 여유 {allow_dp - dp_tube_bar:.2f} bar", delta_color="normal")

# =========================================================
# [H] 6. 3D 형상 렌더링
# =========================================================
st.markdown("---")
st.subheader("5. 3D 코일 형상 (Schematic Representation)")

if Turns > 0 and Turns < 5000:
    t = np.linspace(0, Turns * 2 * np.pi, int(max(Turns * 50, 100)))
    x = (st.session_state['D_c'] / 2) * np.cos(t)
    y = (st.session_state['D_c'] / 2) * np.sin(t)
    z = (st.session_state['pitch'] / (2 * np.pi)) * t

    fig = go.Figure(data=[go.Scatter3d(x=x, y=y, z=z, mode='lines', line=dict(color='darkblue', width=8))])
    fig.update_layout(
        scene=dict(xaxis_title='X (mm)', yaxis_title='Y (mm)', zaxis_title='Height (mm)', aspectmode='data'),
        margin=dict(l=0, r=0, b=0, t=0),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("전열 면적 산출 불가. 온도 조건(Temperature Cross) 또는 물리적 변수를 다시 확인하십시오.")
