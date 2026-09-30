---
name: ncpgr-lsf
description: NCPGR高性能计算集群LSF作业调度系统使用指南。用于提交、管理和监控LSF批处理作业，包括串行作业、多线程作业、MPI并行作业、GPU作业、数组作业等。当用户需要编写LSF作业脚本、提交计算任务、查询作业状态、调整作业参数或排查作业问题时使用此skill。
trigger: |
  当用户问题涉及以下任一场景时加载本 skill，并联动加载 ncpgr-software：
  1. 提到"集群"、"HPC"、"计算节点"、"登录节点"
  2. 提到 LSF 命令（bsub、bjobs、bpeek、bkill、bhist、bqueues）或 #BSUB 指令
  3. 提到"作业脚本"、".lsf"、"作业提交"、"作业状态"、"作业数组"、"依赖作业"
  4. 提到队列名称（normal、smp、high、gpu、parallel）或资源申请（核数、内存、GPU）
  5. 询问如何编写、提交、监控、调试集群批处理作业
---

# NCPGR LSF 作业调度使用指南

> **本地校正记录（2026-09-30）**：本副本已按集群实测修订，与上游正典
> `/public/home/software/opt/skills/ncpgr-lsf/` 不再逐字节一致。
> 修订点：补记**实际队列全清单**（含 `smp2`/`test`/`parallel2`）与排队现状，并在 `references/lsf-guide.md`、
> `references/faq.md` 中把已禁用的 `q2680v2` 标注出来（原 lsf-guide 曾建议改用它，与 SKILL.md 的禁令冲突）。

## 编写规范（重要）

提交LSF作业前必须遵守以下规范：

### 0. 网络访问规范

**由于计算节点没有联网，所有需要网络的任务都必须在当前登录节点进行，不得提交到计算节点。**

| 任务类型 | 执行位置 | 说明 |
|---------|---------|------|
| 需要网络（下载数据、下载参考基因组、安装软件包等） | **登录节点** | 直接在登录节点执行，不能通过bsub提交 |
| 纯计算（比对、定量、组装、分析等） | 计算节点（通过LSF提交） | 通过编写 `.lsf` 脚本提交到计算节点 |

### 0.1 脚本编写原则

**作业脚本应保持简洁易读**，不可过度编码或使用高级技巧（如复杂的 sed/awk 变量替换、多重临时文件创建/清理、嵌套条件逻辑等）。用户需要能够轻松阅读、检查和自行修改脚本。

### 1. 脚本命名规范

**LSF作业脚本后缀必须使用 `.lsf`**

```bash
# 正确命名
my_job.lsf
bwa_mem.lsf
rnaseq_pipeline.lsf

# 避免使用
my_job.sh          # 不推荐
my_job.bash        # 不推荐
```

### 2. 极简编写规范

**核心原则：由于队列已配置资源限制，作业脚本应尽可能简化**

#### 规则2.1：不设置内存参数

所有队列都已配置**单核**内存限制，**不需要**在作业脚本中设置 `-M` 和 `rusage[mem=...]`。

**作业总内存 = 申请核数 × 队列单核内存上限**，需要更多内存时只需增加 `-n`：

```bash
# 正确的简化写法（推荐）
#!/bin/bash
#BSUB -J my_job
#BSUB -q normal
#BSUB -n 4
#BSUB -R "span[hosts=1]"
#BSUB -o %J.out
#BSUB -e %J.err

your_program --threads $LSB_DJOB_NUMPROC

# 错误的冗余写法（不推荐）
#BSUB -M 8G                 # 不需要！
#BSUB -R "rusage[mem=8G]"   # 不需要！
```

#### 规则2.2：不设置时间限制

不需要设置 `-W` 运行时间限制：

```bash
# 正确的简化写法（推荐）
#!/bin/bash
#BSUB -J my_job
#BSUB -q normal
#BSUB -n 4
#BSUB -R "span[hosts=1]"
#BSUB -o %J.out
#BSUB -e %J.err

# 错误的冗余写法（不推荐）
#BSUB -W 12:00             # 不需要！
```

#### 规则2.3：资源规划（设置核数前查看资源）

```bash
# 第1步：查看当前集群资源
bhosts | grep -E "ok|closed" | head -10

# 第2步：根据结果决定核数
# 多数节点为 closed → 申请2-4核（易调度）
#BSUB -n 2

# 有空闲节点且核心充足 → 可申请8+核
#BSUB -n 8
```

| 场景 | 建议策略 |
|------|----------|
| 多数节点状态为`closed` | 申请2-4核，提高调度优先级 |
| 有空闲节点(`ok`)且有较多空核心 | 可申请8-16核加速计算 |
| 急需作业跑上 | 申请1-2核，几乎可以立即调度 |

