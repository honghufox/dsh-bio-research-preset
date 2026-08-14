// DSH 生物科研模式一键启动器（系统托盘版 v3）
// 编译:
//   csc.exe /nologo /codepage:65001 /target:winexe /optimize
//         /r:System.Windows.Forms.dll /r:System.Drawing.dll
//         /win32icon:whale.ico /out:DSH生物科研一键启动.exe DSH生物科研启动器.cs
// 行为: 无窗口、无任务栏按钮，只驻留系统托盘（黑鲸鱼图标）。
//   v3 修复: 异步启动不再卡死 UI；用批处理文件启动 dsh 规避 cmd 引号/重定向解析问题；
//   单实例互斥（重复双击只打开浏览器）；「停止 DSH」按 3080 端口定位进程整树结束。
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

class DshTrayApp : Form
{
    const int PORT = 3080;
    const string MutexName = "DSHBioResearchLauncher";
    static readonly string HomeDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    static readonly string SettingsPath = Path.Combine(HomeDir, ".dsh", "settings.yaml");
    static readonly string BakPath = SettingsPath + ".launcher-bak";
    static readonly string Workspace = Directory.Exists("G:\\dsh") ? "G:\\dsh" : HomeDir;
    static readonly string LogFile = Path.Combine(Workspace, "dsh-web.log");
    static readonly string ExeDir = Path.GetDirectoryName(typeof(DshTrayApp).Assembly.Location) ?? ".";
    static readonly string CheckFile = Path.Combine(ExeDir, "check-result.txt");
    static readonly string BatFile = Path.Combine(ExeDir, "start-dsh.bat");

    NotifyIcon trayIcon;
    System.Windows.Forms.Timer monitor;
    Process dshProc;
    bool startedByUs = false;
    bool exited = false;

    [STAThread]
    static int Main(string[] args)
    {
        if (HasArg(args, "--check"))
            return DoCheck();

        bool createdNew;
        using (Mutex m = new Mutex(true, MutexName, out createdNew))
        {
            if (!createdNew)
            {
                // 已有实例在托盘运行：重复双击只打开浏览器
                try { Process.Start("http://127.0.0.1:" + PORT); }
                catch { }
                return 0;
            }
            Application.EnableVisualStyles();
            Application.Run(new DshTrayApp());
        }
        return 0;
    }

    DshTrayApp()
    {
        // 隐藏窗口作为消息循环宿主（保证 BeginInvoke 可用）
        ShowInTaskbar = false;
        WindowState = FormWindowState.Minimized;
        Opacity = 0;
        Show();
        Hide();

        // 1. 备份并切换默认预设（快速，无 UI）
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

        // 2. 托盘图标（黑鲸鱼，取自 exe 嵌入图标）
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
        menu.Items.Add("停止 DSH（含外部启动的实例）并恢复默认", null, (s, e) => { StopDsh(); Exit(true); });
        menu.Items.Add("退出（DSH 保持运行）", null, (s, e) => Exit(true));
        trayIcon.ContextMenuStrip = menu;
        trayIcon.DoubleClick += (s, e) => OpenBrowser();

        // 3. 异步启动流程（不阻塞 UI 线程）
        Task.Run((Action)Startup);

        // 4. 监控 DSH 状态
        monitor = new System.Windows.Forms.Timer();
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

    // 后台线程: 启动 DSH（若未运行）→ 等就绪 → 打开浏览器
    void Startup()
    {
        try
        {
            if (!PortOpen(PORT))
            {
                Balloon("生物科研模式", "正在后台启动 dsh web ...");
                StartDsh();
                int waited = 0;
                while (!PortOpen(PORT) && waited < 180000)
                {
                    Thread.Sleep(2000);
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
        }
        catch (Exception ex)
        {
            Balloon("启动异常", ex.Message);
            Exit(true);
        }
    }

    // 用批处理文件启动 dsh（规避 cmd /c "..." 重定向被吞的解析问题）
    void StartDsh()
    {
        try
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("@echo off");
            sb.AppendLine("\"dsh\" web > \"" + LogFile + "\" 2>&1");
            File.WriteAllText(BatFile, sb.ToString(), new UTF8Encoding(false));

            ProcessStartInfo psi = new ProcessStartInfo("cmd.exe", "/c \"" + BatFile + "\"");
            psi.WorkingDirectory = Workspace;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            dshProc = Process.Start(psi);
            startedByUs = true;
        }
        catch (Exception ex)
        {
            Balloon("启动失败", "无法启动 dsh: " + ex.Message + "（请确认 npm install -g @deepseek-ai/dsh）");
        }
    }

    void StopDsh()
    {
        if (startedByUs && dshProc != null)
        {
            try { if (!dshProc.HasExited) KillTree(dshProc.Id); }
            catch { }
        }
        int pid = FindPidOnPort(PORT);
        if (pid > 0) KillTree(pid);
    }

    static int FindPidOnPort(int port)
    {
        try
        {
            Process p = new Process();
            p.StartInfo = new ProcessStartInfo("netstat", "-ano");
            p.StartInfo.UseShellExecute = false;
            p.StartInfo.CreateNoWindow = true;
            p.StartInfo.RedirectStandardOutput = true;
            p.Start();
            string output = p.StandardOutput.ReadToEnd();
            p.WaitForExit(5000);
            string token = ":" + port;
            foreach (string line in output.Split('\n'))
            {
                string t = line.Trim();
                if (t.Contains(token) && (t.Contains("LISTENING") || t.Contains("LISTEN")))
                {
                    string[] parts = t.Split(new char[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 5)
                    {
                        int pid;
                        if (int.TryParse(parts[parts.Length - 1], out pid))
                            return pid;
                    }
                }
            }
        }
        catch { }
        return 0;
    }

    static void KillTree(int pid)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo("taskkill", "/pid " + pid + " /T /F");
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;
            Process.Start(psi).WaitForExit(10000);
        }
        catch { }
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

    // 气泡提示：必须回到 UI 线程
    void Balloon(string title, string text)
    {
        try
        {
            BeginInvoke(new Action(delegate()
            {
                try { if (trayIcon != null) trayIcon.ShowBalloonTip(4000, title, text, ToolTipIcon.Info); }
                catch { }
            }));
        }
        catch { }
    }

    void Exit(bool restore)
    {
        if (exited) return;
        exited = true;
        try { if (restore) RestoreDefault(); } catch { }
        try { if (monitor != null) { monitor.Stop(); monitor.Dispose(); } } catch { }
        try { if (trayIcon != null) { trayIcon.Visible = false; trayIcon.Dispose(); } } catch { }
        try { Close(); } catch { }
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

    // 自检: 切换预设 -> 检测端口/PID -> 恢复，结果写 check-result.txt（无 UI）
    static int DoCheck()
    {
        string result;
        try
        {
            string original = File.Exists(SettingsPath) ? File.ReadAllText(SettingsPath, Encoding.UTF8) : "";
            File.WriteAllText(BakPath, original, new UTF8Encoding(false));
            File.WriteAllText(SettingsPath, SetDefaultPreset(original, "bio-research"), new UTF8Encoding(false));
            bool open = PortOpen(PORT);
            int pid = open ? FindPidOnPort(PORT) : 0;
            RestoreDefault();
            string now = File.Exists(SettingsPath) ? File.ReadAllText(SettingsPath, Encoding.UTF8) : "";
            result = "OK port=" + (open ? "running(pid " + pid + ")" : "closed")
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
