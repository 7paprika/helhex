import streamlit as st
import numpy as np
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")

st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# =========================================================
# [A] Session State 초기화 (JSON 로드용)
# =========================================================
default_props = {
    "tube_side": {"density": 998.0, "cp": 4180.0, "thermal_cond": 0.6},
    "shell_side": {"density": 998.0, "viscosity": 0.001, "cp": 4180.0, "thermal_cond": 0.6}
}

if 'props' not in st.session_state:
    st.session_state['props'] = default_props

def apply_json():
    try:
        parsed_data = json.loads(st.session_state['json_input'])
        st.session_state['props'] = parsed_data
        st.success("JSON 데이터가 성공적으로 로드되었습니다.")
    except Exception as e:
        st.error(f"JSON 파싱 에러: 형식이 잘못되었습니다. ({e})")

# =========================================================
# [B] 1. 유체 물성치 데이터 (Fluid Properties)
# =========================================================
st.subheader("1. 유체 물성치 및 상(Phase) 정의")

fluid_type = st.radio(
    "튜브 측(Tube-side) 유체 특성 선택",
    options=["Liquid (뉴턴 유체 - 물, 오일 등)", "Slurry (비뉴턴 유체 - 고농도 혼합물)"],
    index=0,
    horizontal=True
)

col_tube, col_shell = st.columns(2)

# Tube-side 입력
with col_tube:
    st.markdown("#### **Tube-side (Inner Fluid)**")
    t_rho = st.number_input("혼합 밀도 (kg/m³)", value=float(st.session_state['props']['tube_side']['density']), key='t_rho')
    t_cp = st.number_input("비열 (J/kg·K)", value=float(st.session_state['props']['tube_side']['cp']), key='t_cp')
    t_k = st.number_input("열전도도 (W/m·K)", value=float(st.session_state['props']['tube_side']['thermal_cond']), key='t_k')
    
    # Liquid / Slurry 동적 입력 분기
    if "Liquid" in fluid_type:
        t_mu = st.number_input("동점성 계수 (Pa·s)", value=0.001, format="%.4f", key='t_mu')
        st.success("✅ 뉴턴 유체 모드 (Dittus-Boelter 및 Ito 일반 수식 적용)")
    else:
        st.warning("🚨 비뉴턴 유체 모드 (Metzner-Reed 일반화 Re 적용)")
        rheology_model = st.selectbox("유변학 모델 선택", ["Power-law (멱법칙)", "Bingham Plastic (빙햄 가소성)"])
        if rheology_model == "Bingham Plastic (빙햄 가소성)":
            tau_y = st.number_input("항복 응력 (Yield stress, Pa)", value=5.0, step=1.0)
            plastic_visc = st.number_input("가소성 점도 (Pa·s)", value=0.05, format="%.4f")
            # Bingham의 단순화를 위해 등가 Power-law 변수로 우회 (실제 설계시엔 Bingham 전용 수식 필요)
            consistency_k = plastic_visc
            flow_index_n = 1.0
            st.info("※ 현재 백단 로직은 Power-law 기반으로 통합되어 있어 등가 근사치로 연산됩니다.")
        else:
            consistency_k = st.number_input("점조도 지수 K (Pa·sⁿ)", value=0.1, format="%.4f")
            flow_index_n = st.number_input("유동 지수 n", min_value=0.1, max_value=2.0, value=0.8, step=0.1)

# Shell-side 입력
with col_shell:
    st.markdown("#### **Shell-side (Outer Fluid)**")
    s_rho = st.number_input("밀도 (kg/m³)", value=float(st.session_state['props']['shell_side']['density']), key='s_rho')
    s_mu = st.number_input("점도 (Pa·s)", value=float(st.session_state['props']['shell_side']['viscosity']), format="%.4f", key='s_mu')
    s_cp = st.number_input("비열 (J/kg·K)", value=float(st.session_state['props']['shell_side']['cp']), key='s_cp')
    s_k = st.number_input("열전도도 (W/m·K)", value=float(st.session_state['props']['shell_side']['thermal_cond']), key='s_k')

with st.expander("⚙️ JSON 데이터 저장 / 로드 열기"):
    col_json1, col_json2 = st.columns(2)
    current_props = {
        "tube_side": {"density": t_rho, "cp": t_cp, "thermal_cond": t_k},
        "shell_side": {"density": s_rho, "viscosity": s_mu, "cp": s_cp, "thermal_cond": s_k}
    }
    with col_json1:
        st.code(json.dumps(current_props, indent=4), language='json')
    with col_json2:
        st.text_area("JSON 로드", value=json.dumps(default_props, indent=4), key='json_input', height=150)
        st.button("JSON 적용하기", on_click=apply_json)

st.markdown("---")

