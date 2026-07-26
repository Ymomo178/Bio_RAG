import { ShieldCheck, UserCog } from "lucide-react";
import type { AdminUser, User } from "../types";

type Props = { currentUser: User; users: AdminUser[]; onUpdate: (user: AdminUser, status: AdminUser["status"], admin: boolean) => Promise<void> };

/** 管理员查看并调整其他用户的状态和角色。 */
export function AdminWorkspace({ currentUser, users, onUpdate }: Props) {
  return <section className="management-workspace">
    <header className="management-header"><div><h1>用户管理</h1><p>停用账号或授予管理员权限</p></div></header>
    <div className="resource-list admin-list">
      <div className="resource-list-head"><strong>全部用户</strong><span>{users.length}</span></div>
      {users.map((item) => <article className="resource-row" key={item.id}>
        <span className="resource-icon">{item.roles.includes("ADMIN") ? <ShieldCheck size={18} /> : <UserCog size={18} />}</span>
        <div className="resource-main"><strong>{item.email}</strong><span>{item.roles.join(" · ")}</span></div>
        {item.id === currentUser.id ? <span className="visibility-badge">当前账号</span> : <>
          <label className="inline-control"><input type="checkbox" checked={item.roles.includes("ADMIN")} onChange={(event) => void onUpdate(item, item.status, event.target.checked)} />管理员</label>
          <button className="secondary-command" onClick={() => void onUpdate(item, item.status === "ACTIVE" ? "DISABLED" : "ACTIVE", item.roles.includes("ADMIN"))}>{item.status === "ACTIVE" ? "停用" : "启用"}</button>
        </>}
      </article>)}
    </div>
  </section>;
}
