import { Bot, ChevronDown, Image as ImageIcon, Send } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage, Citation, Conversation } from "../types";

type ChatWorkspaceProps = {
  conversation: Conversation | null;
  messages: ChatMessage[];
  sending: boolean;
  onSend: (content: string) => Promise<void>;
};

/** 展示当前持久化会话，并负责收集用户的新问题。 */
export function ChatWorkspace({
  conversation,
  messages,
  sending,
  onSend
}: ChatWorkspaceProps) {
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  /** 清空输入框并把问题交给 Java 会话接口。 */
  async function submit(event: FormEvent) {
    event.preventDefault();
    await sendDraft();
  }

  /** 发送当前输入框内容，供表单提交和回车快捷发送复用。 */
  async function sendDraft() {
    const content = draft.trim();
    if (!content || sending) return;
    setDraft("");
    await onSend(content);
  }

  return (
    <section className="chat-workspace">
      <header className="workspace-header">
        <div>
          <h1>{conversation?.title ?? "新对话"}</h1>
          <span>{conversation?.knowledgeBaseName ?? "内置知识库"}</span>
        </div>
        <div className="model-state"><span className="status-dot" />Qwen</div>
      </header>

      <div className="messages">
        <div className="message-column">
          {messages.length === 0 && (
            <div className="empty-chat">
              <span className="assistant-avatar"><Bot size={18} /></span>
              <p>请输入一个生物信息学问题。当前会话会自动保存，后续追问可以引用前文。</p>
            </div>
          )}
          {messages.map((message) => <Message key={message.id} message={message} />)}
          {sending && <LoadingMessage />}
          <div ref={endRef} />
        </div>
      </div>

      <div className="composer-wrap">
        <form className="composer" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void sendDraft();
              }
            }}
            placeholder="输入问题"
            rows={1}
            disabled={sending}
          />
          <button className="send-button" type="submit" disabled={!draft.trim() || sending} title="发送">
            <Send size={18} />
          </button>
        </form>
        <p>AI 生成内容可能存在误差，请核对引用和官方文档。</p>
      </div>
    </section>
  );
}

/** 按角色展示一条用户或助手消息。 */
function Message({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return <article className="message-row user-row"><div className="user-message">{message.content}</div></article>;
  }
  const relatedImages = collectRelatedImages(message.citations);
  return (
    <article className={`message-row assistant-row ${message.failed ? "failed" : ""}`}>
      <div className="assistant-avatar"><Bot size={17} /></div>
      <div className="assistant-content">
        {message.answerMode && <AnswerMode message={message} />}
        {message.notice && <div className="fallback-notice">{message.notice}</div>}
        <div className="answer-text"><ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown></div>
        {relatedImages.length > 0 && <RelatedImageGallery images={relatedImages} />}
        {message.citations.length > 0 && <CitationList citations={message.citations} />}
      </div>
    </article>
  );
}

type RelatedImage = {
  imageId: string;
  sourceId: string;
  evidenceIds: string[];
};

/** 汇总并去重所有引用中的原图，让图片直接出现在回答区域。 */
function collectRelatedImages(citations: Citation[]): RelatedImage[] {
  const images = new Map<string, RelatedImage>();
  for (const citation of citations) {
    for (const imageId of citation.imageIds ?? []) {
      const existing = images.get(imageId);
      if (existing) {
        if (!existing.evidenceIds.includes(citation.evidenceId)) {
          existing.evidenceIds.push(citation.evidenceId);
        }
        continue;
      }
      images.set(imageId, {
        imageId,
        sourceId: citation.sourceId ?? "知识库文档",
        evidenceIds: [citation.evidenceId]
      });
    }
  }
  return [...images.values()];
}

/** 直接展示与回答相关的原始图片，点击缩略图可在新标签页查看原图。 */
function RelatedImageGallery({ images }: { images: RelatedImage[] }) {
  return (
    <section className="related-images" aria-label="相关原图">
      <div className="related-images-heading">
        <ImageIcon size={15} />
        <span>相关原图</span>
        <small>{images.length}</small>
      </div>
      <div className="related-images-grid">
        {images.map((item) => (
          <a
            href={`/api/assets/${encodeURIComponent(item.imageId)}`}
            key={item.imageId}
            target="_blank"
            rel="noreferrer"
            title="打开原图"
          >
            <img
              src={`/api/assets/${encodeURIComponent(item.imageId)}`}
              alt={`${item.sourceId} 原图`}
              loading="lazy"
            />
            <span>{item.sourceId}</span>
            <small>{item.evidenceIds.join(" / ")}</small>
          </a>
        ))}
      </div>
    </section>
  );
}

/** 标识回答来自知识库证据还是 Qwen 通用知识。 */
function AnswerMode({ message }: { message: ChatMessage }) {
  const knowledge = message.answerMode === "knowledge_base";
  return (
    <div className={`answer-mode ${knowledge ? "knowledge-mode" : "general-mode"}`}>
      <span>{knowledge ? "知识库回答" : "通用模型回答"}</span>
      {message.knowledgeBaseScore !== null && (
        <span>匹配度 {(message.knowledgeBaseScore * 100).toFixed(1)}%</span>
      )}
    </div>
  );
}

/** 展示可展开的引用来源和文本块位置。 */
function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="citation-list">
      <div className="citation-heading">引用来源 <span>{citations.length}</span></div>
      {citations.map((citation) => (
        <details className="citation-item" key={`${citation.evidenceId}-${citation.chunkId}`}>
          <summary>
            <span className="citation-index">{citation.evidenceId}</span>
            <span className="citation-title">
              <strong>{citation.sourceId ?? "未知来源"}</strong>
              <small>{citation.section ?? citation.normalizedPath ?? citation.chunkId}</small>
            </span>
            <span className="citation-score">{(citation.score * 100).toFixed(1)}%</span>
            <ChevronDown size={16} />
          </summary>
          <div className="citation-details">
            {citation.pageNumber !== null && <span>第 {citation.pageNumber} 页</span>}
            <span>{citation.normalizedPath}</span>
            <code>{citation.chunkId}</code>
          </div>
          {(citation.imageIds ?? []).length > 0 && <div className="citation-images">
            {(citation.imageIds ?? []).map((imageId) => <a key={imageId} href={`/api/assets/${encodeURIComponent(imageId)}`} target="_blank" rel="noreferrer">
              <img src={`/api/assets/${encodeURIComponent(imageId)}`} alt={`${citation.sourceId ?? "文档"} 原图`} loading="lazy" />
            </a>)}
          </div>}
        </details>
      ))}
    </div>
  );
}

/** 检索和生成期间展示固定尺寸的等待状态。 */
function LoadingMessage() {
  return (
    <article className="message-row assistant-row">
      <div className="assistant-avatar"><Bot size={17} /></div>
      <div className="loading-line"><span /><span /><span /></div>
    </article>
  );
}