**警告**：盲目申请过多核心（如32核）会导致作业长时间排队

## 快速参考

### 常用命令速查

| 命令 | 用途 |
|------|------|
| `bsub < job.lsf` | 提交作业脚本 |
| `bjobs` | 查看作业状态 |
| `bjobs -l <jobid>` | 查看作业详细信息 |
| `bpeek <jobid>` | 查看作业输出 |
| `bkill <jobid>` | 终止作业 |
| `bstop <jobid>` / `bresume <jobid>` | 挂起/恢复作业 |
| `bmod -n 4 <jobid>` | 修改作业参数 |
| `lsload` | 查看节点负载 |
| `bhosts` | 查看节点状态 |
| `bqueues` | 查看队列信息 |

### 推荐别名

添加到 `~/.bashrc`：

```bash
alias bbjobs='bjobs -o "jobid:10 user:6 stat:6 queue:6 exec_host:10 job_name:10 max_mem:14 submit_time:12"'
alias bbs='bjobs -o "jobid:8 user:8 stat:6 queue:6 exec_host:10 job_name:8 nreq_slot:6 slots:5 max_mem:12 submit_time:12 start_time:12 run_time:16 cpu_used"'
```

## 作业提交

### 1. 软件环境规范（重要）

**如果用户使用集群已安装的软件，必须使用 `module` 命令加载：**

```bash
# 查看可用软件
module av bwa          # 查看bwa相关模块
module av star         # 查看STAR相关模块
module av              # 查看所有可用模块

# 在作业脚本中加载
module load BWA/0.7.17-foss-2018b
module load STAR/2.6.0a-foss-2016b
```

**规则**：
- **优先原则**：只要应用软件已通过module安装在集群，**必须优先**使用module版本
- 当用户说"使用集群已安装的bwa/star/samtools"等时，**不要**假设软件已在PATH中
- 必须使用 `module load` 加载对应的模块
- 先用 `module av 软件名` 查看具体模块名

### 2. 极简串行/多线程作业模板（推荐）

```bash
#!/bin/bash
#BSUB -J job_name          # 作业名
#BSUB -n 4                  # 申请4个核心（根据bhosts结果调整）
#BSUB -R "span[hosts=1]"    # 限制在单节点运行
#BSUB -o %J.out             # 输出文件
#BSUB -e %J.err             # 错误文件
#BSUB -q normal             # 队列名

# 加载集群已安装的软件（如果有）
# module load SoftwareName/Version

# 使用 $LSB_DJOB_NUMPROC 自动获取申请的核心数
your_program --threads $LSB_DJOB_NUMPROC
```

**极简原则**：
- ✅ 不设置 `-M` 和 `rusage[mem=...]`（队列已自动管理）
- ✅ 不设置 `-W` 时间限制
- ✅ 使用 `module load` 加载集群已安装的软件
- ✅ 只保留最核心的参数

**重要**: 生物信息软件大多不支持跨节点并行，务必使用 `-R "span[hosts=1]"` 限制在单节点运行。

### 2. 其他作业类型模板

#### MPI并行作业（多节点）

```bash
#!/bin/bash
#BSUB -J MPIJob
#BSUB -q normal
#BSUB -n 400
#BSUB -R "span[ptile=20]"   # 每节点20核
#BSUB -o stdout_%J.out
#BSUB -e stderr_%J.err

module load intel/2018.4
module load mpi/intel/2018.4

mpirun -np $LSB_DJOB_NUMPROC ./MPI_program
```

**警告**: 生物软件绝大多数不支持MPI，请勿随意使用多节点并行。

#### GPU作业

> **注意**: 使用 GPU 队列前，需先向管理员申请 GPU 队列使用权限。

```bash
#!/bin/bash
#BSUB -J gpu_job
#BSUB -q gpu
#BSUB -n 4
#BSUB -R "span[hosts=1]"
#BSUB -gpu "num=1:mode=shared"
#BSUB -o %J.out
#BSUB -e %J.err

python train.py
```

#### 交互式作业

```bash
# 基础交互
bsub -q interactive -Is bash

# 带X11转发（图形界面）
bsub -q interactive -XF -Is bash
```

限制：只能在interactive队列，最长48小时。

## 批量作业提交

### 方式1: Shell循环提交（推荐）

```bash
for sample in /path/to/data/*_1.fq.gz; do
    index=$(basename $sample | sed 's/_1.fq.gz//')
    bsub -J ${index} -n 8 -R span[hosts=1] -o %J.${index}.out \
        "your_program -t 8 -i $sample"
    sleep 10  # 避免瞬间提交过多
done
```

### 方式2: 流程脚本 + 批量提交（带依赖）

使用 `-K` 参数让作业按顺序执行：

