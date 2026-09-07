import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import CubicSpline
from scipy.signal import welch
import io

integrate_func = getattr(np, 'trapezoid', getattr(np, 'trapz', None))

def calc_dfa_alpha1(rr):
    """計算 DFA Alpha 1 (短時間尺度非線性相關性)"""
    # 短期尺度 n 通常定義為 4 到 16，至少需要確保有足夠的心跳樣本(約3-4倍的最大n值)
    if len(rr) < 48:
        return np.nan
        
    y = np.cumsum(rr - np.mean(rr))
    n_vals = np.arange(4, 17)
    F_n = np.zeros(len(n_vals))
    
    for i, n in enumerate(n_vals):
        n_boxes = len(y) // n
        if n_boxes == 0:
            continue
            
        y_boxes = y[:n_boxes * n].reshape((n_boxes, n))
        x = np.arange(1, n + 1)
        
        # 對每個 box 進行線性擬合 (detrend)
        coefs = np.polyfit(x, y_boxes.T, 1)
        y_trend = np.outer(x, coefs[0]) + coefs[1]
        
        # 計算均方根波動
        F_n[i] = np.sqrt(np.mean((y_boxes.T - y_trend)**2))
        
    valid = F_n > 0
    if np.sum(valid) > 2:
        # 在 log-log 座標上計算斜率
        coeffs = np.polyfit(np.log10(n_vals[valid]), np.log10(F_n[valid]), 1)
        return coeffs[0]
    return np.nan

st.set_page_config(page_title="進階 HRV (時/頻/非線性) 分析工具", layout="wide")
st.title("HRV & HR 連續時間軸分析工具 (含 LF/HF & DFA α1)")
st.markdown("針對帶有精確時間戳記 `Time,RRI,...` 的 CSV 檔案進行解析，新增非線性碎形特徵 DFA α1 追蹤。")

st.sidebar.header("演算法參數設定")
window_size_sec = st.sidebar.slider("滑動視窗大小 (秒)", 60, 300, 120, 10, help="LF與DFA建議至少 120 秒")
step_sec = st.sidebar.number_input("滑動步伐 (秒)", min_value=1.0, value=1.0)
rri_min = st.sidebar.number_input("RRI 生理下限 (ms)", value=300)
rri_max = st.sidebar.number_input("RRI 生理上限 (ms)", value=2000)

