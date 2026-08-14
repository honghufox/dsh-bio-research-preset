// DSH 生物科研模式一键启动器（系统托盘版）
// 编译:
//   csc.exe /nologo /codepage:65001 /target:winexe /optimize
//         /r:System.Windows.Forms.dll /r:System.Drawing.dll
//         /win32icon:whale.ico /out:DSH生物科研一键启动.exe DSH生物科研启动器.cs
// 行为: 无窗口、无任务栏按钮，只驻留系统托盘（黑鲸鱼图标）。
//   启动时临时把默认预设切换为 bio-research -> 必要时后台启动 dsh web（日志写文件）
//   -> 托盘气泡提示 -> 监控 3080 端口，DSH 停止后自动恢复默认预设并退出。
// 用法: DSH生物科研一键启动.exe [--check]
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

class DshTrayLauncher : ApplicationContext
{
    const int PORT = 3080;
    static readonly string HomeDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    static readonly string SettingsPath = Path.Combine(HomeDir, ".dsh", "settings.yaml");
    static readonly string BakPath = SettingsPath + ".launcher-bak";
    static readonly string Workspace = Directory.Exists("G:\\dsh") ? "G:\\dsh" : HomeDir;
    static readonly string LogFile = Path.Combine(Workspace, "dsh-web.log");
    static readonly string CheckFile = Path.Combine(Path.GetDirectoryName(typeof(DshTrayLauncher).Assembly.Location) ?? ".", "check-result.txt");

    NotifyIcon trayIcon;
    Timer monitor;
    Process dshProcess;
    bool startedByUs = false;
    bool exited = false;

    [STAThread]
    static int Main(string[] args)
    {
        if (HasArg(args, "--check"))
            return DoCheck();
        Application.EnableVisualStyles();
        Application.Run(new DshTrayLauncher());
        return 0;
    }

    DshTrayLauncher()
    {
        // 1. 备份并切换默认预设
        try
        {
            string original = File.Exists(SettingsPath) ? File.ReadAllText(SettingsPath, Encoding.UTF8) : "";
            File.WriteAllText(BakPath, original, new UTF8Encoding(false));
            File.WriteAllText(SettingsPath, SetDefaultPreset(original, "bio-research"), new UTF8Encoding(false));
        }
        catch (Exception ex)
        {
            Balloon("启动失败", "无法修改 settings.yaml: " + ex.Message);
            Exit(false);
            return;
        }

        // 2. 托盘图标（黑鲸鱼，取自 exe 自身嵌入图标）
        Icon appIcon;
        try { appIcon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); }
        catch { appIcon = SystemIcons.Application; }
        trayIcon = new NotifyIcon();
        trayIcon.Icon = appIcon;
        trayIcon.Text = "DSH 生物科研模式";
        trayIcon.Visible = true;

        ContextMenuStrip menu = new ContextMenuStrip();
        menu.Items.Add("打开 DSH 界面", null, (s, e) => OpenBrowser());
        menu.Items.Add("查看 DSH 日志", null, (s, e) => OpenLog());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("停止 DSH 并恢复默认", null, (s, e) => { StopDsh(); Exit(true); });
        menu.Items.Add("退出（DSH 保持运行）", null, (s, e) => Exit(true));
        trayIcon.ContextMenuStrip = menu;
        trayIcon.DoubleClick += (s, e) => OpenBrowser();

        // 3. 启动 DSH（未运行时）
        if (!PortOpen(PORT))
        {
            Balloon("生物科研模式", "正在后台启动 dsh web ...");
            StartDsh();
            int waited = 0;
            while (!PortOpen(PORT) && waited < 180000)
            {
                System.Threading.Thread.Sleep(2000);
                waited += 2000;
            }
            if (!PortOpen(PORT))
            {
                Balloon("启动失败", "DSH 180 秒内未就绪，请查看日志: " + LogFile);
                Exit(true);
                return;
            }
            Balloon("生物科研模式已就绪", "http://127.0.0.1:" + PORT + Environment.NewLine + "日志: " + LogFile);
        }
        else
        {
            Balloon("生物科研模式", "DSH 已在运行，直接使用: http://127.0.0.1:" + PORT);
        }
        OpenBrowser();

