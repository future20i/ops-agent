import streamlit as st
import time
import uuid

st.set_page_config(page_title="运维 Agent 驾驶舱", layout="wide")

# ============================================================
# 模拟 VPC 数据（session_state 持久化，跨交互保留新建的 VPC）
# ============================================================
if "vpcs" not in st.session_state:
    st.session_state.vpcs = {
        "us-east-1": [
            {"VPC ID": "vpc-0a1b2c3d4e5f67890", "CIDR": "10.0.0.0/16", "State": "available", "IsDefault": True},
            {"VPC ID": "vpc-1b2c3d4e5f67890ab", "CIDR": "172.31.0.0/16", "State": "available", "IsDefault": False},
            {"VPC ID": "vpc-2c3d4e5f67890abc1", "CIDR": "192.168.0.0/24", "State": "available", "IsDefault": False},
        ],
        "us-west-2": [
            {"VPC ID": "vpc-3d4e5f67890abcd2", "CIDR": "10.1.0.0/16", "State": "available", "IsDefault": True},
            {"VPC ID": "vpc-4e5f67890abcde34", "CIDR": "10.100.0.0/16", "State": "available", "IsDefault": False},
        ],
        "ap-northeast-1": [
            {"VPC ID": "vpc-5f67890abcdef56", "CIDR": "10.2.0.0/16", "State": "available", "IsDefault": True},
            {"VPC ID": "vpc-67890abcdef6789", "CIDR": "10.3.0.0/16", "State": "available", "IsDefault": False},
            {"VPC ID": "vpc-7890abcdef789ab", "CIDR": "10.200.0.0/16", "State": "available", "IsDefault": False},
            {"VPC ID": "vpc-890abcdef789abc", "CIDR": "172.20.0.0/16", "State": "available", "IsDefault": False},
        ],
    }

if "deploy_log" not in st.session_state:
    st.session_state.deploy_log = []

# ============================================================
# 侧边栏 —— 控制面板
# ============================================================
st.sidebar.markdown("## 🌍 地区设置")
region = st.sidebar.selectbox("选择云地区", list(st.session_state.vpcs.keys()))

st.sidebar.divider()
st.sidebar.markdown("## 🏗️ 创建新 VPC")

with st.sidebar.form("create_vpc_form"):
    cidr = st.text_input("CIDR 地址块", placeholder="例如 10.50.0.0/16", value="10.50.0.0/16")
    vpc_name = st.text_input("VPC 名称（可选）", placeholder="my-production-vpc")
    submitted = st.form_submit_button("🚀 一键部署 VPC", use_container_width=True, type="primary")

    if submitted:
        if not cidr:
            st.sidebar.error("CIDR 不能为空")
        else:
            # 模拟部署过程
            deploy_id = str(uuid.uuid4())[:12]
            new_vpc_id = f"vpc-{deploy_id}"
            
            with st.spinner(f"⏳ 正在 {region} 创建 VPC..."):
                time.sleep(1.2)  # 模拟 API 调用延迟
                new_vpc = {
                    "VPC ID": new_vpc_id,
                    "CIDR": cidr,
                    "State": "available",
                    "IsDefault": False,
                    "Name": vpc_name if vpc_name else f"vpc-{deploy_id[:8]}",
                }
                st.session_state.vpcs[region].append(new_vpc)
                timestamp = time.strftime("%H:%M:%S")
                st.session_state.deploy_log.insert(0, {
                    "time": timestamp,
                    "region": region,
                    "vpc_id": new_vpc_id,
                    "cidr": cidr,
                    "status": "✅ 部署成功",
                })
            
            st.sidebar.success(f"✅ VPC 创建成功！\n\n`{new_vpc_id}` → {cidr}")
            st.balloons()

# ============================================================
# 主面板
# ============================================================
st.title("🚀 AWS 运维 Agent - 资产仪表盘")

# ---- VPC 列表 ----
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"📋 {region} — VPC 资产清单")
with col2:
    if st.button("🔄 刷新列表", use_container_width=True):
        pass  # session_state 自动持久化，刷新只是重新渲染

vpcs = st.session_state.vpcs.get(region, [])
if vpcs:
    st.success(f"共 **{len(vpcs)}** 个 VPC")
    st.table(vpcs)
else:
    st.warning("该地区暂无 VPC")

# ---- 部署日志 ----
st.divider()
st.subheader("📜 部署操作日志")
if st.session_state.deploy_log:
    st.dataframe(
        st.session_state.deploy_log,
        column_config={
            "time": "时间",
            "region": "地区",
            "vpc_id": "VPC ID",
            "cidr": "CIDR",
            "status": "状态",
        },
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("暂无部署记录 — 在左侧创建你的第一个 VPC！")
