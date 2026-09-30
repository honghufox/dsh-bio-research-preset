// askpass.exe 的源码。随插件分发，首次连接时由 ensureAskpass() 编译一次并缓存到
// askpass/askpass.exe（该目录被 .gitignore 忽略，编译产物不进仓库）。
//
// 为什么需要原生 exe：Windows OpenSSH 通过 posix_spawnp 拉起 SSH_ASKPASS 程序，
// 无法执行 .bat —— 实测 `CreateProcessW failed error:2` /
// `ssh_askpass: posix_spawnp: No such file or directory`，三次尝试后 Permission denied。
// 另外 posix_spawnp 还需要 MSYS 的目录在 PATH 上（见 index.js 的 msysBinDir()）。
//
// 契约（与 index.js 的 askpassEnv() 一致）：
//   DSH_ASKPASS_CRED   必填，credentials.json 的路径，内容 {"password":"…","otp":"…"}
//   DSH_ASKPASS_COUNT  选填，调用计数文件；用于「第 1 次问密码、之后问动态口令」
//   DSH_ASKPASS_LOG    选填，把收到的提示词与回答分支追加到该文件（排查认证失败用；
//                      提示词不含任何凭据内容，可安全记录）
//   提示词含 verification / code 时回动态口令，否则按计数判断
using System;
using System.IO;
using System.Text.RegularExpressions;

internal static class AskPass
{
    private static int Main(string[] args)
    {
        try
        {
            string credPath = Environment.GetEnvironmentVariable("DSH_ASKPASS_CRED");
            if (string.IsNullOrEmpty(credPath) || !File.Exists(credPath))
            {
                Console.Error.Write("askpass: DSH_ASKPASS_CRED is unset or the credentials file is missing\n");
                return 1;
            }

            int attempt = 0;
            string countPath = Environment.GetEnvironmentVariable("DSH_ASKPASS_COUNT");
            if (!string.IsNullOrEmpty(countPath))
            {
                try
                {
                    if (File.Exists(countPath))
                    {
                        int parsed;
                        if (int.TryParse(File.ReadAllText(countPath).Trim(), out parsed)) attempt = parsed;
                    }
                    attempt = attempt + 1;
                    File.WriteAllText(countPath, attempt.ToString());
                }
                catch (Exception)
                {
                    // 计数只是辅助信号：写不进去也不影响回答。
                }
            }

            string prompt = args.Length > 0 && args[0] != null ? args[0] : string.Empty;
            bool wantsOtp = Regex.IsMatch(prompt, "verification|code|Code") || attempt > 1;

            string logPath = Environment.GetEnvironmentVariable("DSH_ASKPASS_LOG");
            if (!string.IsNullOrEmpty(logPath))
            {
                try
                {
                    File.AppendAllText(logPath, "attempt=" + attempt + " branch=" + (wantsOtp ? "otp" : "password")
                        + " prompt=" + prompt.Replace("\r", " ").Replace("\n", " ") + "\n");
                }
                catch (Exception)
                {
                    // 日志是排查辅助，失败不影响回答。
                }
            }

            string text = File.ReadAllText(credPath);
            Console.Out.Write(wantsOtp ? Extract(text, "otp") : Extract(text, "password"));
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.Write("askpass: " + error.Message + "\n");
            return 1;
        }
    }

    private static string Extract(string text, string key)
    {
        Match match = Regex.Match(text, "\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
        return match.Success ? match.Groups[1].Value : string.Empty;
    }
}
