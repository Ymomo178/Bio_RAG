import type {
  ChatMessage,
  ChatTurn,
  Conversation,
  KnowledgeBase,
  KnowledgeDocument,
  User
  , AdminUser
} from "./types";

type ApiError = {
  code: string;
  message: string;
};

type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  error?: ApiError;
};

/** 统一解析 Java 的 ApiResponse，并把业务错误转成页面可显示的异常。 */
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => null)) as ApiEnvelope<T> | null;
  if (!response.ok || !payload?.success) {
    throw new Error(payload?.error?.message ?? `请求失败：${response.status}`);
  }
  return payload.data;
}

/** 使用邮箱和密码建立 Java Session。 */
export function login(email: string, password: string): Promise<User> {
  return request<User>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
}

/** 创建账号，注册成功后由页面继续执行登录。 */
export function register(email: string, password: string): Promise<User> {
  return request<User>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
}

/** 恢复浏览器现有 Session 中的用户。 */
export function currentUser(): Promise<User> {
  return request<User>("/api/auth/me");
}

/** 注销当前 Session。 */
export function logout(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" });
}

/** 加载用户会话列表。 */
export function listConversations(): Promise<Conversation[]> {
  return request<Conversation[]>("/api/conversations");
}

/** 创建一个绑定可选知识库的新会话。 */
export function createConversation(knowledgeBaseIds: string[]): Promise<Conversation> {
  return request<Conversation>("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ knowledgeBaseIds })
  });
}

/** 加载指定会话的完整消息历史。 */
export function listMessages(conversationId: string): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/conversations/${conversationId}/messages`);
}

/** 通过 Java 发送问题，由 Java 持久化后再调用 Python。 */
export function sendMessage(conversationId: string, content: string): Promise<ChatTurn> {
  return request<ChatTurn>(`/api/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });
}

/** 删除会话及其全部历史消息。 */
export function deleteConversation(conversationId: string): Promise<void> {
  return request<void>(`/api/conversations/${conversationId}`, { method: "DELETE" });
}

/** 加载当前用户拥有的知识库。 */
export function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return request<KnowledgeBase[]>("/api/knowledge-bases");
}

/** 创建一个新的用户知识库。 */
export function createKnowledgeBase(
  name: string,
  description: string,
  visibility: "PRIVATE" | "PUBLIC" | "BUILT_IN"
): Promise<KnowledgeBase> {
  return request<KnowledgeBase>("/api/knowledge-bases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, visibility })
  });
}

/** 删除知识库。 */
export function deleteKnowledgeBase(knowledgeBaseId: string): Promise<void> {
  return request<void>(`/api/knowledge-bases/${knowledgeBaseId}`, { method: "DELETE" });
}

/** 发布、取消公开或修改知识库信息。 */
export function updateKnowledgeBase(knowledgeBase: KnowledgeBase, visibility: "PRIVATE" | "PUBLIC"): Promise<KnowledgeBase> {
  return request<KnowledgeBase>(`/api/knowledge-bases/${knowledgeBase.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: knowledgeBase.name, description: knowledgeBase.description, visibility })
  });
}

/** 管理员加载全部用户。 */
export function listAdminUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>("/api/admin/users");
}

/** 管理员修改用户状态和角色。 */
export function updateAdminUser(userId: string, status: "ACTIVE" | "DISABLED", admin: boolean): Promise<AdminUser> {
  return request<AdminUser>(`/api/admin/users/${userId}`, {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, admin })
  });
}

/** 加载指定知识库的文档和索引状态。 */
export function listDocuments(knowledgeBaseId: string): Promise<KnowledgeDocument[]> {
  return request<KnowledgeDocument[]>(`/api/knowledge-bases/${knowledgeBaseId}/documents`);
}

/** 上传文档，由 Java 保存后同步交给 Python 建立索引。 */
export function uploadDocument(
  knowledgeBaseId: string,
  file: File
): Promise<KnowledgeDocument> {
  const form = new FormData();
  form.append("file", file);
  return request<KnowledgeDocument>(`/api/knowledge-bases/${knowledgeBaseId}/documents`, {
    method: "POST",
    body: form
  });
}

/** 删除文档和对应的向量文本块。 */
export function deleteDocument(
  knowledgeBaseId: string,
  documentId: string
): Promise<void> {
  return request<void>(
    `/api/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`,
    { method: "DELETE" }
  );
}