uploaded_file = st.file_uploader("上傳 HRV 資料檔 (CSV)", type=["csv"])

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8").splitlines()
    header_idx = 0
    for i, line in enumerate(content):
        if "Time" in line and "RRI" in line:
            header_idx = i
            break
            
    df_raw = pd.read_csv(io.StringIO("\n".join(content[header_idx:])))
    
    if 'Time' not in df_raw.columns or 'RRI' not in df_raw.columns:
        st.error("CSV 檔案中找不到 'Time' 或 'RRI' 欄位。")
        st.stop()
        
    df_raw['RRI'] = pd.to_numeric(df_raw['RRI'], errors='coerce')
    
    t_str = df_raw['Time'].astype(str).str.strip()
    t_str = t_str.str.replace(r'\s+(\d+)$', r'.\1', regex=True)
    dt = pd.to_datetime(t_str, errors='coerce')
    
    valid_mask = dt.notna() & df_raw['RRI'].notna()
    df = df_raw[valid_mask].copy()
    dt_valid = dt[valid_mask]
    
    start_dt = dt_valid.iloc[0]
    
    secs = dt_valid.dt.hour * 3600 + dt_valid.dt.minute * 60 + dt_valid.dt.second + dt_valid.dt.microsecond / 1e6
    diffs = secs.diff()
    crossings = (diffs < -43200).cumsum().fillna(0) * 86400
    
    continuous_secs = secs + crossings
    df['Time_sec'] = continuous_secs - continuous_secs.iloc[0]
    
    df = df[(df['RRI'] >= rri_min) & (df['RRI'] <= rri_max)]
    df = df.sort_values('Time_sec').drop_duplicates(subset=['Time_sec'])
    
    if len(df) < 10:
        st.error(f"有效資料點過少 (僅餘 {len(df)} 筆)。")
        st.stop()
        
    df['RRI_diff'] = df['RRI'].diff()
    df['RRI_diff_sq'] = df['RRI_diff'] ** 2
    df['NN50_flag'] = (df['RRI_diff'].abs() > 50).astype(int)
    
    t_raw = df['Time_sec'].values
    rri_raw = df['RRI'].values
    fs = 4.0 
    t_interp = np.arange(t_raw[0], t_raw[-1], 1/fs)
    cubic_spline = CubicSpline(t_raw, rri_raw, extrapolate=True)
    rri_interp = cubic_spline(t_interp)
    
    results = []
    progress_bar = st.progress(0)
    time_points = np.arange(t_raw[0] + window_size_sec, t_raw[-1], step_sec)
    
    for i, current_t in enumerate(time_points):
        if i % 10 == 0:
            progress_bar.progress((i + 1) / len(time_points))
            
        win_mask = (df['Time_sec'] > current_t - window_size_sec) & (df['Time_sec'] <= current_t)
        df_win = df[win_mask]
        
        if len(df_win) < 10:
            continue
            
        hr = 60000.0 / df_win['RRI'].mean()
        sdnn = df_win['RRI'].std()
        rmssd = np.sqrt(df_win['RRI_diff_sq'].mean())
        pnn50 = df_win['NN50_flag'].mean() * 100
        
        # 計算 DFA Alpha 1 (直接使用原始未插值、去除極端值的 RRI 序列)
        alpha1 = calc_dfa_alpha1(df_win['RRI'].values)
        
        win_interp_mask = (t_interp > current_t - window_size_sec) & (t_interp <= current_t)
        win_rri_interp = rri_interp[win_interp_mask]
        
        if len(win_rri_interp) >= int(window_size_sec * fs * 0.8):
            win_rri_detrend = win_rri_interp - np.mean(win_rri_interp)
            f_psd, pxx = welch(win_rri_detrend, fs=fs, nperseg=len(win_rri_detrend))
            idx_lf = np.where((f_psd >= 0.04) & (f_psd <= 0.15))[0]
            idx_hf = np.where((f_psd >= 0.15) & (f_psd <= 0.40))[0]
            lf = integrate_func(pxx[idx_lf], f_psd[idx_lf]) if len(idx_lf) > 0 else np.nan
            hf = integrate_func(pxx[idx_hf], f_psd[idx_hf]) if len(idx_hf) > 0 else np.nan
        else:
            lf, hf = np.nan, np.nan
            
        current_dt = start_dt + pd.Timedelta(seconds=float(current_t))
        
        results.append({
            'Datetime': current_dt,
            'Time_str': current_dt.strftime('%H:%M:%S'),
            'HR': hr, 'SDNN': sdnn, 'RMSSD': rmssd, 'pNN50': pnn50,
            'LF': lf, 'HF': hf, 'Alpha1': alpha1
        })
        
    progress_bar.empty()
    calc_df = pd.DataFrame(results).dropna(subset=['HR', 'RMSSD'])
    st.success(f"✅ 計算完成！基於真實時間軸，共產生 **{len(calc_df)}** 個特徵點。")
    
    fig = make_subplots(rows=6, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03,
                        subplot_titles=("心率 (HR)", "RMSSD", "SDNN", "pNN50", "頻域功率 (LF & HF)", "DFA Alpha 1 (短尺度非線性動態)"))

    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['HR'], mode='lines', name='HR', line=dict(color='#EF553B')), row=1, col=1)
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['RMSSD'], mode='lines', name='RMSSD', line=dict(color='#00CC96')), row=2, col=1)
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['SDNN'], mode='lines', name='SDNN', line=dict(color='#AB63FA')), row=3, col=1)
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['pNN50'], mode='lines', name='pNN50', line=dict(color='#FFA15A')), row=4, col=1)
    
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['LF'], mode='lines', name='LF', line=dict(color='#FF97FF')), row=5, col=1)
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['HF'], mode='lines', name='HF', line=dict(color='#19D3F3')), row=5, col=1)
    
    fig.add_trace(go.Scatter(x=calc_df['Datetime'], y=calc_df['Alpha1'], mode='lines', name='DFA α1', line=dict(color='#FFD700')), row=6, col=1)

    fig.update_layout(height=1200, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      title_text=f"HRV 連續追蹤分析 (滑動視窗: {window_size_sec}s)")
    
    fig.update_yaxes(title_text="bpm", row=1, col=1)
    for i in range(2, 4): fig.update_yaxes(title_text="ms", row=i, col=1)
    fig.update_yaxes(title_text="%", row=4, col=1)
    fig.update_yaxes(title_text="ms²", row=5, col=1)
    fig.update_yaxes(title_text="α1", range=[0, 2], row=6, col=1) 
    
    fig.update_xaxes(title_text="真實時間", tickformat="%H:%M:%S", row=6, col=1)

    st.plotly_chart(fig, use_container_width=True)
    
    export_df = calc_df.drop(columns=['Datetime']).rename(columns={'Time_str': 'Time'})
    st.download_button(
        label="下載計算結果 (CSV)",
        data=export_df.to_csv(index=False).encode('utf-8'),
        file_name='hrv_features_real_time_with_dfa.csv',
        mime='text/csv'
    )
