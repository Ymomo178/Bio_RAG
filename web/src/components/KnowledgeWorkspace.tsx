import { Database, Globe2, Lock, Plus, Trash2 } from "lucide-react";
import { FormEvent, useState } from "react";
import type { KnowledgeBase } from "../types";

type KnowledgeWorkspaceProps = {
  knowledgeBases: KnowledgeBase[];
  isAdmin: boolean;
  busy: boolean;
  onCreate: (name: string, description: string, visibility: "PRIVATE" | "PUBLIC" | "BUILT_IN") => Promise<void>;
  onDelete: (knowledgeBase: KnowledgeBase) => Promise<void>;
  onVisibilityChange: (knowledgeBase: KnowledgeBase, visibility: "PRIVATE" | "PUBLIC") => Promise<void>;
};

/** 提供知识库创建、列表和删除操作。 */
export function KnowledgeWorkspace({
  knowledgeBases,
  isAdmin,
  busy,
  onCreate,
  onDelete,
  onVisibilityChange
}: KnowledgeWorkspaceProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"PRIVATE" | "PUBLIC" | "BUILT_IN">("PRIVATE");

  /** 提交新知识库并清空表单。 */
  async function submit(event: FormEvent) {
    event.preventDefault();
    await onCreate(name, description, visibility);
    setName("");
    setDescription("");
    setVisibility("PRIVATE");
  }

  return (
    <section className="management-workspace">
      <header className="management-header">
        <div><h1>知识库</h1><p>组织个人文档并控制检索范围</p></div>
      </header>
      <div className="management-layout">
        <form className="management-form" onSubmit={submit}>
          <h2>新建知识库</h2>
          <label>名称<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={255} /></label>
          <label>说明<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} /></label>
          <label>可见范围
            <select value={visibility} onChange={(event) => setVisibility(event.target.value as "PRIVATE" | "PUBLIC" | "BUILT_IN")}>
              <option value="PRIVATE">仅自己</option>
              <option value="PUBLIC">公开只读</option>
              {isAdmin && <option value="BUILT_IN">系统内置</option>}
            </select>
          </label>
          <button className="primary-command" type="submit" disabled={busy || !name.trim()}><Plus size={17} />创建</button>
        </form>

        <div className="resource-list">
          <div className="resource-list-head"><strong>可用知识库</strong><span>{knowledgeBases.length}</span></div>
          {knowledgeBases.length === 0 && <div className="empty-resource"><Database size={22} /><span>还没有个人知识库</span></div>}
          {knowledgeBases.map((knowledgeBase) => (
            <article className="resource-row" key={knowledgeBase.id}>
              <span className="resource-icon"><Database size={18} /></span>
              <div className="resource-main">
                <strong>{knowledgeBase.name}</strong>
                <span>{knowledgeBase.description || "暂无说明"} · {knowledgeBase.owned ? "我创建的" : knowledgeBase.ownerEmail}</span>
              </div>
              <span className="visibility-badge">{knowledgeBase.visibility === "PRIVATE" ? "仅自己" : knowledgeBase.visibility === "BUILT_IN" ? "内置" : "公开"}</span>
              {knowledgeBase.owned && knowledgeBase.visibility !== "BUILT_IN" && <button className="secondary-command" onClick={() => void onVisibilityChange(knowledgeBase, knowledgeBase.visibility === "PRIVATE" ? "PUBLIC" : "PRIVATE")}>
                {knowledgeBase.visibility === "PRIVATE" ? <><Globe2 size={15} />发布</> : <><Lock size={15} />取消公开</>}
              </button>}
              {knowledgeBase.editable && <button className="danger-icon" onClick={() => void onDelete(knowledgeBase)} title="删除知识库"><Trash2 size={16} /></button>}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
