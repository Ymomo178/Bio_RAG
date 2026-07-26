import { Bot, LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { login, register } from "../api";
import type { User } from "../types";

type AuthScreenProps = {
  onAuthenticated: (user: User) => void;
};

/** 提供登录和注册入口，并在成功后交还用户信息。 */
export function AuthScreen({ onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** 注册或登录，并让 Java 在浏览器中建立 Session。 */
  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "register") await register(email, password);
      onAuthenticated(await login(email, password));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "认证失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-brand">
          <span className="brand-mark"><Bot size={22} /></span>
          <div><strong>Bio-RAG</strong><span>生物信息学知识助手</span></div>
        </div>
        <div className="auth-heading">
          <h1>{mode === "login" ? "登录" : "创建账号"}</h1>
          <p>使用个人账号管理会话与知识库</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            邮箱
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            密码
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={8}
              required
            />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-command" type="submit" disabled={submitting}>
            <LogIn size={17} />
            {submitting ? "正在提交" : mode === "login" ? "登录" : "注册并登录"}
          </button>
        </form>
        <button
          className="text-command"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
        >
          {mode === "login" ? "没有账号？创建一个" : "已有账号？返回登录"}
        </button>
      </section>
    </main>
  );
}
