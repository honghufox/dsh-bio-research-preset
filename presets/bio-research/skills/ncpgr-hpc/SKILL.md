---
name: ncpgr-hpc
description: 华中农业大学作物遗传改良全国重点实验室生物信息高性能计算平台（hpc.ncpgr.cn）环境须知：登录节点地址与选用、计算节点与存储规格、目录与配额、module 软件环境。当用户要在该集群上登录、选节点、查资源或了解平台限制时使用。
---

# 作重计算平台（hpc.ncpgr.cn）环境须知

华中农业大学作物遗传改良全国重点实验室生物信息高性能计算平台：155 个刀片计算节点、2 个 GPU 节点、6 个八路大内存胖节点，5600 核，存储 12.7PB。预装 1000+ 生信软件与常用数据库。

## 登录节点

| 节点 | 地址 | 说明 |
|---|---|---|
| login01 | 211.69.141.130:22333 | 校内登录 |
| login02 | 211.69.141.140:33322 | **校外登录** |
| login03 | 211.69.141.131:22333 | 校内登录，万兆网 |
| mn02 | 211.69.141.142:22333 | 校内登录（常用） |

登录方式：**动态口令(TOTP) + 密码**，走 keyboard-interactive（Xshell 方法选 Keyboard Interactive，不要勾选 password）。限速：30 秒内最多 3 次登录尝试；每个动态口令仅使用一次。本机已配置自动生成动态口令（TOTP 密钥在 `~/.dsh/dsh-ssh-totp.json`），dsh-ssh 工作区与集群终端会自动应答，无需手动输入。

## 存储

- 用户主目录：`/public/home/<用户名>`（如 `/public/home/username`）
- 用 `diskquota` 查看配额与用量；存储超配额会报 `Disk quota exceeded`，导致**无法写数据、也无法登录集群**
- 集群存储只放使用中的数据：结果及时下载回本地、中间数据及时删除、原始测序数据本地备份一份
- 用户间禁止用 scp 互拷数据，数据共享走平台机制（见文档）

## 软件环境

- `module` 加载预装软件（1000+ 款，含 GATK、deepvariant、parabricks、cellranger、HISAT2、BWA、samtools、bcftools、seqkit、kraken2 等）
- `singularity` 运行容器；`mamba` 替代 conda 创建个人环境（比 conda 快）
- 常用数据库（NR、NT 等）已内置，路径见 `module` 或平台文档

## 平台规则提醒

- 详见 lsf-cluster 技能：队列（normal/interactive/gpu/smp/parrallel）、核数=线程数、内存上限（normal 5G/核、high 10G/核）、禁止登录节点跑大程序
- 账号需每学年集中考核/申请；作业与存储按标准收费
- 数据分析建议流程：转录调控测序、单细胞（cellranger）、三维基因组（HiC-Pro）、表观组（Bismark）、基因组组装（hifiasm/NextDenovo/necat）、变异检测（GATK/deepvariant/parabricks）
