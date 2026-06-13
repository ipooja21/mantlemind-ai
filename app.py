import time, os, sys
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="MantleMind AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pipeline import MantleMindPipeline
from new_ui_sections import (
    inject_glassmorphism_css,
    render_reasoning_chain,
    render_agent_voting,
    render_wallet_clusters,
    render_mev_alerts,
    render_predictive_accuracy,
    render_wallet_network_graph,
)
from mission_control import (
    inject_world_class_css,
    render_agent_pulse_strip,
    render_empty_state,
    render_live_badge,
)

inject_glassmorphism_css()
inject_world_class_css()


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif;}
.stApp{background:#030D1A;color:#E2E8F0;}
section[data-testid="stSidebar"]{background:#060F1E!important;border-right:1px solid #0F2540;}
.metric-card{background:linear-gradient(135deg,#071428,#0A1E35);border:1px solid #0E2A45;border-radius:12px;padding:20px 24px;position:relative;overflow:hidden;}
.metric-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#00C2B2,#0080FF);}
.metric-label{font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#5A7A9A;margin-bottom:8px;}
.metric-value{font-size:28px;font-weight:700;color:#E2E8F0;font-family:'JetBrains Mono',monospace;}
.metric-delta{font-size:12px;color:#00C2B2;margin-top:4px;}
.signal-badge{display:inline-block;padding:4px 14px;border-radius:20px;font-size:12px;font-weight:700;letter-spacing:1px;}
.signal-STRONG_BULL{background:#003322;color:#00E676;border:1px solid #00E676;}
.signal-BULL{background:#002215;color:#69F0AE;border:1px solid #69F0AE;}
.signal-NEUTRAL{background:#1A1A00;color:#FFD600;border:1px solid #FFD600;}
.signal-BEAR{background:#1A0800;color:#FF9800;border:1px solid #FF9800;}
.signal-STRONG_BEAR{background:#200000;color:#F44336;border:1px solid #F44336;}
.alert-item{background:#060F1E;border-left:3px solid #00C2B2;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:8px;font-size:12px;}
.alert-WHALE{border-left-color:#00C2B2;}
.alert-ANOMALY{border-left-color:#FF9800;}
.alert-ALPHA{border-left-color:#7C4DFF;}
.section-header{font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:#5A7A9A;border-bottom:1px solid #0F2540;padding-bottom:8px;margin-bottom:16px;}
.chat-bubble-user{background:#0A1E35;border-radius:12px 12px 0 12px;padding:10px 14px;margin:6px 0;font-size:13px;color:#E2E8F0;border:1px solid #0E2A45;}
.chat-bubble-ai{background:linear-gradient(135deg,#071428,#0A2540);border-radius:12px 12px 12px 0;padding:10px 14px;margin:6px 0;font-size:13px;color:#B0C4DE;border:1px solid #00C2B2;}
#MainMenu,footer,header{visibility:hidden;}
.stDeployButton{display:none;}
.stButton>button{background:linear-gradient(135deg,#00C2B2,#0080FF);color:white;border:none;border-radius:8px;font-weight:600;}
.stButton>button:hover{background:linear-gradient(135deg,#00D9C7,#1A90FF);transform:translateY(-1px);}
</style>
""", unsafe_allow_html=True)


if "pipeline" not in st.session_state:
    with st.spinner("Initialising MantleMind AI — 10 agents loading…"):
        st.session_state.pipeline  = MantleMindPipeline()
        st.session_state.state     = None
        st.session_state.chat_hist = []

pipeline: MantleMindPipeline = st.session_state.pipeline

def _sig_color(s):
    return {"STRONG_BULL":"#00E676","BULL":"#69F0AE","NEUTRAL":"#FFD600","BEAR":"#FF9800","STRONG_BEAR":"#F44336"}.get(s,"#8A9BB0")

def fmt_ts(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:10px 0 20px 0;'>
      <div style='font-size:32px;'>🧠</div>
      <div style='font-size:20px;font-weight:700;color:#00C2B2;'>MantleMind AI</div>
      <div style='font-size:11px;color:#5A7A9A;'>On-Chain Intelligence Platform</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">⚙️ CONFIGURATION</div>', unsafe_allow_html=True)
    n_blocks         = st.slider("Blocks per scan", 5, 50, 20, 5)
    auto_refresh     = st.checkbox("Auto-refresh", value=False)
    refresh_interval = st.select_slider("Interval (s)", [15,30,60,120], value=30)

    st.markdown("---")
    st.markdown('<div class="section-header">🔔 THRESHOLDS</div>', unsafe_allow_html=True)
    whale_thresh = st.number_input("Whale threshold (MNT)", value=1000, step=500)
    alpha_thresh = st.slider("Alpha alert threshold", 50, 95, 75)

    st.markdown("---")
    run_btn = st.button("🔄 Run Analysis", use_container_width=True)
    st.markdown("---")

    if st.session_state.state:
        ns = st.session_state.state.get("network_stats", {})
        col = "#00E676" if ns.get("connected") else "#FF9800"
        st.markdown(f"""
        <div style='text-align:center;'>
          <div style='font-size:10px;color:#5A7A9A;'>NETWORK STATUS</div>
          <div style='font-size:14px;font-weight:700;color:{col};'>⬤ MANTLE LIVE</div>
          <div style='font-size:11px;color:#5A7A9A;'>Chain ID: 5000</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:10px;color:#3A5A7A;text-align:center;'>
      🏆 Mantle Turing Test 2026<br>
      Track: AI Alpha & Data<br>
      10-Agent Architecture
    </div>""", unsafe_allow_html=True)

if auto_refresh:
    import streamlit_autorefresh as sar
    sar.st_autorefresh(interval=refresh_interval*1000, key="auto")


if run_btn or st.session_state.state is None:
    with st.spinner("🧠 Running 10-agent on-chain analysis…"):
        st.session_state.state = pipeline.run(n_blocks=n_blocks)

state            = st.session_state.state
df               = state["df"]
net_stats        = state["network_stats"]
anom_summary     = state["anomaly_summary"]
whale_alerts     = state["whale_alerts"]
whale_summary    = state["whale_summary"]
alpha            = state["alpha"]
recent_alerts    = state["recent_alerts"]
alpha_history    = state["alpha_history"]
watchlist_alerts = state.get("watchlist_alerts", [])
wallet_clusters  = state.get("wallet_clusters", [])
mev_alerts       = state.get("mev_alerts", [])


latest_block = net_stats.get("latest_block", 0)
st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;padding:12px 0 4px 0;'>
  <div>
    <span style='font-size:26px;font-weight:700;color:#00C2B2;'>MantleMind AI</span>
    <span style='font-size:14px;color:#5A7A9A;margin-left:12px;'>On-Chain Intelligence · 10-Agent System</span>
  </div>
  <div style='text-align:right;font-size:12px;color:#5A7A9A;'>
    Last run: <b style='color:#E2E8F0;'>{fmt_ts(state["run_timestamp"])}</b> &nbsp;·&nbsp;
    Time: <b style='color:#00C2B2;'>{state.get("elapsed",0)}s</b> &nbsp;·&nbsp;
    Block: <b style='color:#E2E8F0;'>{latest_block:,}</b>
  </div>
</div>""", unsafe_allow_html=True)

render_live_badge()
render_agent_pulse_strip(state)

st.markdown("<br>", unsafe_allow_html=True)


k1,k2,k3,k4,k5,k6 = st.columns(6)
kpis = [
    (k1,"LATEST BLOCK",   f"{latest_block:,}",                              "Mantle Mainnet"),
    (k2,"TRANSACTIONS",   f"{len(df):,}",                                    f"Last {n_blocks} blocks"),
    (k3,"WHALE WALLETS",  f"{len(whale_alerts)}",                            f"{whale_summary.get('total_volume_mnt',0):,.0f} MNT"),
    (k4,"ANOMALIES",      f"{anom_summary.get('total_anomalies',0)}",        f"Rate: {anom_summary.get('anomaly_rate',0):.1f}%"),
    (k5,"CRITICAL TXS",   f"{anom_summary.get('critical_count',0)}",         "High risk"),
    (k6,"GAS PRICE",      f"{net_stats.get('gas_price_gwei',0):.4f}",        "Gwei"),
]
for col,label,value,sub in kpis:
    with col:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-delta">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


col_alpha, col_chart = st.columns([1,2])

with col_alpha:
    score     = alpha["alpha_score"]
    signal    = alpha["signal"]
    sig_color = _sig_color(signal)

    fig_g = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        domain={"x":[0,1],"y":[0,1]},
        title={"text":"Alpha Score","font":{"color":"#8A9BB0","size":14}},
        number={"font":{"color":sig_color,"size":48,"family":"JetBrains Mono"}},
        gauge={
            "axis":{"range":[0,100],"tickcolor":"#5A7A9A","tickfont":{"color":"#5A7A9A"}},
            "bar":{"color":sig_color,"thickness":0.25},
            "bgcolor":"#071428","bordercolor":"#0E2A45",
            "steps":[
                {"range":[0,20],"color":"#200000"},{"range":[20,40],"color":"#1A0800"},
                {"range":[40,60],"color":"#141400"},{"range":[60,80],"color":"#002215"},
                {"range":[80,100],"color":"#003322"},
            ],
            "threshold":{"line":{"color":sig_color,"width":3},"thickness":0.75,"value":score},
        },
    ))
    fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                        font={"color":"#E2E8F0"},margin=dict(l=20,r=20,t=40,b=20),height=250)
    st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar":False})

    st.markdown(f"""
    <div style='text-align:center;'>
      <span class='signal-badge signal-{signal}'>{alpha.get("emoji","")} {signal.replace("_"," ")}</span>
      <div style='font-size:11px;color:#5A7A9A;margin-top:6px;'>Confidence: {alpha.get("confidence","Medium")}</div>
    </div>""", unsafe_allow_html=True)

    render_predictive_accuracy(alpha["alpha_score"], alpha["signal"])

    st.markdown("<br>", unsafe_allow_html=True)
    comps = alpha.get("components", {})
    comp_labels = {
        "whale_signal":"🐋 Whale Signal","volume_trend":"📊 Volume Trend",
        "gas_momentum":"⛽ Gas Momentum","contract_activity":"📝 Contracts",
        "anomaly_penalty":"⚠️ Anomaly Penalty",
    }
    for key,label in comp_labels.items():
        val = min(comps.get(key,0), 100)
        bar_color = "#F44336" if key=="anomaly_penalty" else "#00C2B2"
        st.markdown(f"""
        <div style='margin-bottom:6px;'>
          <div style='display:flex;justify-content:space-between;font-size:11px;color:#8A9BB0;'>
            <span>{label}</span>
            <span style='color:#E2E8F0;font-family:JetBrains Mono;'>{val:.0f}</span>
          </div>
          <div style='background:#0A1628;border-radius:3px;height:4px;'>
            <div style='background:{bar_color};width:{val}%;height:4px;border-radius:3px;'></div>
          </div>
        </div>""", unsafe_allow_html=True)

with col_chart:
    if "value_mnt" in df.columns and len(df) > 0:
        fig_v = go.Figure()
        if "is_whale_tx" in df.columns:
            norm  = df[df["is_whale_tx"]==False]["value_mnt"]
            whale = df[df["is_whale_tx"]==True]["value_mnt"]
            fig_v.add_trace(go.Histogram(x=np.log1p(norm),  name="Normal", marker_color="#0080FF",opacity=0.7,nbinsx=40))
            fig_v.add_trace(go.Histogram(x=np.log1p(whale), name="Whale",  marker_color="#00C2B2",opacity=0.9,nbinsx=40))
        else:
            fig_v.add_trace(go.Histogram(x=np.log1p(df["value_mnt"]),marker_color="#00C2B2",opacity=0.8,nbinsx=40))
        fig_v.update_layout(
            title=dict(text="Transaction Value Distribution (log scale)",font=dict(size=13,color="#8A9BB0")),
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#071428",barmode="overlay",
            font=dict(color="#8A9BB0"),xaxis=dict(gridcolor="#0A1E35",title="log(1+MNT)"),
            yaxis=dict(gridcolor="#0A1E35"),legend=dict(bgcolor="rgba(0,0,0,0)"),
            height=280,margin=dict(l=0,r=0,t=40,b=40),
        )
        st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar":False})

    if alpha_history is not None and len(alpha_history) > 1:
        ah = alpha_history.copy()
        ah["time"] = pd.to_datetime(ah["timestamp"],unit="s").dt.strftime("%H:%M")
        fig_h = go.Figure()
        fig_h.add_hrect(y0=80,y1=100,fillcolor="rgba(0,230,118,0.05)",line_width=0)
        fig_h.add_hrect(y0=0, y1=20, fillcolor="rgba(244,67,54,0.05)", line_width=0)
        fig_h.add_trace(go.Scatter(
            x=ah["time"],y=ah["alpha_score"],mode="lines+markers",
            line=dict(color="#00C2B2",width=2.5),marker=dict(size=5,color="#00C2B2"),
            fill="tozeroy",fillcolor="rgba(0,194,178,0.08)",
        ))
        fig_h.update_layout(
            title=dict(text="Alpha Score History",font=dict(size=13,color="#8A9BB0")),
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#071428",
            font=dict(color="#8A9BB0"),xaxis=dict(gridcolor="#0A1E35"),
            yaxis=dict(gridcolor="#0A1E35",range=[0,100]),
            height=220,margin=dict(l=0,r=0,t=40,b=20),showlegend=False,
        )
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar":False})


st.markdown('<div class="section-header">💡 AI INSIGHTS — AGENT 7 (AI)</div>', unsafe_allow_html=True)
st.markdown(f"""
<div style='background:linear-gradient(135deg,#071428,#0A1E35);border:1px solid #0E2A45;
            border-radius:12px;padding:20px 24px;border-left:4px solid #00C2B2;'>
  <pre style='font-family:Space Grotesk,sans-serif;white-space:pre-wrap;
              font-size:13px;color:#B0C4DE;margin:0;line-height:1.7;'>{alpha.get("narrative","")}</pre>
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


render_reasoning_chain(
    alpha_score=alpha["alpha_score"],
    signal=alpha["signal"],
    whale_count=len(whale_alerts),
    anomaly_count=anom_summary.get("total_anomalies", 0),
    tx_count=len(df),
)

st.markdown("<br>", unsafe_allow_html=True)


render_agent_voting(
    alpha_score=alpha["alpha_score"],
    signal=alpha["signal"],
    whale_count=len(whale_alerts),
    anomaly_count=anom_summary.get("total_anomalies", 0),
    components=alpha.get("components", {}),
)

st.markdown("<br>", unsafe_allow_html=True)


st.markdown('<div class="section-header">💬 AI CHAT — ASK MANTLEMIND</div>', unsafe_allow_html=True)
col_chat1, col_chat2 = st.columns([3,1])
with col_chat1:
    user_q = st.text_input("Ask about current on-chain data", placeholder="e.g. What are the top risks right now?", label_visibility="collapsed")
with col_chat2:
    ask_btn = st.button("Ask AI 🤖", use_container_width=True)

if ask_btn and user_q:
    with st.spinner("AI analyzing…"):
        answer = pipeline.chat(user_q)
        st.session_state.chat_hist.append({"q": user_q, "a": answer})

for item in reversed(st.session_state.chat_hist[-5:]):
    st.markdown(f'<div class="chat-bubble-user">🧑 {item["q"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chat-bubble-ai">🤖 {item["a"]}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


col_w, col_a = st.columns(2)
with col_w:
    st.markdown('<div class="section-header">🐋 WHALE ACTIVITY — AGENT 3</div>', unsafe_allow_html=True)
    if whale_alerts:
        rows = []
        for w in sorted(whale_alerts, key=lambda x: x.get("score",0), reverse=True)[:15]:
            rows.append({
                "Address":    w.get("address","")[:16]+"…",
                "Tier":       w.get("tier",""),
                "Pattern":    w.get("pattern",""),
                "Volume MNT": f"{w.get('total_mnt',0):,.0f}",
                "Score":      w.get("score",0),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     column_config={"Score":st.column_config.ProgressColumn("Score",min_value=0,max_value=100)})
    else:
        render_empty_state("🐋", "Quiet waters",
            f"No wallets crossed the {whale_thresh:,} MNT threshold in this scan.")

with col_a:
    st.markdown('<div class="section-header">⚠️ TOP ANOMALIES — AGENT 2</div>', unsafe_allow_html=True)
    top_anoms = anom_summary.get("top_anomalies",[])
    if top_anoms:
        st.dataframe(pd.DataFrame(top_anoms), use_container_width=True, hide_index=True,
                     column_config={"anomaly_score":st.column_config.ProgressColumn("Score",min_value=0,max_value=1)})
    else:
        render_empty_state("🛡️", "All clear",
            "No anomalies above threshold in this scan — Agent 2's Isolation Forest model found nothing unusual.")


st.markdown("<br>", unsafe_allow_html=True)
render_wallet_network_graph()


st.markdown("<br>", unsafe_allow_html=True)
render_wallet_clusters()


st.markdown("<br>", unsafe_allow_html=True)
render_mev_alerts()


st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">👁️ SMART MONEY WATCHLIST — AGENT 8</div>', unsafe_allow_html=True)
col_wl1, col_wl2 = st.columns([1,2])
with col_wl1:
    new_addr  = st.text_input("Wallet Address", placeholder="0x...")
    new_label = st.text_input("Label", placeholder="Smart Money #1")
    if st.button("➕ Add to Watchlist", use_container_width=True):
        if new_addr.startswith("0x") and len(new_addr) >= 20:
            pipeline.watchlist_agent.add_wallet(new_addr, new_label)
            st.success("Added: " + (new_label or new_addr[:16]))
        else:
            st.error("Valid 0x address daalo")
with col_wl2:
    all_watched = pipeline.watchlist_agent.get_all()
    st.markdown(f"**Tracked:** {len(all_watched)} wallets &nbsp;·&nbsp; **Hits this scan:** {len(watchlist_alerts)}", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if watchlist_alerts:
        for hit in watchlist_alerts:
            st.markdown(f"""
            <div class="alert-item alert-WHALE">
              <b style='color:#00C2B2;'>{hit['label']}</b> &nbsp;·&nbsp;
              {hit['tx_count']} txns &nbsp;·&nbsp;
              <span style='color:#E2E8F0;'>{hit['total_eth']:,.4f} MNT</span>
              <span style='float:right;color:#5A7A9A;'>{hit['time']}</span>
            </div>""", unsafe_allow_html=True)
    elif all_watched:
        render_empty_state("👁️", "Watching quietly", "Your tracked wallets had no activity in this scan.")
    else:
        render_empty_state("➕", "Start tracking", "Add a wallet address above to follow smart money in real time.")


st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">⚡ LIVE TRANSACTION FEED — AGENT 1</div>', unsafe_allow_html=True)
if not df.empty:
    display_cols = ["block_number","tx_hash","from_address","to_address","value_mnt","gas_price_gwei","is_contract_call"]
    for c in ["anomaly_score","risk_level","is_whale_tx"]:
        if c in df.columns: display_cols.append(c)
    feed_df = df[[c for c in display_cols if c in df.columns]].tail(50).copy()
    feed_df["tx_hash"]      = feed_df["tx_hash"].apply(lambda x: str(x)[:18]+"…")
    feed_df["from_address"] = feed_df["from_address"].apply(lambda x: str(x)[:14]+"…")
    feed_df["to_address"]   = feed_df["to_address"].apply(lambda x: str(x)[:14]+"…")
    feed_df["value_mnt"]    = feed_df["value_mnt"].round(4)
    st.dataframe(feed_df, use_container_width=True, hide_index=True, height=300)


if "risk_level" in df.columns and len(df) > 0:
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        rc = df["risk_level"].value_counts().reset_index()
        rc.columns = ["Risk Level","Count"]
        order = ["LOW","MEDIUM","HIGH","CRITICAL"]
        rc["Risk Level"] = pd.Categorical(rc["Risk Level"],categories=order,ordered=True)
        rc = rc.sort_values("Risk Level")
        fig_r = go.Figure(go.Bar(
            x=rc["Risk Level"].astype(str), y=rc["Count"],
            marker_color=["#00E676","#FFD600","#FF9800","#F44336"][:len(rc)],
            text=rc["Count"], textposition="outside", textfont=dict(color="#E2E8F0"),
        ))
        fig_r.update_layout(
            title=dict(text="Risk Level Distribution",font=dict(size=13,color="#8A9BB0")),
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#071428",
            font=dict(color="#8A9BB0"),xaxis=dict(gridcolor="#0A1E35"),yaxis=dict(gridcolor="#0A1E35"),
            height=280,margin=dict(l=0,r=0,t=40,b=20),showlegend=False,
        )
        st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar":False})
    with col_r2:
        if whale_alerts and all("tier" in w for w in whale_alerts):
            tc = pd.Series([w["tier"] for w in whale_alerts]).value_counts()
            fig_p = go.Figure(go.Pie(
                labels=tc.index.tolist(), values=tc.values.tolist(),
                hole=0.55, marker_colors=["#00C2B2","#0080FF","#7C4DFF"],
                textfont=dict(color="#E2E8F0"),
            ))
            fig_p.update_layout(
                title=dict(text="Whale Tier Breakdown",font=dict(size=13,color="#8A9BB0")),
                paper_bgcolor="rgba(0,0,0,0)",font=dict(color="#8A9BB0"),
                height=280,margin=dict(l=0,r=0,t=40,b=20),legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_p, use_container_width=True, config={"displayModeBar":False})


st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">🔔 ALERT HISTORY — AGENT 5</div>', unsafe_allow_html=True)
if recent_alerts:
    for alert in recent_alerts[:10]:
        atype = alert.get("type","INFO")
        ts    = fmt_ts(alert.get("timestamp", int(time.time())))
        msg   = alert.get("message","")[:120]
        icon  = {"WHALE":"🐋","ANOMALY":"⚠️","ALPHA":"🎯","TEST":"🧪"}.get(atype,"ℹ️")
        bc    = {"WHALE":"#00C2B2","ANOMALY":"#FF9800","ALPHA":"#7C4DFF"}.get(atype,"#5A7A9A")
        st.markdown(f"""
        <div class="alert-item alert-{atype}">
          <span style='font-size:11px;color:#5A7A9A;'>{ts}</span>
          <span style='margin:0 8px;font-size:11px;font-weight:700;color:{bc};'>{icon} {atype}</span>
          <span style='font-size:12px;color:#B0C4DE;'>{msg}</span>
        </div>""", unsafe_allow_html=True)
else:
    render_empty_state("🔔", "No alerts yet", "Run analysis to start generating real-time Telegram & Discord alerts.")


st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">📥 DOWNLOAD REPORTS — AGENT 6</div>', unsafe_allow_html=True)
col_pdf, col_xls, col_info = st.columns([1,1,2])
with col_pdf:
    if st.button("📄 Generate PDF", use_container_width=True):
        with st.spinner("Generating…"):
            r = pipeline.generate_reports()
            if r["pdf"]:
                st.download_button("⬇️ Download PDF", data=r["pdf"],
                    file_name="MantleMind_"+datetime.now().strftime("%Y%m%d_%H%M")+".pdf",
                    mime="application/pdf", use_container_width=True)
with col_xls:
    if st.button("📊 Generate Excel", use_container_width=True):
        with st.spinner("Generating…"):
            r = pipeline.generate_reports()
            if r["excel"]:
                st.download_button("⬇️ Download Excel", data=r["excel"],
                    file_name="MantleMind_"+datetime.now().strftime("%Y%m%d_%H%M")+".xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
with col_info:
    st.markdown("""
    <div style='font-size:12px;color:#5A7A9A;padding-top:8px;'>
      PDF: Investor-ready report with all 10 agent outputs.<br>
      Excel: Raw data for quantitative analysis.
    </div>""", unsafe_allow_html=True)


st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(f"""
<div style='border-top:1px solid #0F2540;padding-top:16px;text-align:center;font-size:11px;color:#3A5A7A;'>
  MantleMind AI &nbsp;·&nbsp; 10-Agent On-Chain Intelligence &nbsp;·&nbsp;
  Mantle Turing Test Hackathon 2026 &nbsp;·&nbsp;
  Track: AI Alpha &amp; Data &nbsp;·&nbsp;
  Block: {latest_block:,} &nbsp;·&nbsp;
  Built with 🧠 by MantleMind Team
</div>""", unsafe_allow_html=True)