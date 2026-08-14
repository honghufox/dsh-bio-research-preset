# DSH 生物科研一键启动器

Windows 桌面工具：双击即启动 DSH Web（并临时切换到「生物科研模式」预设），
关闭 DSH 后自动恢复原默认预设。

## 使用

- **双击 `DSH生物科研一键启动.exe`**（桌面或 `G:\dsh\` 下）：
  1. 把默认预设临时切换为 `bio-research`
  2. 若 DSH 未运行 → 自动启动 `dsh web`（新窗口，工作目录 `G:\dsh`）；已在运行 → 直接使用
  3. 自动打开浏览器 `http://127.0.0.1:3080`
  4. 关闭 DSH 窗口或按 `Ctrl+C` → 恢复原默认预设
- 命令行选项：`--check`（自检，不启动）`--no-browser`（不弹浏览器）

## 工作原理

- 备份 `%USERPROFILE%\.dsh\settings.yaml` → 把 `agent-presets.default` 临时改为 `bio-research`
- 轮询 127.0.0.1:3080 判断 DSH 是否在运行
- 退出时从备份恢复 `settings.yaml`（备份文件 `settings.yaml.launcher-bak` 自动删除）

## 注意事项

- 强制关闭启动器窗口（点 X）时 DSH 会继续运行、默认预设保持 bio-research 不恢复；
  再次运行启动器或手动编辑 settings.yaml 即可恢复
- 需要 `dsh` 在 PATH 中（`npm install -g @deepseek-ai/dsh`）
- 工作目录固定为 `G:\dsh`（不存在时用用户主目录）

## 重新编译（如修改源码）

需要 .NET Framework（Windows 自带 csc.exe）：

```powershell
& "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /codepage:65001 /optimize /out:"DSH生物科研一键启动.exe" "DSH生物科研启动器.cs"
```
