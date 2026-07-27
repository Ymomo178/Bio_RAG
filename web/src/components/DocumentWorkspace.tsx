import { CheckCircle2, CircleAlert, FileText, LoaderCircle, Trash2, Upload, X } from "lucide-react";
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
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => setUploadItems([]), [selectedKnowledgeBaseId]);

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
    const candidates = uploadItems.filter((item) => item.status === "pending" || item.status === "failed");
    if (candidates.length === 0) return;
    setUploading(true);
    for (const item of candidates) {
      updateUploadItem(item.key, { status: "uploading", error: null });
      try {
        await onUpload(item.file);
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

  return (
    <section className="management-workspace">
      <header className="management-header">
        <div><h1>文档</h1><p>上传后由 Python 自动解析、切分并建立向量索引</p></div>
        <select
          className="header-select"
          value={selectedKnowledgeBaseId}
          disabled={controlsDisabled}
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
          {knowledgeBases.find((item) => item.id === selectedKnowledgeBaseId)?.editable && <div className="upload-panel">
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
                      <span>{formatFileSize(item.file.size)}{item.error ? ` · ${item.error}` : ""}</span>
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
