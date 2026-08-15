# dsh-voice-input — DSH 语音输入插件

输入框工具行左侧「**🎤 语音**」按钮：按住开始识别、松开定稿，识别文字**流式实时**写入输入框。
本地离线识别（sherpa-onnx 流式 paraformer 中英双语 int8 + SenseVoice 离线精修），SAPI 自动兜底。

## 架构

- **Host 半区**（`lib/index.js`）：启动本地 HTTP 服务 `127.0.0.1:8765`（CORS 放行），
  管理识别子进程（sherpa-onnx python 或 SAPI powershell），端点：
  - `POST /asr/start` — 启动识别（返回模式 sherpa/sapi）
  - `GET  /asr/peek` — 读取增量文本（流式）
  - `POST /asr/stop` — 停止并返回最终文本
  - `GET  /asr/health` — 健康检查
- **Client 半区**（`lib/client.js`）：`__ModuleLoader__` bundle（导出 `apply`），
  在 `conversation.input.left`（输入框工具行，hero 与普通模式都渲染）注册按钮，
  用浏览器 `fetch` 调用上述端点。

## 识别管线（`stream-recognize.py`）

1. **流式**：paraformer 中英双语 int8（`OnlineRecognizer.from_paraformer`），
   按住时实时出字（`TEXT:` 行）。
2. **精修**：松开后对整段录音跑 **SenseVoice**（`OfflineRecognizer.from_sense_voice`，
   阿里开源，sherpa-onnx 转换 int8），输出带标点、数字规整（ITN）的最终文本（`FINAL:` 行）。
   SenseVoice 为专用 ASR 模型，中英混说质量显著优于早期使用的 whisper-small，
   且不会吞字（此前 whisper-small 会系统性删掉如「体」等字，已废弃）。
3. 语言提示：流式文本含 CJK → `language="zh"`，纯英文 → `"en"`。

## 依赖（本机已装）

- Python 包：`pip install --user sherpa-onnx sounddevice`
- 模型：
  - `G:\dsh\_tools\asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en`（int8，~226MB）
  - `G:\dsh\_tools\asr\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17`（int8，~239MB，用 `model.int8.onnx`）
  - 均下载自 k2-fsa/sherpa-onnx releases
- 识别脚本：`G:\dsh\_tools\asr\stream-recognize.py`（模型路径为脚本内常量，改模型无需动 host）

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
重启 `dsh web` 生效。Client 或识别脚本改动：刷新页面 / 下次录音即生效；Host 改动需重启。

## 验证

`node test.js`（宿主 HTTP 端点 + client bundle 加载/注册的预安装测试，16 项全过）。

## 许可

MIT。识别模型来自 [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0/MIT 生态）。