# =========================================================
# [C] 2. 공정 조건 (Process Conditions)
# =========================================================
st.subheader("2. 공정 조건 및 허용 압력 강하 (Process & Constraints)")
col_pc1, col_pc2, col_pc3, col_pc4 = st.columns(4)

with col_pc1:
    m_hot = st.number_input("Tube 유량 (kg/h)", value=5000.0, step=100.0)
    m_cold = st.number_input("Shell 유량 (kg/h)", value=8000.0, step=100.0)
with col_pc2:
    T_hot_in = st.number_input("Tube 입구 온도 (°C)", value=150.0)
    T_hot_out = st.number_input("Tube 목표 출구 온도 (°C)", value=80.0)
with col_pc3:
    T_cold_in = st.number_input("Shell 입구 온도 (°C)", value=30.0)
    T_cold_out = st.number_input("Shell 목표 출구 온도 (°C)", value=60.0)
with col_pc4:
    allowable_dp_tube = st.number_input("Tube 허용 ΔP (bar)", 0.1, 10.0, 0.5, 0.1)
    allowable_dp_shell = st.number_input("Shell 허용 ΔP (bar)", 0.1, 10.0, 0.5, 0.1)

# 열부하 (Q) 및 LMTD 계산
Q_kW_tube = (m_hot / 3600.0) * (t_cp / 1000.0) * abs(T_hot_in - T_hot_out)
dT1 = T_hot_in - T_cold_out
dT2 = T_hot_out - T_cold_in
LMTD = (dT1 - dT2) / np.log(dT1 / dT2) if dT1 != dT2 and dT1 > 0 and dT2 > 0 else (dT1 + dT2)/2.0

st.markdown("---")

# =========================================================
# [D] 3. 기하학적 변수 및 오염 계수 (Geometry & Fouling)
# =========================================================
st.subheader("3. 기하학적 설계 변수 (Geometry Adjustments)")

col_g1, col_g2, col_g3, col_g4 = st.columns(4)

with col_g1:
    d_o = st.slider("튜브 외경 (d_o, mm)", 10.0, 50.0, 25.4, 0.1)
    t_thick = st.number_input("튜브 두께 (t, mm)", 1.0, 5.0, 2.11, 0.1)
    d_i = d_o - 2 * t_thick
    st.caption(f"✓ 내경 (d_i): **{d_i:.2f} mm**")

with col_g2:
    min_Dc = d_o / 0.1
    D_c = st.slider("코일 중심 직경 (D_c, mm)", float(min_Dc), 1000.0, max(300.0, min_Dc), 10.0)
    curvature_ratio = d_i / D_c
    st.caption(f"✓ 곡률비: **{curvature_ratio:.4f}** (권장 < 0.1)")

with col_g3:
    min_pitch = d_o * 1.25
    pitch = st.slider("코일 피치 (p, mm)", float(min_pitch), 200.0, max(50.0, min_pitch), 1.0)
    min_Ds = D_c + d_o + 20.0
    D_s = st.number_input("쉘 내경 (D_s, mm)", float(min_Ds), 2000.0, float(min_Ds + 50.0), 10.0)

with col_g4:
    R_fi = st.number_input("Tube 오염계수 R_fi", 0.0, 0.01, 0.000176, format="%.6f", help="물: 0.0002, 중질유: 0.0015")
    R_fo = st.number_input("Shell 오염계수 R_fo", 0.0, 0.01, 0.000176, format="%.6f", help="크루드 오일: 0.0020")

st.markdown("---")

# =========================================================
# [E] 4. 열역학 및 수력학 코어 연산 (Core Calculations)
# =========================================================
st.subheader("4. 열전달 및 수력학 검증 (Thermodynamics & Hydraulics)")

m_hot_kg_s = m_hot / 3600.0
A_c = np.pi * ((d_i / 1000.0) ** 2) / 4.0
v_tube = m_hot_kg_s / (t_rho * A_c)

# 유속 검증
if "Slurry" in fluid_type and v_tube > 2.5:
    st.error(f"🚨 침식 위험: 슬러리 유속({v_tube:.2f} m/s)이 너무 빠릅니다! 튜브 직경을 키우십시오.")
elif v_tube > 5.0:
    st.warning(f"⚠️ 유속({v_tube:.2f} m/s)이 매우 높습니다. 진동 및 압력 강하를 주의하십시오.")

# Tube-side 계산 (Liquid vs Slurry)
if "Liquid" in fluid_type:
    Re = (t_rho * v_tube * (d_i / 1000.0)) / t_mu
    Pr = (t_cp * t_mu) / t_k
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    
    if Re < Re_crit:
        Nu_straight = 4.36
        f_straight = 64.0 / Re if Re > 0 else 0.0
        f_c = f_straight * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)
        flow_regime = "층류 (Laminar)"
    else:
        Nu_straight = 0.023 * (Re ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)
        flow_regime = "난류 (Turbulent)"
