import streamlit as st
import time
import uuid
import json

st.set_page_config(page_title="运维 Agent 驾驶舱", layout="wide")

# ============================================================
# 模拟数据初始化
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

if "k3s_clusters" not in st.session_state:
    st.session_state.k3s_clusters = []


# ============================================================
# 部署处理函数
# ============================================================

def _handle_mock_deploy(cidr: str, vpc_name: str, region: str):
    deploy_id = str(uuid.uuid4())[:12]
    new_vpc_id = f"vpc-{deploy_id}"
    with st.spinner(f"⏳ 正在 {region} 模拟创建 VPC..."):
        time.sleep(1.2)
        new_vpc = {
            "VPC ID": new_vpc_id, "CIDR": cidr,
            "State": "available", "IsDefault": False,
            "Name": vpc_name or f"vpc-{deploy_id[:8]}",
        }
        st.session_state.vpcs[region].append(new_vpc)
        st.session_state.deploy_log.insert(0, {
            "time": time.strftime("%H:%M:%S"), "region": region,
            "vpc_id": new_vpc_id, "cidr": cidr, "status": "✅ 模拟部署成功",
        })
    st.sidebar.success(f"✅ VPC 创建成功！\n\n`{new_vpc_id}` → {cidr}")
    st.balloons()


def _handle_terraform_deploy(cidr: str, vpc_name: str, region: str):
    from app.utils.network import validate_network_plan
    from app.utils.terraform_executor import TerraformExecutor
    from app.agents.governance import GovernanceEngine
    from app.agents.llm_advisor import LLMAdvisor

    governance = GovernanceEngine()
    advisor = LLMAdvisor()

    existing_cidrs = [v["CIDR"] for v in st.session_state.vpcs.get(region, [])]
    config = {
        "enable_dns_support": True,
        "tags": {"Environment": "ops-agent", "ManagedBy": "ops-agent"} if vpc_name else {},
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
                with st.spinner("🤖 AI 分析中..."):
                    analysis = advisor.analyze_violation(v.rule.name, v.detail)
                st.info(f"🤖 **AI 分析**\n\n{analysis}")
        if not report.passed:
            st.error("❌ 存在 block 级别的规则违反，部署已拦截")
            st.sidebar.error("❌ 治理检查未通过")
            return

    with st.spinner("🔧 初始化 Terraform..."):
        tf = TerraformExecutor("infrastructure/modules/vpc")
        init_result = tf.init()
        if not init_result.success:
            st.error(f"Terraform init 失败\n```\n{init_result.output[-1000:]}\n```")
            return

    with st.spinner("📋 生成执行计划..."):
        plan_result = tf.plan({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
        })
        if not plan_result.success:
            with st.spinner("🤖 AI 分析错误..."):
                analysis = advisor.analyze_terraform_error(plan_result.output)
            st.info(f"🤖 **AI 诊断**\n\n{analysis}")
            st.error(f"```\n{plan_result.output[-2000:]}\n```")
            return

    with st.expander("📋 Terraform Plan 详情", expanded=False):
        st.code(plan_result.output[-3000:], language="terraform")

    with st.spinner("🚀 执行部署..."):
        apply_result = tf.apply({
            "cidr_block": cidr,
            "vpc_name": vpc_name or f"ops-agent-{uuid.uuid4().hex[:8]}",
        })

    if apply_result.success:
        new_vpc = {
            "VPC ID": apply_result.vpc_id or "pending", "CIDR": cidr,
            "State": "available", "IsDefault": False, "Name": vpc_name or "ops-agent",
        }
        st.session_state.vpcs[region].append(new_vpc)
        st.session_state.deploy_log.insert(0, {
            "time": time.strftime("%H:%M:%S"), "region": region,
            "vpc_id": new_vpc["VPC ID"], "cidr": cidr, "status": "✅ Terraform 部署成功",
        })
        st.sidebar.success(f"✅ Terraform 部署成功！\n\n`{new_vpc['VPC ID']}` → {cidr}")
        st.balloons()
        with st.expander("📜 Terraform Apply 日志", expanded=False):
            st.code(apply_result.output[-3000:], language="terraform")
    else:
        with st.spinner("🤖 AI 分析错误..."):
            analysis = advisor.analyze_terraform_error(apply_result.output)
        st.info(f"🤖 **AI 诊断**\n\n{analysis}")
        st.error(f"```\n{apply_result.output[-2000:]}\n```")
        st.sidebar.error("Terraform apply 失败")


def _handle_k3s_deploy(cluster_name: str, region: str, master_count: int, worker_count: int, instance_type: str):
    """K3S 一键部署 — 先计算，后渲染（避免 Streamlit 重复渲染）"""
    from app.agents.k3s_agent import K3SDeployer

    # 用 spinner 包裹全部计算，不在计算途中调用 UI 元素
    with st.spinner(f"🚀 正在部署 K3S 集群 {cluster_name}（{master_count + worker_count} 节点）..."):
        deployer = K3SDeployer()
        cluster = deployer.deploy(cluster_name, region, master_count, worker_count, instance_type)

    st.session_state.k3s_clusters.append(cluster)

    # 记录日志
    st.session_state.deploy_log.insert(0, {
        "time": time.strftime("%H:%M:%S"), "region": region,
        "vpc_id": cluster.cluster_id, "cidr": f"K3S/{cluster.name}",
        "status": f"✅ K3S 集群就绪 ({len(cluster.nodes)} 节点)",
    })

    # ===================== 下面全部是纯渲染 =====================
    st.success(f"🎉 K3S 集群 `{cluster.name}` 部署完成！")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🖥️ 节点状态")
        node_data = []
        for n in cluster.nodes:
            node_data.append({
                "角色": "⭐ Master" if n.role == "master" else "🔗 Worker",
                "实例 ID": n.node_id,
                "公网 IP": n.public_ip,
                "内网 IP": n.private_ip,
                "状态": "✅ Ready",
            })
        st.table(node_data)

    with col2:
        st.subheader("📋 部署步骤")
        for step in cluster.steps:
            if step.status == "done":
                st.markdown(f"✅ **{step.name}**")
                with st.expander("详情"):
                    st.code(step.output, language="bash")

    st.divider()
    st.subheader("🔑 kubeconfig")
    st.info(
        "将以下内容保存为 `~/.kube/config`，即可用 `kubectl` 管理集群：\n\n"
        f"```bash\nkubectl --kubeconfig ./{cluster.name}.yaml get nodes\n```"
    )
    with st.expander("📄 查看 kubeconfig", expanded=False):
        st.code(cluster.kubeconfig, language="yaml")
        st.download_button(
            "⬇️ 下载 kubeconfig",
            data=cluster.kubeconfig,
            file_name=f"{cluster.name}-kubeconfig.yaml",
            mime="text/yaml",
            key=f"dl_{cluster.cluster_id}",
        )

    st.info(
        "🚀 **集群已就绪！接下来你可以：**\n\n"
        f"1. 下载 kubeconfig 并配置 `kubectl`\n"
        f"2. `kubectl get nodes` 查看节点状态\n"
        f"3. `kubectl create deployment nginx --image=nginx` 部署第一个应用\n"
        f"4. 在侧边栏继续创建更多资源"
    )

    st.sidebar.success(f"✅ K3S `{cluster.name}` 部署完成！")


# ============================================================
# 侧边栏 —— 控制面板
# ============================================================
st.sidebar.markdown("## ⚙️ 部署引擎")
deploy_mode = st.sidebar.radio(
    "选择部署模式",
    ["🧪 模拟模式", "🏗️ Terraform 模式"],
    horizontal=True,
    key="deploy_mode_radio",
)
use_terraform = (deploy_mode == "🏗️ Terraform 模式")

st.sidebar.divider()
st.sidebar.markdown("## 🌍 地区设置")
region = st.sidebar.selectbox("选择云地区", list(st.session_state.vpcs.keys()))

# ---- VPC 创建 ----
st.sidebar.divider()
st.sidebar.markdown("## 🏗️ 创建新 VPC")
with st.sidebar.form("create_vpc_form"):
    cidr = st.text_input("CIDR 地址块", placeholder="例如 10.50.0.0/16", value="10.50.0.0/16")
    vpc_name = st.text_input("VPC 名称（可选）", placeholder="my-production-vpc")
    btn_label = "🚀 Terraform 部署" if use_terraform else "🚀 一键部署 VPC"
    vpc_submitted = st.form_submit_button(btn_label, use_container_width=True, type="primary")

    if vpc_submitted:
        if not cidr:
            st.sidebar.error("CIDR 不能为空")
        elif use_terraform:
            _handle_terraform_deploy(cidr, vpc_name, region)
        else:
            _handle_mock_deploy(cidr, vpc_name, region)

# ---- K3S 一键部署 ----
st.sidebar.divider()
st.sidebar.markdown("## 🏗️ K3S 一键部署")

with st.sidebar.form("k3s_deploy_form"):
    k3s_name = st.text_input("集群名称", placeholder="my-k3s-cluster", value="k3s-prod")
    k3s_master = st.slider("⭐ Master 节点", 1, 3, 1)
    k3s_worker = st.slider("🔗 Worker 节点", 0, 5, 2)
    k3s_type = st.selectbox("实例类型", ["t3.medium", "t3.large", "t3.xlarge", "c5.large"])
    k3s_submitted = st.form_submit_button("🚀 一键部署 K3S 集群", use_container_width=True, type="primary")

    if k3s_submitted:
        _handle_k3s_deploy(k3s_name, region, k3s_master, k3s_worker, k3s_type)


# ============================================================
# 主面板
# ============================================================
st.title("🚀 AWS 运维 Agent - 资产仪表盘")

if use_terraform:
    st.caption("⚡ 当前模式：**Terraform 真实部署** — 将调用 terraform plan/apply 创建真实 AWS 资源")
else:
    st.caption("🧪 当前模式：**模拟部署** — 仅在本会话中模拟，不会创建真实云资源")

# ---- Tab 切换：VPC / K3S ----
tab_vpc, tab_k3s = st.tabs(["📋 VPC 管理", "🏗️ K3S 集群"])

with tab_vpc:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📋 {region} — VPC 资产清单")
    with col2:
        if st.button("🔄 刷新列表", use_container_width=True, key="refresh_vpc"):
            pass

    vpcs = st.session_state.vpcs.get(region, [])
    if vpcs:
        st.success(f"共 **{len(vpcs)}** 个 VPC")
        st.table(vpcs)
    else:
        st.warning("该地区暂无 VPC")

    st.divider()
    st.subheader("📜 部署操作日志")
    if st.session_state.deploy_log:
        st.dataframe(
            st.session_state.deploy_log,
            column_config={
                "time": "时间", "region": "地区",
                "vpc_id": "资源 ID", "cidr": "详情", "status": "状态",
            },
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("暂无部署记录 — 在左侧创建你的第一个 VPC！")

with tab_k3s:
    st.subheader("🏗️ K3S 集群一览")

    if not st.session_state.k3s_clusters:
        st.info(
            "👈 **还没有 K3S 集群** — 在左侧边栏填写配置，点击「一键部署 K3S 集群」开始！\n\n"
            "部署流程将自动完成：\n"
            "1. 🔧 系统环境准备（安装依赖、关闭 swap）\n"
            "2. 🖥️ 创建节点实例\n"
            "3. ⭐ 初始化 Master 节点\n"
            "4. 🔗 加入 Worker 节点\n"
            "5. ✅ 集群验证\n\n"
            "全部自动化，无需手动操作！"
        )
    else:
        for i, cluster in enumerate(st.session_state.k3s_clusters):
            with st.container():
                st.markdown(f"### 🟢 {cluster.name}")
                st.caption(f"ID: `{cluster.cluster_id}` | Region: `{cluster.region}` | K3S: `{cluster.k3s_version}`")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Master 节点", sum(1 for n in cluster.nodes if n.role == "master"))
                with col2:
                    st.metric("Worker 节点", sum(1 for n in cluster.nodes if n.role == "worker"))
                with col3:
                    st.metric("总节点", len(cluster.nodes))

                with st.expander("🖥️ 节点详情", expanded=False):
                    node_data = [{
                        "角色": "⭐ Master" if n.role == "master" else "🔗 Worker",
                        "实例 ID": n.node_id,
                        "公网 IP": n.public_ip,
                        "内网 IP": n.private_ip,
                        "状态": "✅ Ready",
                    } for n in cluster.nodes]
                    st.table(node_data)

                with st.expander("🔑 kubeconfig", expanded=False):
                    st.code(cluster.kubeconfig, language="yaml")

                if i < len(st.session_state.k3s_clusters) - 1:
                    st.divider()