```bash
# 在流程脚本内
bsub -K -J step1 -n 8 ... "command1"   # -K等待完成
bsub -K -J step2 -n 1 ... "command2"   # step1完成后执行
bsub -K -J step3 -n 2 ... "command3"
```

### 方式3: 数组作业

```bash
#BSUB -J array[1-100]  # 提交100个任务

# 使用 $LSB_JOBINDEX 区分不同任务
input="sample_${LSB_JOBINDEX}.fq"
```

## 作业查询与监控

### 作业状态说明

| 状态 | 含义 |
|------|------|
| PEND | 排队中 |
| RUN | 运行中 |
| DONE | 正常完成 |
| EXIT | 异常退出 |
| SSUSP | 系统挂起（节点内存不足等） |
| USUSP | 用户挂起 |

### 排查作业问题

**查看排队原因**:
```bash
bjobs -p <jobid>
```

常见原因：
- `User has reached the pre-user job slot limit`: 用户作业数达队列上限
- `The user has reached his job slot limit`: 用户总作业数达系统上限
- `The queue has reached its job slot limit`: 队列总核数已满

**检查作业效率**:
```bash
# 比较 run_time (walltime) 和 cpu_used (cputime)
# 若 cpu_used << run_time * 核数，说明作业可能空跑或出错
```

**作业运行异常/资源不合理检查原则**：

当分析已完成作业的 `bjobs` 输出时，如果同时满足以下两个条件，必须提醒用户：

1. **walltime (实际运行时间) 远小于 cputime (CPU总时间)**  
   - walltime ≈ cputime → 程序实际上只使用了单核，多核心未被利用
   - 例如：申请了8核，walltime=1小时，cputime=1.2小时 → 说明只用到约1核

2. **单核实际内存使用 < 队列单核内存限制**

**提醒内容应包括**：
- 指出资源申请不合理：程序没有充分利用申请的所有核心
- 建议减少核数重新提交，这样排队更快且不浪费集群资源
- 可能原因：程序本身不支持多线程，或多线程参数配置不正确

**判断示例**：

| 申请核数 | walltime | cputime | 实际内存 | 队列限制 | 结论 |
|---------|---------|---------|---------|---------|------|
| 8核 | 60分钟 | 70分钟 | 2GB | 6GB | **提醒**：只用到1核，建议减少核数 |
| 8核 | 60分钟 | 420分钟 | 2GB | 6GB | 正常：有效利用了约7核 |
| 4核 | 30分钟 | 35分钟 | 1GB | 6GB | **提醒**：只用到1核，建议减少核数 |

## 作业控制

```bash
bkill <jobid>           # 终止作业
bkill 0                 # 终止用户所有作业
bstop <jobid>           # 挂起作业
bresume <jobid>         # 恢复作业
bmod -n 8 <jobid>       # 修改核心数
bmod -q high <jobid>    # 修改队列
btop <jobid>            # 作业移到队首
bbot <jobid>            # 作业移到队尾
brequeue <jobid>        # 重新提交作业
```

## 集群特定信息

### 队列选择

**队列优先级：normal → high → smp**

| 优先级 | 队列 | 适用场景 | 单核内存上限 |
|--------|------|---------|-------------|
| **1（默认）** | normal | 一般作业 | 10 GB |
| **2** | high | 大内存作业（≤540GB） | 15 GB |
| **3** | smp | 总内存需求 **>200GB** 的作业 | 20 GB |
| 专用 | gpu | GPU 计算（需申请权限） | - |
| 专用 | parallel | MPI 跨节点并行 | - |
| 专用 | interactive | 交互调试，限48小时 | - |

> **禁止使用 short 和 q2680v2 队列。**
>
> **集群实际队列**（2026-09-30 实测 `bqueues`）：`normal`、`high`、`smp`、`smp2`、`gpu`、`parallel`、`parallel2`（Closed）、`interactive`、`short`、`q2680v2`、`test`。上表只列**推荐使用**的队列；`smp2`/`test`/`parallel2` 不是通用选择，`short` 与 `q2680v2` 禁用。申请前先 `bqueues` 看实时排队——`normal`/`high`/`smp` 长期各有数千作业排队（实测 normal 排队 6000+），**核数越小越容易调度**。
>
> **选择规则**：
> 1. 一般作业默认用 **normal**
> 2. 内存需求大（≤540GB）时优先用 **high**
> 3. 只有总内存需求 **超过 200GB** 时才用 **smp**

### 队列自动资源限制

**所有队列都已配置单核内存限制。作业总内存 = 核数 × 单核限制**：

