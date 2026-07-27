import {
  Bot,
  Database,
  FileText,
  LogOut,
  ShieldCheck,
  MessageSquare,
  Plus,
  Trash2
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import * as api from "./api";
import { AuthScreen } from "./components/AuthScreen";
import { AdminWorkspace } from "./components/AdminWorkspace";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { DocumentWorkspace } from "./components/DocumentWorkspace";
import { KnowledgeWorkspace } from "./components/KnowledgeWorkspace";
import type {
  ChatMessage,
  AdminUser,
  Conversation,
  KnowledgeBase,
  KnowledgeDocument,
  User,
  Workspace
} from "./types";

/** 管理登录状态、三类工作区数据和完整的 Java API 调用。 */
function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [workspace, setWorkspace] = useState<Workspace>("chat");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [newChatKnowledgeBaseIds, setNewChatKnowledgeBaseIds] = useState<string[]>([]);
  const [documentKnowledgeBaseId, setDocumentKnowledgeBaseId] = useState("");
  const [sendingConversationIds, setSendingConversationIds] = useState<Set<string>>(new Set());
  const currentConversationIdRef = useRef<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.currentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    if (user) void loadWorkspace();
  }, [user]);

  useEffect(() => {
    if (!documentKnowledgeBaseId) {
      setDocuments([]);
      return;
    }
    api.listDocuments(documentKnowledgeBaseId)
      .then(setDocuments)
      .catch(showError);
  }, [documentKnowledgeBaseId]);

  useEffect(() => {
    if (workspace === "admin" && user?.roles.includes("ADMIN")) api.listAdminUsers().then(setAdminUsers).catch(showError);
  }, [workspace, user]);

  /** 登录后并行加载知识库和会话，并恢复最近一条会话。 */
  async function loadWorkspace() {
    setError(null);
    try {
      const [loadedKnowledgeBases, loadedConversations] = await Promise.all([
        api.listKnowledgeBases(),
        api.listConversations()
      ]);
      setKnowledgeBases(loadedKnowledgeBases);
      setConversations(loadedConversations);
      if (loadedConversations.length > 0) {
        await selectConversation(loadedConversations[0]);
      } else {
        setCurrentConversation(null);
        setMessages([]);
      }
      if (loadedKnowledgeBases.length > 0) {
        setDocumentKnowledgeBaseId((current) => current || loadedKnowledgeBases.find((item) => item.editable)?.id || loadedKnowledgeBases[0].id);
      }
    } catch (cause) {
      showError(cause);
    }
  }

  /** 选择会话并从 Java 数据库恢复全部消息。 */
  async function selectConversation(conversation: Conversation) {
    currentConversationIdRef.current = conversation.id;
    setCurrentConversation(conversation);
    setWorkspace("chat");
    setError(null);
    try {
      const loaded = await api.listMessages(conversation.id);
      if (currentConversationIdRef.current === conversation.id) setMessages(loaded);
    } catch (cause) {
      showError(cause);
    }
  }

  /** 立即创建一条空会话，并绑定侧栏中选择的知识库。 */
  async function newConversation(): Promise<Conversation | null> {
    setError(null);
    try {
      const conversation = await api.createConversation(newChatKnowledgeBaseIds);
      setConversations((current) => [conversation, ...current]);
      setCurrentConversation(conversation);
      currentConversationIdRef.current = conversation.id;
      setMessages([]);
      setWorkspace("chat");
      return conversation;
    } catch (cause) {
      showError(cause);
      return null;
    }
  }

  /** 向当前会话发送问题，并用 Java 返回的持久化消息替换临时消息。 */
  async function send(content: string) {
    let conversation = currentConversation;
    if (!conversation) conversation = await newConversation();
    if (!conversation) return;

    const temporaryId = `temporary-${crypto.randomUUID()}`;
    const temporaryMessage: ChatMessage = {
      id: temporaryId,
      role: "user",
      content,
      answerMode: null,
      notice: null,
      knowledgeBaseScore: null,
      citations: [],
      createdAt: new Date().toISOString()
    };
    setMessages((current) => [...current, temporaryMessage]);
    setSendingConversationIds((current) => new Set(current).add(conversation.id));
    setError(null);
    try {
      const turn = await api.sendMessage(conversation.id, content);
      if (currentConversationIdRef.current === conversation.id) {
        setMessages((current) => [
          ...current.filter((message) => message.id !== temporaryId),
          turn.userMessage,
          turn.assistantMessage
        ]);
        setCurrentConversation(turn.conversation);
      }
      setConversations((current) => [
        turn.conversation,
        ...current.filter((item) => item.id !== turn.conversation.id)
      ]);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "问答失败";
      if (currentConversationIdRef.current === conversation.id) setMessages((current) => [
        ...current.filter((item) => item.id !== temporaryId), {
          id: `failed-${crypto.randomUUID()}`,
          role: "assistant",
          content: message,
          answerMode: null,
          notice: null,
          knowledgeBaseScore: null,
          citations: [],
          createdAt: new Date().toISOString(),
          failed: true
        }
      ]);
      setError(message);
    } finally {
      setSendingConversationIds((current) => {
        const next = new Set(current); next.delete(conversation.id); return next;
      });
    }
  }

  /** 删除会话并切换到剩余的第一条会话。 */
  async function removeConversation(conversation: Conversation) {
    if (!window.confirm(`删除会话“${conversation.title}”？`)) return;
    try {
      await api.deleteConversation(conversation.id);
      const remaining = conversations.filter((item) => item.id !== conversation.id);
      setConversations(remaining);
      if (currentConversation?.id === conversation.id) {
        if (remaining[0]) await selectConversation(remaining[0]);
        else {
          setCurrentConversation(null);
          currentConversationIdRef.current = null;
          setMessages([]);
        }
      }
    } catch (cause) {
      showError(cause);
    }
  }

  /** 创建个人知识库并刷新可选范围。 */
  async function addKnowledgeBase(
    name: string,
    description: string,
    visibility: "PRIVATE" | "PUBLIC" | "BUILT_IN"
  ) {
    setBusy(true);
    try {
      const created = await api.createKnowledgeBase(name, description, visibility);
      setKnowledgeBases((current) => [created, ...current]);
      setDocumentKnowledgeBaseId(created.id);
    } catch (cause) {
      showError(cause);
    } finally {
      setBusy(false);
    }
  }

  /** 删除空知识库，并同步清理页面选择。 */
  async function removeKnowledgeBase(knowledgeBase: KnowledgeBase) {
    if (!window.confirm(`删除知识库“${knowledgeBase.name}”？请先删除其中的文档。`)) return;
    try {
      await api.deleteKnowledgeBase(knowledgeBase.id);
      setKnowledgeBases((current) => current.filter((item) => item.id !== knowledgeBase.id));
      if (documentKnowledgeBaseId === knowledgeBase.id) setDocumentKnowledgeBaseId("");
      setNewChatKnowledgeBaseIds((current) => current.filter((id) => id !== knowledgeBase.id));
    } catch (cause) {
      showError(cause);
    }
  }

  /** 发布或取消公开自己的知识库。 */
  async function changeKnowledgeBaseVisibility(knowledgeBase: KnowledgeBase, visibility: "PRIVATE" | "PUBLIC") {
    try {
      const updated = await api.updateKnowledgeBase(knowledgeBase, visibility);
      setKnowledgeBases((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) { showError(cause); }
  }

  /** 管理员修改其他用户的状态或角色。 */
  async function updateAdminUser(item: AdminUser, status: AdminUser["status"], admin: boolean) {
    try {
      const updated = await api.updateAdminUser(item.id, status, admin);
      setAdminUsers((current) => current.map((userItem) => userItem.id === updated.id ? updated : userItem));
    } catch (cause) { showError(cause); }
  }

  /** 上传一个文件并把 Python 返回的最终索引状态放入文档列表。 */
  async function addDocument(file: File) {
    if (!documentKnowledgeBaseId) throw new Error("请先选择知识库");
    setBusy(true);
    setError(null);
    try {
      const created = await api.uploadDocument(documentKnowledgeBaseId, file);
      setDocuments((current) => [created, ...current]);
    } finally {
      setBusy(false);
    }
  }

  /** 删除文档和数据库中的向量文本块。 */
  async function removeDocument(document: KnowledgeDocument) {
    if (!window.confirm(`删除文档“${document.name}”及其索引？`)) return;
    try {
      await api.deleteDocument(document.knowledgeBaseId, document.id);
      setDocuments((current) => current.filter((item) => item.id !== document.id));
    } catch (cause) {
      showError(cause);
    }
  }

  /** 注销 Session 并清空浏览器内的工作区状态。 */
  async function signOut() {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setConversations([]);
      setKnowledgeBases([]);
      setMessages([]);
      setCurrentConversation(null);
      currentConversationIdRef.current = null;
    }
  }

  /** 把未知异常转换成页面顶部错误提示。 */
  function showError(cause: unknown) {
    setError(cause instanceof Error ? cause.message : "请求失败");
  }

  if (checkingSession) return <div className="boot-screen">正在连接 Java 后端...</div>;
  if (!user) return <AuthScreen onAuthenticated={setUser} />;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <span className="brand-mark"><Bot size={19} /></span>
          <div><strong>Bio-RAG</strong><span>生物信息学助手</span></div>
        </div>

        <div className="new-chat-controls">
          <details className="kb-multi-select">
            <summary>{newChatKnowledgeBaseIds.length ? `已选 ${newChatKnowledgeBaseIds.length} 个知识库` : "内置知识库"}</summary>
            <div className="kb-options">
              {knowledgeBases.map((item) => <label key={item.id}>
                <input type="checkbox" checked={newChatKnowledgeBaseIds.includes(item.id)} onChange={() => setNewChatKnowledgeBaseIds((current) => current.includes(item.id) ? current.filter((id) => id !== item.id) : [...current, item.id])} />
                <span>{item.name}</span>
              </label>)}
            </div>
          </details>
          <button className="new-chat-button" onClick={() => void newConversation()}><Plus size={17} />新建对话</button>
        </div>

        <nav className="sidebar-nav" aria-label="主导航">
          <button className={workspace === "chat" ? "active" : ""} onClick={() => setWorkspace("chat")}><MessageSquare size={17} />问答</button>
          <button className={workspace === "knowledge" ? "active" : ""} onClick={() => setWorkspace("knowledge")}><Database size={17} />知识库<span>{knowledgeBases.length}</span></button>
          <button className={workspace === "documents" ? "active" : ""} onClick={() => setWorkspace("documents")}><FileText size={17} />文档<span>{documents.length}</span></button>
          {user.roles.includes("ADMIN") && <button className={workspace === "admin" ? "active" : ""} onClick={() => setWorkspace("admin")}><ShieldCheck size={17} />管理</button>}
        </nav>

        <div className="conversation-section">
          <div className="sidebar-label">最近会话</div>
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <div className={`conversation-item ${currentConversation?.id === conversation.id ? "selected" : ""}`} key={conversation.id}>
                <button onClick={() => void selectConversation(conversation)} title={conversation.title}>
                  <MessageSquare size={15} /><span>{conversation.title}</span>
                </button>
                <button className="conversation-delete" onClick={() => void removeConversation(conversation)} title="删除会话"><Trash2 size={14} /></button>
              </div>
            ))}
          </div>
        </div>

        <div className="account-row">
          <span>{user.email}</span>
          <button onClick={() => void signOut()} title="退出登录"><LogOut size={16} /></button>
        </div>
      </aside>

      <main className="main-area">
        {error && <div className="global-error"><span>{error}</span><button onClick={() => setError(null)}>关闭</button></div>}
        {workspace === "chat" && (
          <ChatWorkspace conversation={currentConversation} messages={messages} sending={currentConversation ? sendingConversationIds.has(currentConversation.id) : false} onSend={send} />
        )}
        {workspace === "knowledge" && (
          <KnowledgeWorkspace knowledgeBases={knowledgeBases} isAdmin={user.roles.includes("ADMIN")} busy={busy} onCreate={addKnowledgeBase} onDelete={removeKnowledgeBase} onVisibilityChange={changeKnowledgeBaseVisibility} />
        )}
        {workspace === "documents" && (
          <DocumentWorkspace
            knowledgeBases={knowledgeBases}
            documents={documents}
            selectedKnowledgeBaseId={documentKnowledgeBaseId}
            busy={busy}
            onSelectKnowledgeBase={setDocumentKnowledgeBaseId}
            onUpload={addDocument}
            onDelete={removeDocument}
          />
        )}
        {workspace === "admin" && user.roles.includes("ADMIN") && <AdminWorkspace currentUser={user} users={adminUsers} onUpdate={updateAdminUser} />}
      </main>
    </div>
  );
}

export default App;
