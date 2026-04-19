import streamlit as st
import requests
import pandas as pd
import time
import altair as alt

st.set_page_config(page_title="IoT Trust Dashboard", layout="wide")

# URL of the backend blockchain API
API_URL = "http://127.0.0.1:5000/api/blockchain"
DATASET_INFO_URL = "http://127.0.0.1:5000/api/dataset_info"

# --- SIDEBAR: Dataset Source Warning ---
with st.sidebar:
    st.markdown("## ℹ️ Dataset Info")
    try:
        ds_resp = requests.get(DATASET_INFO_URL, timeout=2)
        if ds_resp.status_code == 200:
            ds_info = ds_resp.json()
            source = ds_info.get("source", "unknown")
            rows   = ds_info.get("rows", 0)
            if "Intel" in source:
                st.success(f"✅ **Active Dataset**  \n`Intel Lab IoT`  \n{rows:,} rows loaded")
            elif "Fallback" in source:
                st.warning(f"⚠️ **Fallback Dataset in use**  \n`sensor_dataset.csv`  \nIntel file not found.")
            else:
                st.error(f"🚨 **Random Generator Active**  \nNo CSV files found. Data is synthetic.")
        else:
            st.warning("⚠️ Could not fetch dataset info from backend.")
    except Exception:
        st.warning("⚠️ Backend unreachable — dataset status unknown.")

st.title("🛡️ IoT Trust & Reputation Dashboard")
st.markdown("Visualizing real-time sensor data, composite trust scores, and time-weighted reputation.")

# Placeholder for auto-refresh
placeholder = st.empty()

def fetch_data():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            chain = response.json()
            # Extract data from blocks
            records = []
            for block in chain:
                if 'data' in block and isinstance(block['data'], dict):
                    rec = dict(block['data'])
                    rec['block_index'] = block.get('index')
                    rec['proof'] = block.get('proof')
                    rec['previous_hash'] = block.get('previous_hash')
                    records.append(rec)
            return records, chain
        return [], []
    except Exception as e:
        st.error(f"Error fetching data from API: {e}")
        return [], []

# Auto-refresh loop
while True:
    records, chain = fetch_data()
    
    with placeholder.container():
        if records:
            df = pd.DataFrame(records)
            
            # Ensure required columns are present
            required_cols = ['timestamp', 'sensor_id', 'temperature', 'humidity', 'trust_status', 'confidence', 'composite_score', 'reputation']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filter valid (more recent first for tables, chronological for charts)
            df = df.sort_values(by='timestamp', ascending=False)
            
            # --- TOP METRICS ---
            st.subheader("Latest Readings Quick View")
            col1, col2, col3, col4, col5 = st.columns(5)
            latest = df.iloc[0]
            
            col1.metric("Latest Sensor", latest['sensor_id'])
            col2.metric("Trust Status", latest['trust_status'])
            col3.metric("Composite Score", f"{latest['composite_score']:.2f}" if pd.notnull(latest['composite_score']) else "N/A")
            col4.metric("Reputation", f"{latest['reputation']:.2f}" if pd.notnull(latest['reputation']) else "N/A")
            col5.metric("Block #", latest['block_index'])
            
            # --- CHARTS ---
            st.markdown("---")
            st.subheader("Metrics Timeline (Chronological)")
            
            # Sort ascending for charts
            chart_df = df.sort_values(by='timestamp', ascending=True)
            
            row1_col1, row1_col2 = st.columns(2)
            
            with row1_col1:
                st.markdown("**🛡️ Composite Trust Score over Time**")
                trust_chart = alt.Chart(chart_df).mark_line(point=True).encode(
                    x='timestamp:T',
                    y=alt.Y('composite_score:Q', scale=alt.Scale(domain=[0, 1])),
                    color='sensor_id:N',
                    tooltip=['timestamp', 'sensor_id', 'composite_score', 'trust_status']
                ).interactive()
                st.altair_chart(trust_chart, use_container_width=True)
                
            with row1_col2:
                st.markdown("**⭐ Time-weighted Reputation**")
                rep_chart = alt.Chart(chart_df).mark_line(interpolate='step-after').encode(
                    x='timestamp:T',
                    y=alt.Y('reputation:Q', scale=alt.Scale(domain=[0, 1])),
                    color='sensor_id:N',
                    tooltip=['timestamp', 'sensor_id', 'reputation']
                ).interactive()
                st.altair_chart(rep_chart, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Data Table")
            st.dataframe(df.style.map(lambda v: 'color: red;' if 'Malicious' in str(v) else ('color: green;' if 'Trusted' in str(v) else ''), subset=['trust_status']))
            
            # --- BLOCKCHAIN DETAILS ---
            st.markdown("---")
            st.subheader("⛓️ Blockchain Ledger")
            with st.expander("View Block Details & Raw JSON", expanded=True):
                blocks_info = []
                for b in chain:
                    b_data = b.get("data", {})
                    blocks_info.append({
                        "Block #": b.get("index"),
                        "Mined Timestamp": b.get("timestamp"),
                        "Proof": b.get("proof"),
                        "Previous Hash": b.get("previous_hash")[:15] + "..." if isinstance(b.get("previous_hash"), str) and len(b.get("previous_hash")) > 15 else b.get("previous_hash"),
                        "Sensor Node": b_data.get("sensor_id") if isinstance(b_data, dict) else "Genesis/None",
                        "Decision": b_data.get("trust_status") if isinstance(b_data, dict) else "N/A"
                    })
                st.dataframe(pd.DataFrame(blocks_info).sort_values(by="Block #", ascending=False), use_container_width=True)
            
        else:
            st.warning("No data found in the blockchain. Ensure backend and sensor simulator are running.")
            
    time.sleep(2) # Refresh every 2 seconds
