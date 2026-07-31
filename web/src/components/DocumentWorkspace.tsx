import { CheckCircle2, CircleAlert, Database, FileText, LoaderCircle, Lock, Trash2, Upload, X } from "lucide-react";
import { ChangeEvent, useEffect, useState } from "react";
import type { KnowledgeBase, KnowledgeDocument } from "../types";

type UploadStatus = "pending" | "uploading" | "success" | "failed";

type UploadItem = {
  key: string;
  file: File;
  status: UploadStatus;
  error: string | null;
};

type DocumentWorkspaceProps = {
  knowledgeBases: KnowledgeBase[];
  documents: KnowledgeDocument[];
  selectedKnowledgeBaseId: string;
  busy: boolean;
  onSelectKnowledgeBase: (id: string) => void;
  onUpload: (knowledgeBaseId: string, file: File) => Promise<void>;
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
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => setUploadItems([]), [selectedKnowledgeBaseId]);

  /** 切换目标知识库前确认未上传队列，避免文件被误传到另一处。 */
  function selectKnowledgeBase(nextId: string) {
    if (nextId === selectedKnowledgeBaseId) return;
    const hasUnfinishedFiles = uploadItems.some((item) => item.status !== "success");
    if (hasUnfinishedFiles && !window.confirm("切换知识库会清空当前上传列表，是否继续？")) return;
    setUploadItems([]);
    onSelectKnowledgeBase(nextId);
  }

  /** 读取用户一次选择的多个文件，并过滤同一批次中的重复项。 */
  function chooseFiles(event: ChangeEvent<HTMLInputElement>) {
    const uniqueFiles = Array.from(event.target.files ?? []).filter((file, index, files) =>
      files.findIndex((candidate) => fileKey(candidate) === fileKey(file)) === index
    );
    setUploadItems(uniqueFiles.map((file) => ({
      key: fileKey(file),
      file,
      status: "pending",
      error: null
    })));
    event.target.value = "";
  }

  /** 依次上传等待中或失败的文件，保证单个失败不会中断整批任务。 */
  async function uploadAll() {
    if (!selectedKnowledgeBaseId) return;
    const candidates = uploadItems.filter((item) => item.status === "pending" || item.status === "failed");
    if (candidates.length === 0) return;
    setUploading(true);
    for (const item of candidates) {
      updateUploadItem(item.key, { status: "uploading", error: null });
      try {
        await onUpload(selectedKnowledgeBaseId, item.file);
        updateUploadItem(item.key, { status: "success", error: null });
      } catch (cause) {
        updateUploadItem(item.key, {
          status: "failed",
          error: cause instanceof Error ? cause.message : "上传失败"
        });
      }
    }
    setUploading(false);
  }

  /** 更新上传队列中一个文件的状态。 */
  function updateUploadItem(key: string, update: Pick<UploadItem, "status" | "error">) {
    setUploadItems((current) => current.map((item) => item.key === key ? { ...item, ...update } : item));
  }

  /** 从尚未开始的上传队列中移除一个文件。 */
  function removeUploadItem(key: string) {
    setUploadItems((current) => current.filter((item) => item.key !== key));
  }

  const pendingCount = uploadItems.filter((item) => item.status === "pending").length;
  const successCount = uploadItems.filter((item) => item.status === "success").length;
  const failedCount = uploadItems.filter((item) => item.status === "failed").length;
  const actionableCount = pendingCount + failedCount;
  const controlsDisabled = busy || uploading;
  const selectedKnowledgeBase = knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId);

  return (
    <section className="management-workspace">
      <header className="management-header">
        <div><h1>文档</h1><p>先选择目标知识库，再上传并建立索引</p></div>
      </header>

      <div className="document-area">
        <section className="document-target" aria-labelledby="document-target-title">
          <div className="document-target-heading">
            <span className="document-target-icon"><Database size={18} /></span>
            <div>
              <strong id="document-target-title">目标知识库</strong>
              <span>文件、文本块和图片都将归入所选知识库</span>
            </div>
          </div>
          <label className="document-target-select">
            <span>上传到</span>
            <select
              value={selectedKnowledgeBaseId}
              disabled={controlsDisabled}
              onChange={(event) => selectKnowledgeBase(event.target.value)}
            >
              <option value="">请选择知识库</option>
              {knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name}{item.editable ? "" : "（只读）"}</option>)}
            </select>
          </label>
        </section>

        {!selectedKnowledgeBase ? (
          <div className="document-empty-selection"><FileText size={28} /><strong>请选择文档要上传到哪个知识库</strong><span>没有知识库时，请先到“知识库”页面创建一个。</span></div>
        ) : !selectedKnowledgeBase.editable ? (
          <>
            <div className="document-readonly-notice"><Lock size={16} /><span>“{selectedKnowledgeBase.name}”是只读知识库，你可以查看其中的文档，但不能上传。</span></div>
            <DocumentList knowledgeBase={selectedKnowledgeBase} documents={documents} onDelete={onDelete} />
          </>
        ) : (
          <>
            <div className="upload-panel">
              <div className="upload-destination">
                <Database size={15} />
                <span>本批文件将上传到</span>
                <strong title={selectedKnowledgeBase.name}>{selectedKnowledgeBase.name}</strong>
              </div>
            <div className="upload-strip">
              <label className={`file-picker ${controlsDisabled ? "disabled" : ""}`}>
                <input
                  type="file"
                  multiple
                  disabled={controlsDisabled}
                  accept=".pdf,.docx,.html,.htm,.md,.mdx,.rst,.txt"
                  onChange={chooseFiles}
                />
                <FileText size={17} />
                <span>{uploadItems.length > 0 ? `已选择 ${uploadItems.length} 个文件` : "选择一个或多个文件"}</span>
              </label>
              {uploadItems.length > 0 && !uploading && (
                <button className="secondary-command" onClick={() => setUploadItems([])} title="清空上传列表">
                  <X size={15} />清空
                </button>
              )}
              <button className="primary-command" onClick={() => void uploadAll()} disabled={actionableCount === 0 || controlsDisabled}>
                {uploading ? <LoaderCircle className="spin" size={17} /> : <Upload size={17} />}
                {uploading ? "正在逐个建立索引" : failedCount > 0 && pendingCount === 0 ? `重试失败项 (${failedCount})` : `上传并索引 (${actionableCount})`}
              </button>
            </div>
            {uploadItems.length > 0 && (
              <div className="upload-queue" aria-live="polite">
                <div className="upload-queue-head">
                  <strong>上传列表</strong>
                  <span>{successCount > 0 && `成功 ${successCount}`}{successCount > 0 && failedCount > 0 && " · "}{failedCount > 0 && `失败 ${failedCount}`}</span>
                </div>
                {uploadItems.map((item) => (
                  <div className="upload-queue-row" key={item.key}>
                    <span className="upload-file-icon"><FileText size={16} /></span>
                    <div className="upload-file-main">
                      <strong title={item.file.name}>{item.file.name}</strong>
                      <span>{formatFileSize(item.file.size)} · 目标：{selectedKnowledgeBase.name}{item.error ? ` · ${item.error}` : ""}</span>
                    </div>
                    <UploadState status={item.status} />
                    <button
                      className="upload-remove"
                      disabled={controlsDisabled || item.status === "success"}
                      onClick={() => removeUploadItem(item.key)}
                      title="从上传列表移除"
                      aria-label={`移除 ${item.file.name}`}
                    >
                      <X size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            </div>
            <DocumentList knowledgeBase={selectedKnowledgeBase} documents={documents} onDelete={onDelete} />
          </>
        )}
      </div>
    </section>
  );
}

/** 展示当前所选知识库中的文档，标题始终标明文档归属。 */
function DocumentList({
  knowledgeBase,
  documents,
  onDelete
}: {
  knowledgeBase: KnowledgeBase;
  documents: KnowledgeDocument[];
  onDelete: (document: KnowledgeDocument) => Promise<void>;
}) {
  return (
    <div className="resource-list document-list">
      <div className="resource-list-head document-list-head">
        <strong title={knowledgeBase.name}>{knowledgeBase.name} · 文档</strong>
        <span>{documents.length}</span>
      </div>
      {documents.length === 0 && <div className="empty-resource"><FileText size={22} /><span>这个知识库还没有文档</span></div>}
      {documents.map((document) => (
        <article className="resource-row" key={document.id}>
          <span className="resource-icon"><FileText size={18} /></span>
          <div className="resource-main">
            <strong>{document.name}</strong>
            <span>所属：{knowledgeBase.name} · {document.chunkCount} 个文本块 · {document.imageCount} 张图片</span>
            {document.errorMessage && <small className="row-error">{document.errorMessage}</small>}
          </div>
          <span className={`document-status status-${document.status.toLowerCase()}`}>{statusName(document.status)}</span>
          {knowledgeBase.editable && <button className="danger-icon" onClick={() => void onDelete(document)} title="删除文档"><Trash2 size={16} /></button>}
        </article>
      ))}
    </div>
  );
}

/** 展示上传队列中单个文件的当前状态。 */
function UploadState({ status }: { status: UploadStatus }) {
  if (status === "uploading") return <span className="upload-state state-uploading"><LoaderCircle className="spin" size={14} />处理中</span>;
  if (status === "success") return <span className="upload-state state-success"><CheckCircle2 size={14} />成功</span>;
  if (status === "failed") return <span className="upload-state state-failed"><CircleAlert size={14} />失败</span>;
  return <span className="upload-state state-pending">等待</span>;
}

/** 生成用于当前选择列表去重的稳定文件标识。 */
function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

/** 把字节数转换为便于扫描的文件大小。 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** 把后端状态枚举转换成简短中文。 */
function statusName(status: KnowledgeDocument["status"]): string {
  return { UPLOADED: "已上传", INDEXING: "处理中", READY: "可检索", FAILED: "失败" }[status];
}
