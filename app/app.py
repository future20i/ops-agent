import streamlit as st
import time
import uuid
import json

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
# 部署处理函数
# ============================================================

def _handle_mock_deploy(cidr: str, vpc_name: str, region: str):
    """模拟模式部署"""
    deploy_id = str(uuid.uuid4())[:12]
    new_vpc_id = f"vpc-{deploy_id}"

    with st.spinner(f"⏳ 正在 {region} 模拟创建 VPC..."):
        time.sleep(1.2)
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
            "status": "✅ 模拟部署成功",
        })

    st.sidebar.success(f"✅ VPC 创建成功！\n\n`{new_vpc_id}` → {cidr}")
    st.balloons()


def _handle_terraform_deploy(cidr: str, vpc_name: str, region: str):
    """Terraform 模式：治理检查 → init → plan → 策略审核 → apply"""
    from app.utils.network import validate_network_plan
    from app.utils.terraform_executor import TerraformExecutor
    from app.agents.governance import GovernanceEngine
    from app.agents.llm_advisor import LLMAdvisor

    governance = GovernanceEngine()
    advisor = LLMAdvisor()

    # 1. 治理策略检查（部署前）
    existing_cidrs = [v["CIDR"] for v in st.session_state.vpcs.get(region, [])]
    config = {
        "enable_dns_support": True,
        "tags": {
            "Environment": "ops-agent",
            "ManagedBy": "ops-agent",
        } if vpc_name else {},
    }

    report = governance.check_vpc_deploy(cidr, existing_cidrs, config)

    if report.violations:
        st.warning(f"⚠️ 治理检查发现 {len(report.violations)} 个问题")

        for v in report.violations:
            severity_icon = "🚫" if v.rule.severity == "block" else "⚠️"
            with st.expander(
                f"{severity_icon} [{v.rule.resource}] {v.rule.name} — {v.rule.severity.upper()}",
                expanded=(v.rule.severity == "block"),
            ):
                st.markdown(f"**规则**: {v.rule.description}")
                st.markdown(f"**详情**: {v.detail}")
                st.markdown(f"**建议**: {v.suggestion}")

                # LLM 智能分析
                with st.spinner("🤖 AI 分析中..."):
                    analysis = advisor.analyze_violation(v.rule.name, v.detail)
                st.info(f"🤖 **AI 分析**\n\n{analysis}")

        if not report.passed:
            st.error("❌ 存在 block 级别的规则违反，部署已拦截")
            st.sidebar.error("❌ 治理检查未通过，部署已拦截")
            return

    # 2. Terraform init
    with st.spinner("🔧 初始化 Terraform（首次需下载 AWS Provider，约 60s）..."):
        tf = TerraformExecutor("infrastructure/modules/vpc")
        init_result = tf.init()
        if not init_result.success:
            st.sidebar.error("Terraform init 失败")
            st.error(f"```\n{init_result.output[-1000:]}\n```")
            return

    # 3. Terraform plan
    with st.spinner("📋 生成执行计划（terraform plan）..."):
        plan_result = tf.plan({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
        })
        if not plan_result.success:
            st.sidebar.error("Terraform plan 失败")
            # LLM 分析 plan 错误
            with st.spinner("🤖 AI 分析错误..."):
                analysis = advisor.analyze_terraform_error(plan_result.output)
            st.info(f"🤖 **AI 诊断**\n\n{analysis}")
            st.error(f"```\n{plan_result.output[-2000:]}\n```")
            return

    # 显示 plan 摘要
    with st.expander("📋 Terraform Plan 详情", expanded=False):
        st.code(plan_result.output[-3000:], language="terraform")

    # 4. Terraform apply
    with st.spinner("🚀 执行部署（terraform apply）..."):
        apply_result = tf.apply({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
        })

    if apply_result.success:
        new_vpc = {
            "VPC ID": apply_result.vpc_id or "pending",
            "CIDR": cidr,
            "State": "available",
            "IsDefault": False,
            "Name": vpc_name or "ops-agent",
        }
        st.session_state.vpcs[region].append(new_vpc)
        timestamp = time.strftime("%H:%M:%S")
        st.session_state.deploy_log.insert(0, {
            "time": timestamp,
            "region": region,
            "vpc_id": new_vpc["VPC ID"],
            "cidr": cidr,
            "status": "✅ Terraform 部署成功",
        })
        st.sidebar.success(f"✅ Terraform 部署成功！\n\n`{new_vpc['VPC ID']}` → {cidr}")
        st.balloons()

        with st.expander("📜 Terraform Apply 日志", expanded=False):
            st.code(apply_result.output[-3000:], language="terraform")
    else:
        # LLM 分析 apply 错误
        with st.spinner("🤖 AI 分析错误..."):
            analysis = advisor.analyze_terraform_error(apply_result.output)
        st.info(f"🤖 **AI 诊断**\n\n{analysis}")
        st.error(f"```\n{apply_result.output[-2000:]}\n```")
        st.sidebar.error("Terraform apply 失败")


# ============================================================
# 侧边栏 —— 控制面板
# ============================================================
st.sidebar.markdown("## ⚙️ 部署引擎")
deploy_mode = st.sidebar.radio(
    "选择部署模式",
    ["🧪 模拟模式", "🏗️ Terraform 模式"],
    horizontal=True,
)
use_terraform = (deploy_mode == "🏗️ Terraform 模式")

st.sidebar.divider()
st.sidebar.markdown("## 🌍 地区设置")
region = st.sidebar.selectbox("选择云地区", list(st.session_state.vpcs.keys()))

st.sidebar.divider()
st.sidebar.markdown("## 🏗️ 创建新 VPC")

with st.sidebar.form("create_vpc_form"):
    cidr = st.text_input("CIDR 地址块", placeholder="例如 10.50.0.0/16", value="10.50.0.0/16")
    vpc_name = st.text_input("VPC 名称（可选）", placeholder="my-production-vpc")
    btn_label = "🚀 Terraform 部署" if use_terraform else "🚀 一键部署 VPC"
    submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")

    if submitted:
        if not cidr:
            st.sidebar.error("CIDR 不能为空")
        elif use_terraform:
            _handle_terraform_deploy(cidr, vpc_name, region)
        else:
            _handle_mock_deploy(cidr, vpc_name, region)


# ============================================================
# 主面板
# ============================================================
st.title("🚀 AWS 运维 Agent - 资产仪表盘")

# 部署模式指示器
if use_terraform:
    st.caption("⚡ 当前模式：**Terraform 真实部署** — 将调用 terraform plan/apply 创建真实 AWS 资源")
else:
    st.caption("🧪 当前模式：**模拟部署** — 仅在本会话中模拟，不会创建真实云资源")

# ---- VPC 列表 ----
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(f"📋 {region} — VPC 资产清单")
with col2:
    if st.button("🔄 刷新列表", use_container_width=True):
        pass

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
