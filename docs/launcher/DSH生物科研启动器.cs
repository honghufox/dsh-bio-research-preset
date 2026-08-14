// DSH 生物科研模式一键启动器
// 编译: csc.exe /nologo /codepage:65001 /out:DSH生物科研一键启动.exe DSH生物科研启动器.cs
// 功能: 临时把默认预设切换为 bio-research -> 启动 dsh web -> 打开浏览器 ->
//       等待 DSH 退出后恢复原默认预设。
// 用法: DSH生物科研一键启动.exe [--check] [--no-browser]
using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

class DshBioLauncher
{
    const int PORT = 3080;
    const int SW_MINIMIZE = 6;
    static readonly string HomeDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
    static readonly string SettingsPath = Path.Combine(HomeDir, ".dsh", "settings.yaml");
    static readonly string BakPath = SettingsPath + ".launcher-bak";
    static readonly string Workspace = Directory.Exists("G:\\dsh") ? "G:\\dsh" : HomeDir;

    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")]   static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    static int Main(string[] args)
    {
        bool check = HasArg(args, "--check");
        bool noBrowser = HasArg(args, "--no-browser");
        bool noMinimize = HasArg(args, "--no-minimize");

        // 默认把控制台窗口最小化到任务栏，降低误关闭几率（自检模式保持可见）
        if (!check && !noMinimize)
        {
            IntPtr hwnd = GetConsoleWindow();
            if (hwnd != IntPtr.Zero)
                ShowWindow(hwnd, SW_MINIMIZE);
        }

        Console.WriteLine("==============================================");
        Console.WriteLine("  DSH 生物科研模式一键启动器");
        Console.WriteLine("==============================================");

        // 1. 备份并切换默认预设
        string original = "";
        try
        {
            if (File.Exists(SettingsPath))
                original = File.ReadAllText(SettingsPath, Encoding.UTF8);
            File.WriteAllText(BakPath, original, new UTF8Encoding(false));
            string next = SetDefaultPreset(original, "bio-research");
            File.WriteAllText(SettingsPath, next, new UTF8Encoding(false));
            Console.WriteLine("[1/4] 默认预设已切换为 bio-research（退出本程序时自动恢复）");
        }
        catch (Exception ex)
        {
            Console.WriteLine("错误: 无法修改 settings.yaml: " + ex.Message);
            return 1;
        }

        if (check)
        {
            Console.WriteLine("自检模式: 预设切换 OK，端口 3080 = " + (PortOpen(PORT) ? "已运行" : "未运行"));
            RestoreDefault();
            Console.WriteLine("自检完成，已恢复原预设。");
            return 0;
        }

        // 2. 检查/启动 DSH
        bool already = PortOpen(PORT);
        if (!already)
        {
            Console.WriteLine("[2/4] DSH 未运行，正在启动 dsh web（工作目录: " + Workspace + "）...");
            try
            {
                var psi = new ProcessStartInfo("cmd.exe", "/c start /min \"DSH Web\" dsh web");
                psi.WorkingDirectory = Workspace;
                psi.UseShellExecute = true;
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                Console.WriteLine("错误: 无法启动 dsh: " + ex.Message);
                RestoreDefault();
                return 1;
            }
            int waited = 0;
            while (!PortOpen(PORT) && waited < 180000)
            {
                Thread.Sleep(2000);
                waited += 2000;
                if (waited % 20000 == 0)
                    Console.WriteLine("    等待 DSH 就绪 ... " + (waited / 1000) + "s");
            }
            if (!PortOpen(PORT))
            {
                Console.WriteLine("错误: DSH 启动超时（180s），请查看 DSH 窗口日志。");
                RestoreDefault();
                return 1;
            }
            Console.WriteLine("    DSH 已就绪 (http://127.0.0.1:" + PORT + ")");
        }
        else
        {
            Console.WriteLine("[2/4] 检测到 DSH 已在运行 (http://127.0.0.1:" + PORT + ")，直接使用。");
        }

        // 3. 打开浏览器
        Console.WriteLine("[3/4] 正在打开浏览器 ...");
        if (!noBrowser)
        {
            try { Process.Start("http://127.0.0.1:" + PORT); }
            catch (Exception ex) { Console.WriteLine("    打开浏览器失败: " + ex.Message + "（可手动访问）"); }
        }

        // 4. 等待 DSH 停止 / Ctrl+C
        Console.WriteLine("[4/4] DSH 运行中。窗口已最小化到任务栏（点击任务栏按钮查看状态）。");
        Console.WriteLine("    关闭 DSH 窗口后本程序自动恢复默认预设；按 Ctrl+C 立即恢复并退出。");
        Console.CancelKeyPress += delegate(object s, ConsoleCancelEventArgs e)
        {
            e.Cancel = true;
            RestoreDefault();
            Console.WriteLine("已恢复默认预设。DSH 仍在运行。");
            Environment.Exit(0);
        };

        while (PortOpen(PORT))
            Thread.Sleep(5000);

        RestoreDefault();
        Console.WriteLine("DSH 已停止，默认预设已恢复。按任意键退出 ...");
        Console.ReadKey();
        return 0;
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
                Console.WriteLine("已恢复原默认预设。");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine("警告: 恢复 settings.yaml 失败: " + ex.Message + "（当前默认预设为 bio-research，可手动编辑 " + SettingsPath + "）");
        }
    }

    // 在 settings.yaml 中把 agent-presets.default 设为 preset
    static string SetDefaultPreset(string content, string preset)
    {
        // 情况 1: 已有 agent-presets 块且含 default 行
        Regex rx1 = new Regex("(?m)^(\\s*agent-presets:\\s*\\r?\\n)(\\s*default:\\s*)[^\\r\\n]*");
        if (rx1.IsMatch(content))
            return rx1.Replace(content, delegate(Match m) { return m.Groups[1].Value + m.Groups[2].Value + preset; });

        // 情况 2: 已有 agent-presets 块但无 default 行
        Regex rx2 = new Regex("(?m)^(\\s*agent-presets:\\s*)$");
        if (rx2.IsMatch(content))
            return rx2.Replace(content, delegate(Match m) { return m.Groups[1].Value + Environment.NewLine + "  default: " + preset; });

        // 情况 3: 文件无 agent-presets 块（或文件不存在）→ 追加
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
