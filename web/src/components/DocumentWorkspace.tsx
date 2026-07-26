import { FileText, Trash2, Upload } from "lucide-react";
import { ChangeEvent, useEffect, useState } from "react";
import type { KnowledgeBase, KnowledgeDocument } from "../types";

type DocumentWorkspaceProps = {
  knowledgeBases: KnowledgeBase[];
  documents: KnowledgeDocument[];
  selectedKnowledgeBaseId: string;
  busy: boolean;
  onSelectKnowledgeBase: (id: string) => void;
  onUpload: (file: File) => Promise<void>;
  onDelete: (document: KnowledgeDocument) => Promise<void>;
};

/** 管理指定知识库中的原文件和向量索引状态。 */
export function DocumentWorkspace({
  knowledgeBases,
  documents,
  selectedKnowledgeBaseId,
  busy,
  onSelectKnowledgeBase,
  onUpload,
  onDelete
}: DocumentWorkspaceProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => setSelectedFile(null), [selectedKnowledgeBaseId]);

  /** 记录用户从本机选择的单个文件。 */
  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
  }

  /** 上传当前文件并在成功后清空选择。 */
  async function upload() {
    if (!selectedFile) return;
    await onUpload(selectedFile);
    setSelectedFile(null);
  }

  return (
    <section className="management-workspace">
      <header className="management-header">
        <div><h1>文档</h1><p>上传后由 Python 自动解析、切分并建立向量索引</p></div>
        <select
          className="header-select"
          value={selectedKnowledgeBaseId}
          onChange={(event) => onSelectKnowledgeBase(event.target.value)}
        >
          <option value="">选择知识库</option>
          {knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name}{item.editable ? "" : "（只读）"}</option>)}
        </select>
      </header>

      {!selectedKnowledgeBaseId ? (
        <div className="empty-state"><FileText size={28} /><strong>请先选择或创建知识库</strong></div>
      ) : (
        <div className="document-area">
          {knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId)?.editable && <div className="upload-strip">
            <label className="file-picker">
              <input type="file" accept=".pdf,.docx,.html,.htm,.md,.mdx,.rst,.txt" onChange={chooseFile} />
              <FileText size={17} />
              <span>{selectedFile?.name ?? "选择文件"}</span>
            </label>
            <button className="primary-command" onClick={() => void upload()} disabled={!selectedFile || busy}>
              <Upload size={17} />{busy ? "正在建立索引" : "上传并索引"}
            </button>
          </div>}
          <div className="resource-list document-list">
            <div className="resource-list-head"><strong>知识库文档</strong><span>{documents.length}</span></div>
            {documents.length === 0 && <div className="empty-resource"><FileText size={22} /><span>还没有上传文档</span></div>}
            {documents.map((document) => (
              <article className="resource-row" key={document.id}>
                <span className="resource-icon"><FileText size={18} /></span>
                <div className="resource-main">
                  <strong>{document.name}</strong>
                  <span>{document.chunkCount} 个文本块 · {document.imageCount} 张图片</span>
                  {document.errorMessage && <small className="row-error">{document.errorMessage}</small>}
                </div>
                <span className={`document-status status-${document.status.toLowerCase()}`}>{statusName(document.status)}</span>
                {knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId)?.editable && <button className="danger-icon" onClick={() => void onDelete(document)} title="删除文档"><Trash2 size={16} /></button>}
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

/** 把后端状态枚举转换成简短中文。 */
function statusName(status: KnowledgeDocument["status"]): string {
  return { UPLOADED: "已上传", INDEXING: "处理中", READY: "可检索", FAILED: "失败" }[status];
}