        // 4. 监控 DSH 状态（每 5 秒）
        monitor = new Timer();
        monitor.Interval = 5000;
        monitor.Tick += delegate(object s, EventArgs e)
        {
            if (!PortOpen(PORT))
            {
                Balloon("DSH 已停止", "默认预设已恢复，本程序将退出。");
                Exit(true);
            }
        };
        monitor.Start();
    }

    void StartDsh()
    {
        try
        {
            string args = "/c \"dsh web\" > \"" + LogFile + "\" 2>&1";
            ProcessStartInfo psi = new ProcessStartInfo("cmd.exe", args);
            psi.WorkingDirectory = Workspace;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            dshProcess = Process.Start(psi);
            startedByUs = true;
        }
        catch (Exception ex)
        {
            Balloon("启动失败", "无法启动 dsh: " + ex.Message + "（请确认 npm install -g @deepseek-ai/dsh）");
        }
    }

    void StopDsh()
    {
        if (startedByUs && dshProcess != null)
        {
            try
            {
                if (!dshProcess.HasExited)
                {
                    ProcessStartInfo psi = new ProcessStartInfo("taskkill", "/pid " + dshProcess.Id + " /T /F");
                    psi.UseShellExecute = false;
                    psi.CreateNoWindow = true;
                    Process.Start(psi).WaitForExit(10000);
                }
            }
            catch { }
        }
    }

    void OpenBrowser()
    {
        try { Process.Start("http://127.0.0.1:" + PORT); }
        catch { }
    }

    void OpenLog()
    {
        try { Process.Start("notepad.exe", LogFile); }
        catch { }
    }

    void Balloon(string title, string text)
    {
        try { trayIcon.ShowBalloonTip(4000, title, text, ToolTipIcon.Info); }
        catch { }
    }

    void Exit(bool restore)
    {
        if (exited) return;
        exited = true;
        if (restore) RestoreDefault();
        if (monitor != null) { monitor.Stop(); monitor.Dispose(); }
        if (trayIcon != null) { trayIcon.Visible = false; trayIcon.Dispose(); }
        Application.Exit();
    }

    static bool HasArg(string[] args, string name)
    {
        foreach (string a in args)
            if (string.Equals(a, name, StringComparison.OrdinalIgnoreCase))
                return true;
        return false;
    }

    static void RestoreDefault()
    {
        try
        {
            if (File.Exists(BakPath))
            {
                File.Copy(BakPath, SettingsPath, true);
                File.Delete(BakPath);
            }
        }
        catch { }
    }

    // 自检: 切换预设 -> 检测端口 -> 恢复，结果写入 check-result.txt（无 UI）
    static int DoCheck()
    {
        string result;
        try
        {
            string original = File.Exists(SettingsPath) ? File.ReadAllText(SettingsPath, Encoding.UTF8) : "";
            File.WriteAllText(BakPath, original, new UTF8Encoding(false));
            File.WriteAllText(SettingsPath, SetDefaultPreset(original, "bio-research"), new UTF8Encoding(false));
            bool open = PortOpen(PORT);
            RestoreDefault();
            string now = File.Exists(SettingsPath) ? File.ReadAllText(SettingsPath, Encoding.UTF8) : "";
            result = "OK port=" + (open ? "running" : "closed")
                   + " restored=" + (now == original ? "yes" : "NO")
                   + " bak=" + (File.Exists(BakPath) ? "left" : "removed");
        }
        catch (Exception ex)
        {
            result = "FAIL " + ex.Message;
        }
        try { File.WriteAllText(CheckFile, result, new UTF8Encoding(false)); }
        catch { }
        return 0;
    }

    // 在 settings.yaml 中把 agent-presets.default 设为 preset
    static string SetDefaultPreset(string content, string preset)
    {
        Regex rx1 = new Regex("(?m)^(\\s*agent-presets:\\s*\\r?\\n)(\\s*default:\\s*)[^\\r\\n]*");
        if (rx1.IsMatch(content))
            return rx1.Replace(content, delegate(Match m) { return m.Groups[1].Value + m.Groups[2].Value + preset; });
        Regex rx2 = new Regex("(?m)^(\\s*agent-presets:\\s*)$");
        if (rx2.IsMatch(content))
            return rx2.Replace(content, delegate(Match m) { return m.Groups[1].Value + Environment.NewLine + "  default: " + preset; });
        StringBuilder sb = new StringBuilder(content);
        if (sb.Length > 0 && !content.EndsWith("\n"))
            sb.Append(Environment.NewLine);
        sb.Append("agent-presets:").Append(Environment.NewLine);
        sb.Append("  default: ").Append(preset).Append(Environment.NewLine);
        return sb.ToString();
    }

    static bool PortOpen(int port)
    {
        try
        {
            using (TcpClient c = new TcpClient())
            {
                IAsyncResult ar = c.BeginConnect("127.0.0.1", port, null, null);
                if (!ar.AsyncWaitHandle.WaitOne(1500))
                    return false;
                c.EndConnect(ar);
                return true;
            }
        }
        catch
        {
            return false;
        }
    }
}