| 队列 | 单核内存（默认/最大） | 节点物理内存 | 总内存计算示例 |
|------|---------------------|-------------|---------------|
| **normal** | 6GB / 10GB | 192~384GB | 8核 → 48~80GB |
| **high** | 11GB / 15GB | 384GB | 8核 → 88~120GB；36核 → 540GB |
| **smp** | 12GB / 20GB | 1.9~3.9TB | 8核 → 96~160GB；16核 → 320GB |
| **interactive** | 30GB / 500GB | - | 仅限48小时交互 |

> **关键公式：作业可用总内存 = 申请核数(`-n`) × 队列单核内存上限**
>
> 例如需要 ~200GB 内存的小麦 STAR 索引：
> - high 队列 16 核：16 × 15GB = **240GB** ✓（优先用 high）
> - smp 队列 12 核：12 × 20GB = **240GB** ✓（备选）
> - **结论：增加核数即可获取更多总内存**

**使用原则**：
- ✅ **不要设置** `-M` 和 `rusage[mem=...]`（队列已自动管理）
- ✅ **不要设置** `-W` 时间限制（除非是测试性作业）
- ✅ **只设置** `-n` 核心数和 `-q` 队列名
- ✅ **需要更多内存时，增加 `-n` 核数**（总内存 = 核数 × 单核上限）

**内存超限处理**：
- 超出默认限制：作业会被挂起(SSUSP)，稍后自动恢复
- 超出最大限制（单核实际用量超过单核上限）：作业会被终止(EXIT)
- 频繁被挂起：增加核数以获取更多总内存，或换到smp/high队列

### 重要系统变量

| 变量 | 说明 |
|------|------|
| `$LSB_JOBID` | 作业ID |
| `$LSB_JOBINDEX` | 数组作业索引 |
| `$LSB_DJOB_NUMPROC` | 申请的核心数 |
| `$LSB_MEMLIMIT` | 单核内存上限（MB），由队列自动设置 |
| `$LSB_QUEUE` | 队列名 |

### 节点资源参考

> 以下为集群节点的实际配置（来源：`lshosts`），用于判断作业需要申请多少核数。
> **核心公式：作业可用总内存 = 核数 × 队列单核内存上限，但不超过节点物理内存。**

| 队列 | 节点 | 每节点核数 | 每节点物理内存 | 单核内存上限 | 单节点最大可用内存 |
|------|------|-----------|--------------|-------------|------------------|
| **normal** | c01~c04（~56台） | 36 | 384 GB | 10 GB | 360 GB (36×10) |
| **normal** | c05~c07（~42台） | 36 | 192 GB | 10 GB | 192 GB（物理上限）|
| **smp** | s001, s003, s004 | 192 | 1.9 TB | 20 GB | 1.9 TB（物理上限）|
| **smp** | s005 | 96 | **3.9 TB** | 20 GB | 1920 GB (96×20) |
| **smp** | s006 | 96 | 1.9 TB | 20 GB | 1920 GB (96×20) |
| **high** | c04n01-03 + cmm01-03 | 36 | 384 GB | 15 GB | 540 GB (36×15) |

**核数选择参考**（根据内存需求反算，按 normal → high → smp 优先级）：

| 作业内存需求 | 推荐队列 | 最少核数 | 说明 |
|-------------|---------|---------|------|
| ≤ 48 GB | normal | 8 核 | normal 默认 6GB/核 × 8 = 48GB |
| ≤ 80 GB | normal | 8 核 | normal 最大 10GB/核 × 8 = 80GB |
| ≤ 120 GB | high | 8 核 | high 最大 15GB/核 × 8 = 120GB |
| ≤ 160 GB | high | 11 核 | high 最大 15GB/核 × 11 = 165GB |
| ≤ 200 GB | high | 14 核 | high 最大 15GB/核 × 14 = 210GB |
| ≤ 240 GB | smp | 12 核 | smp 最大 20GB/核 × 12 = 240GB（超过200GB，用smp）|
| ≤ 320 GB | smp | 16 核 | smp 最大 20GB/核 × 16 = 320GB |
| ≤ 540 GB | high | 36 核 | high 整节点（优先于 smp）|
| ≤ 2 TB | smp | 96+ 核 | smp 大内存节点 |

> **注意**：
> - c05~c07 节点仅 192GB 物理内存。如果在 normal 队列申请大内存作业被 SSUSP，可能是调度到了 c05~c07 节点内存不足，此时应改用 high 队列。
> - **禁止使用 short 和 q2680v2 队列。**
> - 实测（2026-09-30）`normal`/`high`/`smp` 三个队列合计排队 1 万+ 作业；**盲目申请大核数是排队的首要原因**，能用 2~4 核解决的就不要写 16 核。

## 参考资料

- [完整文档](references/lsf-guide.md)
- [作业模板脚本](scripts/) （后缀均为 `.lsf`）
- [常见问题](references/faq.md)
- [快速参考](references/quick-ref.md)
