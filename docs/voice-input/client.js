// dsh-voice-input — Client half (v0.3 bundle, __ModuleLoader__ format)
// Press-and-hold voice input button in the composer dock. The ASR engine is
// exposed by the host half as a localhost HTTP service (127.0.0.1:8765);
// this bundle talks to it with plain fetch.
window.__ModuleLoader__.load({
	id: "dsh-voice-input",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		var React = require("react");
		var BASE = "http://127.0.0.1:8765";

		async function rpc(path, body) {
			const res = await fetch(BASE + path, {
				method: body === undefined ? "GET" : "POST",
				headers: body === undefined ? undefined : { "Content-Type": "application/json" },
				body: body === undefined ? undefined : JSON.stringify(body || {}),
			});
			return res.json();
		}

		function apply(ctx) {
			var slots = ctx.get("slots");
			var timer = ctx.get("timer");
			if (slots === undefined || timer === undefined) return;

			function VoiceButton(props) {
				var rec = React.useState(false);
				var recording = rec[0];
				var setRecording = rec[1];
				var prep = React.useState(false);
				var preparing = prep[0];
				var setPreparing = prep[1];
				var not = React.useState("");
				var notice = not[0];
				var setNotice = not[1];
				var pollRef = React.useRef(null);
				var preRef = React.useRef("");
				var liveRef = React.useRef(false);

				var start = async function () {
					if (recording || preparing) return;
					setPreparing(true);
					setNotice("");
					liveRef.current = true;
					preRef.current = (props.input && props.input.draft) || "";
					try {
						var res = await rpc("/asr/start", {});
						if (!liveRef.current) {
							try { await rpc("/asr/stop", {}); } catch (e) { /* noop */ }
							setPreparing(false);
							return;
						}
						if (!res || !res.ok) {
							setNotice("启动失败: " + ((res && res.error) || "未知"));
							setPreparing(false);
							liveRef.current = false;
							return;
						}
						setPreparing(false);
						setRecording(true);
						var busy = false;
						pollRef.current = timer.interval(async function () {
							if (busy) return;
							busy = true;
							try {
								var p = await rpc("/asr/peek", undefined);
								if (p && p.text) {
									var pre = preRef.current;
									props.inputActions.setDraft(pre ? pre + " " + p.text : p.text);
								}
							} catch (e) { /* keep polling */ }
							busy = false;
						}, 350);
					} catch (e) {
						setNotice("启动失败: " + String(e && e.message ? e.message : e));
						setPreparing(false);
						liveRef.current = false;
					}
				};

				var stop = async function () {
					if (!recording && !preparing) return;
					liveRef.current = false;
					if (pollRef.current) { pollRef.current(); pollRef.current = null; }
					var finalText = "";
					try {
						var res = await rpc("/asr/stop", {});
						if (res && res.ok && res.text) finalText = res.text;
						else if (res && res.error && res.error !== "没有进行中的录音") setNotice("识别失败: " + res.error);
					} catch (e) {
						setNotice("识别失败: " + String(e && e.message ? e.message : e));
					}
					if (finalText) {
						var pre = preRef.current;
						props.inputActions.setDraft(pre ? pre + " " + finalText : finalText);
					}
					setRecording(false);
					setPreparing(false);
				};

				var label = preparing ? "⏳ 准备中…" : (recording ? "⏺ 聆听中…" : "🎤 语音");
				return React.createElement(
					"div",
					{ style: { display: "inline-flex", alignItems: "center", gap: "6px" } },
					React.createElement(
						"button",
						{
							onPointerDown: function (e) { e.preventDefault(); start(); },
							onPointerUp: function (e) { e.preventDefault(); stop(); },
							onPointerLeave: function () { if (recording || preparing) stop(); },
							onPointerCancel: function () { if (recording || preparing) stop(); },
							title: "按住说话，松开结束（本地流式识别，中英混合）",
							style: {
								display: "inline-flex", alignItems: "center", gap: "4px",
								border: "1px solid #888", borderRadius: "6px", padding: "2px 8px",
								cursor: "pointer", fontSize: "12px", lineHeight: "18px", userSelect: "none",
								background: recording ? "#c62828" : (preparing ? "#e65100" : "transparent"),
								color: recording || preparing ? "#fff" : "inherit",
								whiteSpace: "nowrap",
							},
						},
						React.createElement("span", null, label),
					),
					notice ? React.createElement("span", { style: { color: "#c62828", fontSize: "12px", marginLeft: "4px" } }, notice) : null,
				);
			}

			// Registered in `conversation.input.left` (the composer tool row) instead
			// of `conversation.composer.dock`: the dock seat is only rendered once the
			// conversation leaves hero mode (i.e. AFTER the first message), so voice
			// input was unavailable on a brand-new conversation. The tool row renders
			// in both hero and active states.
			slots.inject("conversation.input.left", function () {
				return slots.register(
					{ name: "conversation.input.left", id: "voice-input", order: 1 },
					function (props) {
						return React.createElement(VoiceButton, { input: props.input, inputActions: props.inputActions });
					}
				);
			});
		}

		exports.apply = apply;
		exports.inject = [];
		return module.exports;
	}
});