else:
    # Slurry (Power-law)
    n_val = flow_index_n
    K_val = consistency_k
    D_m = d_i / 1000.0
    
    term1 = t_rho * (v_tube ** (2.0 - n_val)) * (D_m ** n_val)
    term2 = (8.0 ** (n_val - 1.0)) * K_val * (((3.0 * n_val + 1.0) / (4.0 * n_val)) ** n_val)
    Re = term1 / term2 if term2 > 0 else 0.0
    
    mu_app = term1 / (Re * v_tube) if (Re * v_tube) > 0 else 0.001
    Pr = (t_cp * mu_app) / t_k
    De = Re * np.sqrt(curvature_ratio)
    Re_crit = 2100 * (1.0 + 12.0 * np.sqrt(curvature_ratio))
    
    if Re < Re_crit:
        Nu_straight = 4.36
        f_straight = 64.0 / max(Re, 1.0)
        f_c = f_straight * (1.0 + 0.033 * (np.log10(max(De, 1.0)))**4.0)
        flow_regime = "슬러리 층류 (Slurry Laminar)"
    else:
        Nu_straight = 0.023 * (max(Re, 1.0) ** 0.8) * (Pr ** 0.4)
        f_c = 0.304 / (max(Re, 1.0) ** 0.25) + 0.029 * np.sqrt(curvature_ratio)
        flow_regime = "슬러리 난류 (Slurry Turbulent)"

Nu_calc = Nu_straight * (1.0 + 3.5 * curvature_ratio)
h_i = (Nu_calc * t_k) / (d_i / 1000.0)

# Shell-side 단순화 연산
m_cold_kg_s = m_cold / 3600.0
A_free_flow = (np.pi/4) * ((D_s/1000.0)**2 - (D_c/1000.0)**2)
v_shell = m_cold_kg_s / (s_rho * A_free_flow) if A_free_flow > 0 else 0.0
Re_shell = (s_rho * v_shell * (d_o / 1000.0)) / s_mu
Pr_shell = (s_cp * s_mu) / s_k
Nu_shell = 0.33 * (max(Re_shell, 1.0) ** 0.6) * (Pr_shell ** 0.33)
h_o = (Nu_shell * s_k) / (d_o / 1000.0)

# 총괄 열전달 계수 (U)
R_wall = ((d_o / 1000.0) * np.log(d_o / d_i)) / (2.0 * 16.0) # SS316 가정
sum_resistances = (1.0 / h_o) + R_fo + R_wall + R_fi * (d_o / d_i) + (d_o / d_i) * (1.0 / h_i)
U_calc = 1.0 / sum_resistances

# =========================================================
# [F] 5. 최종 결과 (Results & Validation)
# =========================================================
Area = (Q_kW_tube * 1000.0) / (U_calc * LMTD)
Tube_length = Area / (np.pi * (d_o / 1000.0))
Turns = Tube_length / (np.pi * (D_c / 1000.0))

# 압력 강하 연산 (ΔP)
dp_tube_pa = f_c * (Tube_length / (d_i / 1000.0)) * (t_rho * (v_tube ** 2) / 2.0)
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

if dp_tube_bar > allowable_dp_tube:
    dp4.metric("Tube 측 예상 ΔP", f"{dp_tube_bar:.2f} bar", delta=f"초과: {dp_tube_bar - allowable_dp_tube:.2f} bar", delta_color="inverse")
    st.error(f"🚨 **설계 불가:** Tube 측 압력 강하가 허용치({allowable_dp_tube} bar)를 초과했습니다. 외경(d_o)을 키우십시오.")
else:
    dp4.metric("Tube 측 예상 ΔP", f"{dp_tube_bar:.2f} bar", delta=f"안전: 여유 {allowable_dp_tube - dp_tube_bar:.2f} bar", delta_color="normal")

st.markdown("---")

# =========================================================
# [G] 6. 3D 형상 시각화 (Visualization)
# =========================================================
st.subheader("5. 3D 코일 형상 (Schematic Representation)")
if Turns > 0:
    t = np.linspace(0, Turns * 2 * np.pi, int(max(Turns * 50, 100)))
    x = (D_c / 2) * np.cos(t)
    y = (D_c / 2) * np.sin(t)
    z = (pitch / (2 * np.pi)) * t

    fig = go.Figure(data=[go.Scatter3d(x=x, y=y, z=z, mode='lines', line=dict(color='darkblue', width=8))])
    fig.update_layout(
        scene=dict(
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            zaxis_title='Height (mm)',
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("전열 면적 계산에 오류가 있어 형상을 렌더링할 수 없습니다. 입력값을 확인하십시오.")
