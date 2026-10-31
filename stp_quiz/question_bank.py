"""Question bank definitions and loader for STP/RSTP/MSTP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
import random

from stp_quiz.models import Category, KeyPoint, Question, QuestionType


DEFAULT_QUESTIONS: List[Dict] = [
    {
        "id": "STP-ELEC-01",
        "category": "stp_election",
        "qtype": "essay",
        "title": "STP 根桥及端口角色四步选举机制",
        "content": "请详细阐述 IEEE 802.1D STP 生成树网络在拓扑初始化时，选举根桥（Root Bridge）、根端口（RP）、指定端口（DP）的四步比较原则（判定次序），以及每一步比较的核心参数。",
        "standard_answer": (
            "STP 的选举严格遵循四步判定原则，在比较 BPDU 时依次比较：\n"
            "1. 比较最小的根桥ID（Root BID）：由优先级（Priority）+ MAC 地址组成，全网最小者为根桥。\n"
            "2. 比较到达根桥的最小根路径开销（Root Path Cost, RPC）：各非根交换机比较从端口到达根桥的累计开销。\n"
            "3. 比较最小发送者桥ID（Sender BID）：由发送该BPDU的对端交换机优先级和MAC决定。\n"
            "4. 比较最小发送者端口ID（Sender PID）：由发送端口优先级和端口号组成；若仍相同则在本地比较接收端口PID。"
        ),
        "key_points": [
            {
                "point_id": "root_bid",
                "description": "比较最小 Root BID（根桥ID，由优先级和MAC地址组成），选举全网唯一的根桥",
                "synonym_groups": [
                    ["根桥id", "root bid", "root bridge id", "rbid", "最小bid", "桥id"],
                    ["优先级", "priority", "mac"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "rpc",
                "description": "比较到达根桥的最小根路径开销（Root Path Cost, RPC）",
                "synonym_groups": [
                    ["根路径开销", "root path cost", "rpc", "路径开销", "cost", "累计开销"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "sender_bid",
                "description": "比较最小发送者桥ID（Sender BID / 对端桥ID）",
                "synonym_groups": [
                    ["发送者桥id", "sender bid", "发送方桥id", "发送桥id", "对端bid", "sbid", "sender bridge id"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "sender_pid",
                "description": "比较最小发送者端口ID（Sender PID，由端口优先级和端口号组成）及本地端口ID",
                "synonym_groups": [
                    ["发送者端口id", "sender pid", "发送端口id", "端口id", "pid", "port id", "对端端口id"],
                    ["端口号", "端口优先级", "port number", "port priority", "本地pid", "接收端口"]
                ],
                "weight": 1.0,
                "required": False,
            },
        ],
        "explanation": "STP 选举口诀：最小根桥ID、最小根路径开销(RPC)、最小发送者BID、最小发送者PID（若同一对端还比较本地PID）。",
        "difficulty": 3,
        "tags": ["STP", "选举机制", "BID", "RPC", "PID"],
    },
    {
        "id": "STP-ELEC-02",
        "category": "stp_election",
        "qtype": "choice",
        "title": "STP 桥优先级配置步长与默认值",
        "content": "在标准 802.1D / 802.1w 中，桥优先级（Bridge Priority）的默认值是多少？以及其配置步长是多少？",
        "options": {
            "A": "默认值 4096，步长 4096",
            "B": "默认值 32768，步长 4096",
            "C": "默认值 32768，步长 1024",
            "D": "默认值 0，步长 2048",
        },
        "standard_answer": "B",
        "key_points": [],
        "explanation": "802.1D/w 桥优先级占用 16 位，在扩展系统ID生效时高 4 位为优先级，低 12 位为系统扩展ID（VLAN ID），因此步长为 2^12 = 4096，默认优先级为 32768。",
        "difficulty": 2,
        "tags": ["STP", "Bridge Priority", "BID"],
    },
    {
        "id": "PORT-STATE-01",
        "category": "port_roles_states",
        "qtype": "essay",
        "title": "STP 5种端口状态与 RSTP 3种端口状态的映射与区别",
        "content": "请对比 IEEE 802.1D STP 的 5 种端口状态（Disabled, Blocking, Listening, Learning, Forwarding）与 IEEE 802.1w RSTP 的 3 种端口状态，并说明 RSTP 在端口状态精简上做了怎样的合并，以及各自在转发数据帧和学习 MAC 地址上的行为差异。",
        "standard_answer": (
            "STP 包含 5 种端口状态：Disabled、Blocking、Listening、Learning、Forwarding。\n"
            "RSTP 将端口状态精简为 3 种：\n"
            "1. Discarding（丢弃）：合并了 STP 的 Disabled、Blocking 和 Listening，既不转发用户数据流量，也不学习 MAC 地址表；\n"
            "2. Learning（学习）：不转发用户数据流量，但接收数据帧并学习源 MAC 地址以防初始泛洪；\n"
            "3. Forwarding（转发）：既学习 MAC 地址，又正常转发用户数据流量。\n"
            "区别与优势：RSTP 状态精简清晰，去除了冗余无用的中间等待状态，明确了转发与学习两维属性。"
        ),
        "key_points": [
            {
                "point_id": "stp_five_states",
                "description": "提及 STP 的 5 种状态：Disabled, Blocking, Listening, Learning, Forwarding",
                "synonym_groups": [
                    ["disabled", "禁用", "disable"],
                    ["blocking", "阻塞", "block"],
                    ["listening", "侦听", "监听"],
                    ["learning", "学习"],
                    ["forwarding", "转发"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "rstp_three_states",
                "description": "提及 RSTP 的 3 种状态：Discarding, Learning, Forwarding",
                "synonym_groups": [
                    ["discarding", "丢弃"],
                    ["learning", "学习"],
                    ["forwarding", "转发"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "discarding_merge",
                "description": "说明 Discarding 状态合并了 STP 的 Disabled、Blocking 和 Listening 状态",
                "synonym_groups": [
                    ["合并", "整合", "替代", "简化", "相当于", "包含"],
                    ["disabled", "blocking", "listening", "禁用", "阻塞", "侦听", "监听"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "mac_and_forwarding_behavior",
                "description": "阐述数据转发和 MAC 学习行为（Discarding不学不转，Learning只学不转，Forwarding既学又转）",
                "synonym_groups": [
                    ["转发", "forward", "数据帧", "流量"],
                    ["学习", "learn", "mac", "地址表"]
                ],
                "weight": 1.0,
                "required": False,
            },
        ],
        "explanation": "RSTP 将端口是否转发流量、是否学习 MAC 地址这两个行为正交化：Discarding（不转不学）、Learning（不转但学）、Forwarding（既转又学）。",
        "difficulty": 3,
        "tags": ["端口状态", "STP", "RSTP", "Discarding", "Learning", "Forwarding"],
    },
    {
        "id": "PORT-ROLE-02",
        "category": "port_roles_states",
        "qtype": "multi_choice",
        "title": "RSTP 新增端口角色及其防护功能",
        "content": "与经典 802.1D 相比，802.1w (RSTP) 新增了哪些端口角色？（多选）",
        "options": {
            "A": "Alternate Port（预备/替代端口，作为根端口的备份）",
            "B": "Backup Port（备份端口，作为指定端口的备份）",
            "C": "Master Port（主端口，MSTP 专用）",
            "D": "Edge Port（边缘端口，通常连接终端）",
        },
        "standard_answer": "A,B,D",
        "key_points": [],
        "explanation": "RSTP 明确细化了端口角色，将 802.1D 的非指定端口细分为 Alternate 端口（RP备份）和 Backup 端口（DP备份），并引入了 Edge Port。Master Port 是 802.1s MSTP 引入的角色。",
        "difficulty": 3,
        "tags": ["RSTP", "端口角色", "Alternate", "Backup", "Edge Port"],
    },
    {
        "id": "RSTP-PA-01",
        "category": "rstp_convergence_pa",
        "qtype": "essay",
        "title": "RSTP Proposal/Agreement (P/A) 快速收敛握手机制深度剖析",
        "content": "详细阐述 RSTP 的 Proposal/Agreement (P/A) 协商机制的完整工作流程，并说明为什么 P/A 机制可以实现秒级甚至毫秒级的无环快速收敛？必须指明其生效的前提条件、同步过程（Sync）的具体动作以及如何避免临时环路。",
        "standard_answer": (
            "RSTP P/A（提案/同意）机制工作流程与核心要点：\n"
            "1. 前提条件：协商链路必须是点对点链路（Point-to-Point），且端口处于全双工（Full-Duplex）模式。\n"
            "2. 发起 Proposal：当一个指定端口（DP）初始化或新加入拓扑，处于 Discarding 状态时，向对端发送置位 Proposal 标志的 RST BPDU，提议自己进入 Forwarding。\n"
            "3. 拓扑同步（Sync 过程）：下游交换机收到 Proposal 后执行 Sync 同步操作，立即阻塞（置为 Discarding）除边缘端口（Edge Port）外的所有其他非根指定端口，确保下游不会形成临时网络环路。\n"
            "4. 回复 Agreement：当下游各相关端口完成 Sync 处于安全阻塞状态后，下游的新根端口（RP）立即向发起方回复置位 Agreement 标志的 RST BPDU。\n"
            "5. 快速切入 Forwarding：发起方 DP 收到合法的 Agreement 后，无需等待传统 2x Forward Delay（30秒）计时器，直接由 Discarding 瞬间进入 Forwarding 状态，完成极速无环收敛。"
        ),
        "key_points": [
            {
                "point_id": "p2p_fullduplex_premise",
                "description": "必须在点对点（Point-to-Point）链路且全双工（Full-Duplex）环境下才能启用 P/A 机制",
                "synonym_groups": [
                    ["点对点", "point-to-point", "p2p", "point to point"],
                    ["全双工", "full-duplex", "full duplex", "双工"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "proposal_trigger",
                "description": "指定端口（DP）在 Discarding 状态发送置位 Proposal 的 BPDU 发起提议",
                "synonym_groups": [
                    ["proposal", "提案", "提议", "p位"],
                    ["指定端口", "dp", "designated port", "discarding"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "sync_blocking_action",
                "description": "下游设备执行 Sync 同步，阻塞（Discarding）所有非边缘端口以杜绝临时环路",
                "synonym_groups": [
                    ["sync", "同步"],
                    ["阻塞", "block", "discarding", "丢弃"],
                    ["非边缘", "non-edge", "除边缘端口", "非边缘端口", "边缘端口除外", "环路", "防环", "临时环路"]
                ],
                "weight": 1.5,
                "required": True,
            },
            {
                "point_id": "agreement_reply",
                "description": "下游同步完成后，根端口（RP）回复置位 Agreement 标志的 BPDU",
                "synonym_groups": [
                    ["agreement", "同意", "确认", "a位"],
                    ["根端口", "rp", "root port", "回复", "回应", "反馈"]
                ],
                "weight": 1.0,
                "required": True,
            },
            {
                "point_id": "fast_forwarding_no_timer",
                "description": "收到 Agreement 后 DP 立即进入 Forwarding 状态，无需等待 30 秒 Forward Delay 计时器",
                "synonym_groups": [
                    ["forwarding", "转发", "立即转发", "直接转发", "快速"],
                    ["无需等待", "无需计时器", "不用等待", "跳过", "不依赖计时器", "forward delay", "30秒", "30s", "计时器"]
                ],
                "weight": 1.0,
                "required": True,
            },
        ],
        "explanation": "P/A 机制是 RSTP 实现极速收敛的灵魂。通过点对点的主动握手与 Sync 阻塞机制，避免了传统 STP 死板依靠 2*Forward Delay(30s) 定时器来防环的缺陷。",
        "difficulty": 4,
        "tags": ["RSTP", "PA机制", "Proposal", "Agreement", "Sync", "快速收敛"],
    },
    {
        "id": "RSTP-EDGE-01",
        "category": "rstp_convergence_pa",
        "qtype": "choice",
        "title": "RSTP 边缘端口（Edge Port）的特性与行为",
        "content": "关于 RSTP 中边缘端口（Edge Port）的描述，下列哪一项是错误的？",
        "options": {
            "A": "边缘端口在链路 Up 后直接进入 Forwarding 状态，不参与 P/A 协商",
            "B": "边缘端口如果收到 BPDU，会自动失去边缘端口属性，变为普通的生成树端口重新参与计算",
            "C": "配置 BPDU Protection（BPDU 保护）后，边缘端口收到 BPDU 将被立即 Error-Disabled（关闭）",
            "D": "边缘端口状态改变（Up/Down）时，也会触发全网拓扑改变通知（TC BPDU）泛洪",
        },
        "standard_answer": "D",
        "key_points": [],
        "explanation": "边缘端口的 Up/Down 不会触发拓扑改变（TC BPDU），因为边缘端口直接连接终端（PC/服务器），其频繁上下线不应引起网络生成树拓扑抖动和 MAC 地址表清空，故 D 项错误。",
        "difficulty": 3,
        "tags": ["RSTP", "Edge Port", "边缘端口", "TC BPDU", "BPDU保护"],
    },
    {
        "id": "MSTP-INST-01",
        "category": "mstp_instance",
        "qtype": "essay",
        "title": "MSTP 区域三要素与 VLAN 到 MSTI 实例映射原理",
        "content": "请阐述 IEEE 802.1s MSTP（多生成树协议）中，交换机划归同一个 MST Region（MST 域）必须完全一致的三个配置要素是什么？并说明 VLAN 映射到 MSTI（多生成树实例）的设计意义（相比于 STP/RSTP 和 Cisco PVST+ 解决了什么核心痛点？）。",
        "standard_answer": (
            "MSTP 同一域（MST Region）必须一致的三要素：\n"
            "1. 相同的域名（Region Name）；\n"
            "2. 相同的修订级别（Revision Level）；\n"
            "3. 相同的 VLAN 到生成树实例（MSTI）映射关系（VLAN-to-Instance Mapping）。\n"
            "解决的痛点与意义：\n"
            "1. 相比 STP/RSTP（单一生成树 CST）：STP 全网只有一棵树，导致所有 VLAN 只能共用同一个阻塞路径，链路利用率低，冗余链路常年闲置无法实现负载分担；\n"
            "2. 相比 PVST+（每 VLAN 一棵树）：PVST+ 虽然可以每 VLAN 独立阻塞实现负载均衡，但当网络中存在上千个 VLAN 时，交换机需要维护成千上万个 STP 实例，CPU 占用率和 BPDU 报文开销极大；\n"
            "3. MSTP 解决方案：将多个业务相似或路径一致的 VLAN 捆绑（Mapping）到少量的几个 MSTI 实例中（例如实例1和实例2），既实现不同 VLAN 流量的多路径负载均衡，又将生成树计算实例数量维持在极低水平，兼顾了灵活性与硬件性能开销。"
        ),
        "key_points": [
            {
                "point_id": "region_three_elements",
                "description": "明确 MST 域三要素：Region Name（域名）、Revision Level（修订级别）、VLAN 到 MSTI 映射",
                "synonym_groups": [
                    ["域名", "region name", "名称"],
                    ["修订级别", "revision level", "revision", "版本号"],
                    ["映射", "mapping", "vlan", "msti", "实例映射", "vlan-to-instance"]
                ],
                "weight": 1.5,
                "required": True,
            },
            {
                "point_id": "single_stp_drawback",
                "description": "指出 STP/RSTP 单一树不能实现负载分担、链路浪费的缺陷",
                "synonym_groups": [
                    ["负载均衡", "负载分担", "load balance", "链路利用率", "浪费", "单树", "单一生成树", "cst"]
                ],
                "weight": 1.0,
                "required": False,
            },
            {
                "point_id": "pvst_drawback",
                "description": "指出 PVST+ 每 VLAN 一棵树带来的 CPU/内存资源消耗大、BPDU 风暴等开销问题",
                "synonym_groups": [
                    ["pvst", "每vlan", "cpu", "资源", "开销", "bpdu", "消耗", "负荷"]
                ],
                "weight": 1.0,
                "required": False,
            },
            {
                "point_id": "mstp_instance_bundle",
                "description": "总结 MSTP 将多个 VLAN 映射/捆绑到少量 MSTI 实例，兼顾负载均衡与开销控制",
                "synonym_groups": [
                    ["捆绑", "映射", "bundle", "结合", "少量实例", "msti", "实例"],
                    ["负载分担", "负载均衡", "兼顾", "性能", "降低开销"]
                ],
                "weight": 1.0,
                "required": True,
            },
        ],
        "explanation": "MSTP 的核心灵魂是：域名+修订级别+VLAN映射关系三者哈希一致判定在同一个Region，通过实例抽象解决了单生成树不负载与多生成树资源炸裂的双重极端难题。",
        "difficulty": 4,
        "tags": ["MSTP", "MST Region", "MSTI", "VLAN映射", "PVST", "负载分担"],
    },
    {
        "id": "MSTP-CONV-02",
        "category": "mstp_instance",
        "qtype": "choice",
        "title": "MSTP 树概念：CST, IST 与 CIST 的拓扑层次关系",
        "content": "在 MSTP 网络中，连接各个 MST 域以及单生成树网络的公共骨干生成树被称为：",
        "options": {
            "A": "IST (Internal Spanning Tree)",
            "B": "CST (Common Spanning Tree)",
            "C": "CIST (Common and Internal Spanning Tree)",
            "D": "MSTI (Multiple Spanning Tree Instance)",
        },
        "standard_answer": "B",
        "key_points": [],
        "explanation": "CST（公共生成树）是连接交换网络内所有 MST 域的单生成树；IST 是域内的内部生成树；CIST 则是整个网络（包含所有 MST 域和 CST）联合构成的总生成树。",
        "difficulty": 3,
        "tags": ["MSTP", "CST", "IST", "CIST"],
    },
    {
        "id": "COMP-TOPO-01",
        "category": "comprehensive",
        "qtype": "essay",
        "title": "经典双交换机多链路拓扑下的根端口（RP）选举推演",
        "content": (
            "拓扑场景分析：\n"
            "交换机 SW1（根桥，BID=4096:0001.0001.0001）与交换机 SW2（非根桥，BID=32768:0002.0002.0002）之间直连了 2 条等开销的千兆以太网链路。\n"
            "链路1连接：SW1 的 G0/0/1 <---> SW2 的 G0/0/2\n"
            "链路2连接：SW1 的 G0/0/2 <---> SW2 的 G0/0/1\n"
            "所有接口默认开销相同，端口优先级均为默认 128。\n"
            "请问：SW2 最终会选择哪个端口作为根端口（Root Port）？并运用 STP 选举规则一步步详细写出判定过程和依据。"
        ),
        "standard_answer": (
            "判定结果：SW2 最终选择 G0/0/2 作为根端口（Root Port）。\n"
            "推导过程：\n"
            "1. 比较到达根桥的 RPC（根路径开销）：由于两条链路均为直连千兆且开销相同，SW2 的 G0/0/1 和 G0/0/2 收到的 RPC 均为 0（加本地开销后相同，均为 20000），打平；\n"
            "2. 比较对端 Sender BID：两端口收到的 BPDU 均来自根桥 SW1（4096:0001.0001.0001），Sender BID 相同，打平；\n"
            "3. 比较对端 Sender PID（发送者端口ID）：\n"
            "   - SW2 的 G0/0/2 端口连接的是 SW1 的 G0/0/1 端口，收到的 Sender PID 为 128.1（G0/0/1）；\n"
            "   - SW2 的 G0/0/1 端口连接的是 SW1 的 G0/0/2 端口，收到的 Sender PID 为 128.2（G0/0/2）；\n"
            "   - 因为 SW1 的 G0/0/1 端口编号更小，Sender PID 128.1 < 128.2；\n"
            "4. 结论：在第 3 步比较 Sender PID 时决出胜负，SW2 的 G0/0/2 端口收到的 Sender PID 更小，故 SW2 的 G0/0/2 胜出成为 Root Port，而 G0/0/1 被阻断为 Alternate Port。"
        ),
        "key_points": [
            {
                "point_id": "rp_result",
                "description": "正确判定 SW2 的 G0/0/2 成为根端口（RP）",
                "synonym_groups": [
                    ["g0/0/2", "ge0/0/2", "0/0/2", "g2", "端口2"],
                    ["根端口", "root port", "rp"]
                ],
                "weight": 1.5,
                "required": True,
            },
            {
                "point_id": "compare_rpc_bid_tie",
                "description": "指出前两步 RPC 和 Sender BID 均相同打平",
                "synonym_groups": [
                    ["rpc", "开销", "根路径开销"],
                    ["sender bid", "桥id", "bid", "相同", "打平", "一致"]
                ],
                "weight": 1.0,
                "required": False,
            },
            {
                "point_id": "compare_sender_pid",
                "description": "依据是比较对端发送者端口ID（Sender PID），SW1的 G0/0/1 端口号小于 G0/0/2",
                "synonym_groups": [
                    ["sender pid", "发送者pid", "发送端pid", "发送端口", "对端端口", "pid"],
                    ["sw1", "g0/0/1", "小于", "更小", "优先", "128.1"]
                ],
                "weight": 1.5,
                "required": True,
            },
            {
                "point_id": "local_pid_not_used",
                "description": "明确不是看 SW2 本地接口号（不能误选本地G0/0/1），而是看对端发送方 PID",
                "synonym_groups": [
                    ["对端", "发送方", "sender", "不是本地", "非本地", "对端发送"]
                ],
                "weight": 1.0,
                "required": False,
            },
        ],
        "explanation": "经典易错题！很多人会因为 SW2 的 G0/0/1 本地端口号更小而误判。记住：只有当多条链路接到对端 Hub（同对端同端口）导致 Sender PID 也相同时，才看本地接收端口 PID！本题在 Sender PID 这一步就已经判定出 SW1-G0/0/1 胜出，对应 SW2-G0/0/2 成为 RP。",
        "difficulty": 4,
        "tags": ["拓扑分析", "RP选举", "Sender PID", "易错题"],
    },
]


class QuestionBank:
    """Manages STP quiz questions with filtering and random selection."""

    def __init__(self, questions: Optional[List[Question]] = None):
        self._questions: Dict[str, Question] = {}
        if questions is not None:
            for q in questions:
                self._questions[q.id] = q
        else:
            self._load_defaults()

    def _load_defaults(self) -> None:
        for q_data in DEFAULT_QUESTIONS:
            q = Question.from_dict(q_data)
            self._questions[q.id] = q

    def count(self) -> int:
        return len(self._questions)

    def get(self, question_id: str) -> Optional[Question]:
        return self._questions.get(question_id)

    def list_all(self) -> List[Question]:
        return list(self._questions.values())

    def filter(
        self,
        category: Optional[Category] = None,
        qtype: Optional[QuestionType] = None,
        tag: Optional[str] = None,
        min_difficulty: int = 1,
        max_difficulty: int = 5,
    ) -> List[Question]:
        res = []
        for q in self._questions.values():
            if category and q.category != category:
                continue
            if qtype and q.qtype != qtype:
                continue
            if tag and tag not in q.tags:
                continue
            if not (min_difficulty <= q.difficulty <= max_difficulty):
                continue
            res.append(q)
        return res

    def pick_random(
        self,
        category: Optional[Category] = None,
        qtype: Optional[QuestionType] = None,
        exclude_ids: Optional[List[str]] = None,
    ) -> Optional[Question]:
        pool = self.filter(category=category, qtype=qtype)
        if exclude_ids:
            pool = [q for q in pool if q.id not in exclude_ids]
        if not pool:
            return None
        return random.choice(pool)

    def export_json(self, file_path: str | Path) -> None:
        data = [q.to_dict() for q in self._questions.values()]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_json(self, file_path: str | Path, override: bool = True) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            q = Question.from_dict(item)
            if override or q.id not in self._questions:
                self._questions[q.id] = q
                count += 1
        return count
