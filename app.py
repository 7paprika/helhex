import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Helical Tube Heat Exchanger Designer", layout="wide")

st.title("플랜트 공정 설계: Helical Tube Heat Exchanger 최적화")
st.markdown("---")

# ---------------------------------------------------------
# 1. 상단: 공정 입력 데이터 (Process Conditions)
# ---------------------------------------------------------
st.subheader("1. 공정 조건 (Process Conditions)")
col1, col2, col3, col4 = st.columns(4)

with col1:
    m_hot = st.number_input("Hot Fluid 유량 (kg/h)", value=5000.0, step=100.0)
with col2:
    T_hot_in = st.number_input("Hot Fluid 입구 온도 (°C)", value=150.0)
with col3:
    T_hot_out = st.number_input("Hot Fluid 목표 출구 온도 (°C)", value=80.0)
with col4:
    U_assumed = st.number_input("가정된 총괄열전달계수 (W/m²K)", value=800.0)
    st.caption("※ 실제 설계 시 튜브/쉘 측 계산 로직으로 대체 필요")

# 기본 열부하 계산 (단순화를 위해 비열 Cp = 4.18 kJ/kgK 가정)
Cp = 4.18 
Q_kW = (m_hot / 3600) * Cp * (T_hot_in - T_hot_out)

st.markdown("---")

# ---------------------------------------------------------
# 2. 중단: 기하학적 설계 변수 (Geometry Adjustments)
# ---------------------------------------------------------
st.subheader("2. 기하학적 변수 최적화 (Geometry Sliders)")
st.info("💡 **엔지니어 가이드:** 곡률비(d_o / D_c)는 0.1 이하를 권장하며, Pitch는 외경의 1.25배 이상이어야 제작이 가능합니다.")

col_g1, col_g2 = st.columns(2)

with col_g1:
    d_o = st.slider("튜브 외경 (d_o, mm)", min_value=10.0, max_value=50.0, value=25.4, step=0.1)
    # Recommended Coil Diameter limits
    min_Dc = d_o / 0.1
    D_c = st.slider("코일 중심 직경 (D_c, mm)", min_value=float(min_Dc), max_value=1000.0, value=max(300.0, min_Dc), step=10.0)
    st.caption(f"✓ 현재 곡률비(Curvature Ratio): **{d_o/D_c:.3f}** (권장: 0.1 이하)")

with col_g2:
    min_pitch = d_o * 1.25
    pitch = st.slider("코일 피치 (Pitch, mm)", min_value=float(min_pitch), max_value=200.0, value=max(50.0, min_pitch), step=1.0)
    st.caption(f"✓ 최소 요구 피치: **{min_pitch:.1f} mm**")

# ---------------------------------------------------------
# 3. 하단: 결과 도출 및 시각화 (Results & Visualization)
# ---------------------------------------------------------
st.markdown("---")
st.subheader("3. 설계 결과 및 형상 시각화")

# LMTD 및 필요 면적 계산 (Cold Fluid 20°C -> 50°C 가정)
T_cold_in, T_cold_out = 20.0, 50.0
dT1 = T_hot_in - T_cold_out
dT2 = T_hot_out - T_cold_in
LMTD = (dT1 - dT2) / np.log(dT1 / dT2) if dT1 != dT2 else dT1

Area = (Q_kW * 1000) / (U_assumed * LMTD)
Tube_length = Area / (np.pi * (d_o / 1000))
Turns = Tube_length / (np.pi * (D_c / 1000))

res_col1, res_col2, res_col3, res_col4 = st.columns(4)
res_col1.metric("열부하 (Heat Duty)", f"{Q_kW:.2f} kW")
res_col2.metric("요구 전열 면적", f"{Area:.2f} m²")
res_col3.metric("필요 튜브 길이", f"{Tube_length:.2f} m")
res_col4.metric("코일 권선 수 (Turns)", f"{Turns:.1f} 회")

# Plotly 3D Visualization
st.markdown("#### 3D 코일 형상 (Schematic Representation)")
t = np.linspace(0, Turns * 2 * np.pi, int(Turns * 50))
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
    height=500
)
st.plotly_chart(fig, use_container_width=True)
