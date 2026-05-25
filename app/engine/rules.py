"""
Alert rule definitions.

Each rule key maps to an AlertType and contains:
- patterns:              substrings matched against alertname (lowercased, stripped)
- severity_thresholds:   value → severity mapping
- reason:                deterministic root-cause summary
- suggestions:           actionable steps (ordered by priority)
- commands:              Linux / K8s commands for troubleshooting
- runbook:               step-by-step SOP
"""

ALERT_RULES: dict[str, dict] = {
    "cpu": {
        "patterns": [
            "cpu", "highcpu", "cpuusage", "cpuhigh",
            "cpuoverload", "cpupressure", "cputhrottle",
        ],
        "severity_thresholds": {"critical": 95, "warning": 80},
        "reason": "CPU使用率过高，可能原因：高负载进程、死循环、资源配额不足、突发流量",
        "suggestions": [
            "使用 top/htop 定位高CPU进程",
            "检查是否有异常定时任务或死循环",
            "确认是否为突发流量导致，考虑弹性扩容",
            "检查容器 CPU limit 是否合理",
        ],
        "commands": [
            "top -bn1 | head -20",
            "ps aux --sort=-%cpu | head -10",
            "mpstat -P ALL 1 3",
            "dmesg | tail -20",
        ],
        "runbook": (
            "1. top 查看 CPU 占用最高的进程\n"
            "2. 确认进程是否为预期负载\n"
            "3. 非预期则 kill 并排查根因\n"
            "4. 预期负载增长则申请扩容"
        ),
    },
    "memory": {
        "patterns": [
            "memory", "mem", "oom", "highmemory",
            "memoryusage", "memorypressure", "memhigh",
        ],
        "severity_thresholds": {"critical": 95, "warning": 85},
        "reason": "内存使用率过高，可能原因：内存泄漏、缓存未清理、OOM 风险",
        "suggestions": [
            "检查内存占用最高的进程",
            "检查是否存在内存泄漏（持续增长）",
            "清理系统缓存或重启服务",
            "考虑增加内存或优化内存使用",
        ],
        "commands": [
            "free -h",
            "ps aux --sort=-%mem | head -10",
            "cat /proc/meminfo | head -20",
            "vmstat 1 5",
        ],
        "runbook": (
            "1. free -h 查看内存使用\n"
            "2. ps 定位高内存进程\n"
            "3. 检查是否有泄漏（持续增长）\n"
            "4. 临时缓解：echo 3 > /proc/sys/vm/drop_caches"
        ),
    },
    "disk": {
        "patterns": [
            "disk", "filesystem", "storage", "diskspace",
            "diskusage", "inode", "diskpressure",
        ],
        "severity_thresholds": {"critical": 95, "warning": 85},
        "reason": "磁盘使用率过高，可能原因：日志未轮转、大文件未清理、数据增长超预期",
        "suggestions": [
            "检查大文件和大目录",
            "清理过期日志和临时文件",
            "检查日志轮转 logrotate 配置",
            "考虑扩容或数据归档",
        ],
        "commands": [
            "df -h",
            "du -sh /* 2>/dev/null | sort -rh | head -10",
            "find /var/log -size +100M -type f",
            "lsof +L1",
        ],
        "runbook": (
            "1. df -h 确认哪个分区满\n"
            "2. du -sh 定位大目录\n"
            "3. 清理日志/临时文件\n"
            "4. 检查 logrotate 配置"
        ),
    },
    "pod_crash": {
        "patterns": [
            "podcrash", "crashloop", "oomkill", "oomkilled",
            "containerkill", "restart", "podrestart",
            "crashloopbackoff", "containerestart",
        ],
        "severity_thresholds": {"critical": 5, "warning": 2},
        "reason": "Pod 异常重启或 CrashLoopBackOff，可能原因：OOM、启动失败、探针超时、配置错误",
        "suggestions": [
            "检查 Pod 日志确认崩溃原因",
            "检查资源 requests/limits 是否足够",
            "确认 readiness/liveness 探针配置",
            "检查 ConfigMap/Secret 是否正确挂载",
        ],
        "commands": [
            "kubectl describe pod <pod-name> -n <namespace>",
            "kubectl logs <pod-name> -n <namespace> --previous",
            "kubectl get events -n <namespace> --sort-by=.lastTimestamp",
            "kubectl top pod -n <namespace>",
        ],
        "runbook": (
            "1. kubectl logs 查看崩溃日志\n"
            "2. kubectl describe 查看 Events\n"
            "3. 检查 resources limits\n"
            "4. 检查探针配置是否合理"
        ),
    },
    "network": {
        "patterns": [
            "network", "latency", "timeout", "connection",
            "dns", "tcp", "http", "packetloss", "bandwidth",
            "networkdelay", "rtt",
        ],
        "severity_thresholds": {"critical": 1000, "warning": 500},
        "reason": "网络异常，可能原因：网络延迟升高、连接超时、DNS 解析失败、带宽饱和",
        "suggestions": [
            "检查网络连通性和延迟",
            "确认 DNS 解析是否正常",
            "检查带宽使用情况",
            "检查防火墙和安全组规则",
        ],
        "commands": [
            "ping -c 4 <target>",
            "curl -o /dev/null -s -w '%{time_total}' <url>",
            "ss -tlnp",
            "netstat -an | grep ESTABLISHED | wc -l",
        ],
        "runbook": (
            "1. ping 测试基础连通性\n"
            "2. traceroute 定位网络瓶颈\n"
            "3. netstat/ss 检查连接状态\n"
            "4. 检查带宽和丢包率"
        ),
    },
}
