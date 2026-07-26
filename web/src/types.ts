/** 当前登录用户。 */
export type User = {
  id: string;
  email: string;
  status: "ACTIVE" | "DISABLED";
  roles: string[];
};

/** 用户拥有的知识库。 */
export type KnowledgeBase = {
  id: string;
  name: string;
  description: string | null;
  ownerId: string;
  ownerEmail: string;
  visibility: "PRIVATE" | "PUBLIC" | "BUILT_IN";
  owned: boolean;
  editable: boolean;
  createdAt: string;
  updatedAt: string;
};

/** 一条经过 Java 验证并持久化的回答引用。 */
export type Citation = {
  evidenceId: string;
  chunkId: string;
  score: number;
  sourceId: string | null;
  normalizedPath: string | null;
  section: string | null;
  pageNumber: number | null;
  imageIds: string[];
};

/** 可恢复的历史会话摘要。 */
export type Conversation = {
  id: string;
  title: string;
  knowledgeBaseId: string | null;
  knowledgeBaseName: string;
  knowledgeBaseIds: string[];
  knowledgeBaseNames: string[];
  createdAt: string;
  updatedAt: string;
};

/** Java 数据库中保存的一条聊天消息。 */
export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  answerMode: "knowledge_base" | "general_knowledge" | null;
  notice: string | null;
  knowledgeBaseScore: number | null;
  citations: Citation[];
  createdAt: string;
  failed?: boolean;
};

/** 一次完整问答返回的两条消息。 */
export type ChatTurn = {
  conversation: Conversation;
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
  standaloneQuestion: string;
};

/** 上传文档及其索引状态。 */
export type KnowledgeDocument = {
  id: string;
  knowledgeBaseId: string;
  name: string;
  contentType: string;
  status: "UPLOADED" | "INDEXING" | "READY" | "FAILED";
  errorMessage: string | null;
  chunkCount: number;
  imageCount: number;
  createdAt: string;
  updatedAt: string;
};

/** 页面当前显示的工作区。 */
export type Workspace = "chat" | "knowledge" | "documents" | "admin";

/** 管理员用户列表中的安全账号摘要。 */
export type AdminUser = {
  id: string;
  email: string;
  status: "ACTIVE" | "DISABLED";
  roles: string[];
  createdAt: string;
};
