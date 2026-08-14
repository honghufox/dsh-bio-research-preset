# dsh-smart-approval — DSH 智能审批插件

在 DeepSeek Harness 中实现**学习式权限规则**：人工批准过一次的目录/操作类型，之后相似的
沙箱外权限请求自动放行；新位置/新操作仍要求人工批准一次。被拒绝的请求不会被学习。

设计对齐 Claude Code 的权限规则模型（`permissions.allow` 工具+模式规则），区别在于
**规则由批准自动生成**，无需手写。

## 行为

| 场景 | 行为 |
|---|---|
| 首次向某目录写入/修改（理由文本含路径） | 弹人工审批；批准后**记住该目录** |
| 同一目录（含子目录）再次写入 | **自动放行**，不打扰 |
| 任务中换到**新目录**写入 | **再次弹审批一次**，批准后记住新目录 |
| 无路径命令（pip/git/tlmgr 等） | 同一会话内同 `工具:模式` 首次人工、之后自动 |
| 预置规则（配置） | 命中即自动，无需先批准 |
| 被拒绝 | 不学习，下次仍询问 |

作用域为**会话**（一个任务）：新会话从零开始，首次仍需人工批准。

## 安装（本机已完成）

1. 包源码：`G:\dsh\_plugins\dsh-smart-approval\`（npm 包，零依赖）
2. 已装入 web profile：`C:\Users\wangh\.dsh\profiles\web\node_modules\dsh-smart-approval`
3. 已挂载：`C:\Users\wangh\.dsh\profiles\web\cordis.patch.yml` 中的 `- id: smart-approval`
4. **重启 DSH web 后生效**

## 配置（可选，Claude Code allow 列表式预置）

在 web profile 的 `cordis.patch.yml` 中给该行加 `config`：

```yaml
- insert:
    - id: smart-approval
      name: dsh-smart-approval
      config:
        rules:
          dirs:
            - 'C:/Users/<你>/.dsh'          # 这些目录始终自动放行
          kinds:
            - 'pwsh:danger-full-access'      # 这些 工具:模式 始终自动放行
        dirLearning: true                    # 学习目录规则（默认开）
        kindLearning: true                   # 学习操作类型规则（默认开）
```

## 工作原理

- 拦截 `approval/request` 瀑布（在人工应答器之前），用 `next()` 包裹人工应答以观察结果
- 从审批理由文本提取目标路径（Windows 盘符/UNC/正斜杠形式），按「目录」归一匹配
- 有路径 → 目录规则；无路径 → `工具:模式` 规则；两者都不中 → 转人工并学习
- 插件永不抛错（fail-closed：异常一律退回人工应答）

## 验证

重启 DSH 后，在任一会话触发两次同目录的沙箱外写入：第一次弹审批，第二次自动放行
（可用会话日志的 `approval/asked` 事件数验证）。
