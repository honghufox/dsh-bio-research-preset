# DSH 生物科研一键启动器（系统托盘版）

Windows 桌面工具：双击即启动 DSH Web（并临时切换到「生物科研模式」预设），
关闭 DSH 后自动恢复原默认预设。**无窗口、无任务栏按钮，只驻留系统托盘**
（黑鲸鱼图标），彻底避免误关闭。

## 使用

- **双击 `DSH生物科研一键启动.exe`**（桌面或 `G:\dsh\` 下）：
  1. 系统托盘出现黑鲸鱼图标（时钟旁边），弹出气泡提示
  2. 默认预设临时切换为 `bio-research`；未运行时后台启动 `dsh web`（无窗口，日志写 `G:\dsh\dsh-web.log`）
  3. 自动打开浏览器 `http://127.0.0.1:3080`
  4. 监控 DSH 状态：DSH 停止后自动恢复默认预设并退出托盘
- **右键托盘图标菜单**：
  - 打开 DSH 界面（浏览器）
  - 查看 DSH 日志（记事本打开）
  - 停止 DSH（含外部启动的实例）并恢复默认：按 3080 端口定位监听进程并 `taskkill /T` 整树结束（能停掉其他终端启动的孤儿 dsh 实例），随后恢复默认并退出
  - 退出（DSH 保持运行，仅恢复默认）
- **左键双击**：打开浏览器

## 常见情形

- **DSH 已在运行**（包括其他终端启动的、或关闭终端后残留的 node 孤儿进程）：启动器检测到 3080 已监听 → 附加到现有实例，直接打开浏览器，**不会重复启动**
- **想彻底重启**：右键托盘 →「停止 DSH（含外部启动的实例）并恢复默认」→ 再次双击启动器
- 关闭启动 DSH 的终端窗口不一定能停掉 DSH（node 可能成为孤儿进程），用启动器的「停止 DSH」最可靠

## 工作原理

- 备份 `%USERPROFILE%\.dsh\settings.yaml` → 把 `agent-presets.default` 临时改为 `bio-research`
- 轮询 127.0.0.1:3080 判断 DSH 是否在运行（每 5 秒）
- 退出时从备份恢复 `settings.yaml`（备份 `settings.yaml.launcher-bak` 自动删除）
- 图标：DSH 官方 favicon（黑色鲸鱼）→ `whale.ico`，经 `/win32icon` 嵌入 exe，托盘直接复用
- DSH 进程通过 `taskkill /T` 整树结束（含其 node 子进程）

## 命令行

- `--check`：自检（切换预设→检测端口→恢复），结果写入 exe 同目录 `check-result.txt`，无界面

## 注意事项

- 需要 `dsh` 在 PATH 中（`npm install -g @deepseek-ai/dsh`）
- 工作目录固定为 `G:\dsh`（不存在时用用户主目录）；DSH 日志 `G:\dsh\dsh-web.log`
- 强制结束托盘进程（任务管理器）时不会恢复默认预设，下次运行启动器或手动编辑 settings.yaml 即可
- 若托盘图标不显示：Windows 设置 → 任务栏 → 选择显示在任务栏上的图标 → 打开「DSH 生物科研模式」

## 重新编译（如修改源码）

需要 .NET Framework（Windows 自带 csc.exe）：

```powershell
# 1. 重新生成 ICO（需 sharp）：
#    node make-ico.js   （读 whale.svg 生成 whale.ico）
# 2. 编译（GUI 子系统，无控制台）：
& "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /codepage:65001 /target:winexe /optimize `
  /r:System.Windows.Forms.dll /r:System.Drawing.dll `
  /win32icon:"whale.ico" /out:"DSH生物科研一键启动.exe" "DSH生物科研启动器.cs"
```
