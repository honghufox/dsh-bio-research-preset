# dsh-voice-input — DSH 语音输入插件

输入框下方「**按住说话**」按钮：按住开始识别、松开定稿，识别文字**流式实时**写入输入框。
本地离线识别（sherpa-onnx 流式 paraformer 中英双语 int8），SAPI 自动兜底。

## 架构

- **Host 半区**（`lib/index.js`）：启动本地 HTTP 服务 `127.0.0.1:8765`（CORS 放行），
  管理识别子进程（sherpa-onnx python 或 SAPI powershell），端点：
  - `POST /asr/start` — 启动识别（返回模式 sherpa/sapi）
  - `GET  /asr/peek` — 读取增量文本（流式）
  - `POST /asr/stop` — 停止并返回最终文本
  - `GET  /asr/health` — 健康检查
- **Client 半区**（`lib/client.js`）：`__ModuleLoader__` bundle（导出 `apply`），
  在 `conversation.composer.dock` 注册按钮，用浏览器 `fetch` 调用上述端点。

## 依赖（本机已装）

- Python 包：`pip install --user sherpa-onnx sounddevice`
- 模型：`G:\dsh\_tools\asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en`（int8，~226MB，
  下载自 k2-fsa/sherpa-onnx releases）
- 识别脚本：`G:\dsh\_tools\asr\stream-recognize.py`

## 安装

```powershell
npm install --save "file:G:\dsh\_plugins\dsh-voice-input" --prefix "C:\Users\wangh\.dsh\profiles\web"
```
并在 `C:\Users\wangh\.dsh\profiles\web\cordis.patch.yml` 增加：
```yaml
- insert:
    - id: voice-input
      name: dsh-voice-input
```
重启 `dsh web` 生效。

## 验证

`node test.js`（宿主 HTTP 端点 + client bundle 加载/注册的预安装测试，13 项全过）。

## 许可

MIT。识别模型来自 [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0/MIT 生态）。
