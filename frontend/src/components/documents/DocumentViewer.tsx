/** PDF viewer that overlays Reducto citation bounding boxes on each page. */

import { useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import type { ExtractionCitation, ExtractionResult } from "../../types/extraction";
import { documentFileUrl } from "../../lib/api/documents";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

interface DocumentViewerProps {
  documentId: string;
  results: ExtractionResult[];
  activeFieldId: string | null;
  onSelectField?: (fieldId: string | null) => void;
  className?: string;
}

interface CitationBox {
  fieldId: string;
  fieldName: string;
  page: number;
  citation: ExtractionCitation;
  isActive: boolean;
}

function buildBoxes(
  results: ExtractionResult[],
  activeFieldId: string | null,
): CitationBox[] {
  const boxes: CitationBox[] = [];
  for (const result of results) {
    for (const c of result.citations ?? []) {
      if (c.width <= 0 || c.height <= 0) continue;
      boxes.push({
        fieldId: result.id,
        fieldName: result.displayName,
        page: c.page,
        citation: c,
        isActive: result.id === activeFieldId,
      });
    }
  }
  return boxes;
}

export default function DocumentViewer({
  documentId,
  results,
  activeFieldId,
  onSelectField,
  className,
}: DocumentViewerProps) {
  // react-pdf fetches the URL directly (no axios), so we have to pass the
  // auth header alongside the URL — the backend's get_current_user_id
  // dependency requires X-User-Id and would otherwise 401 the file request.
  const fileSource = useMemo(
    () => ({
      url: documentFileUrl(documentId),
      httpHeaders: { "X-User-Id": "default-user" },
    }),
    [documentId],
  );
  const [numPages, setNumPages] = useState<number>(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  const allBoxes = useMemo(
    () => buildBoxes(results, activeFieldId),
    [results, activeFieldId],
  );

  // Scroll the active field's first citation into view.
  useEffect(() => {
    if (!activeFieldId) return;
    const target = allBoxes.find((b) => b.fieldId === activeFieldId);
    if (!target) return;
    const pageEl = pageRefs.current.get(target.page);
    if (pageEl) {
      pageEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [activeFieldId, allBoxes]);

  if (loadError) {
    return (
      <div className={`p-6 text-sm text-red-700 bg-red-50 rounded ${className ?? ""}`}>
        Could not load document: {loadError}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`bg-gray-100 overflow-y-auto ${className ?? ""}`}
      data-testid="document-viewer"
    >
      <Document
        file={fileSource}
        onLoadSuccess={({ numPages: n }) => setNumPages(n)}
        onLoadError={(err) => setLoadError(err.message)}
        loading={
          <div className="p-6 text-sm text-gray-500">Loading document...</div>
        }
      >
        {Array.from({ length: numPages }, (_, idx) => idx + 1).map((pageNum) => {
          const pageBoxes = allBoxes.filter((b) => b.page === pageNum);
          return (
            <PageWithOverlay
              key={pageNum}
              pageNum={pageNum}
              boxes={pageBoxes}
              onPageRef={(el) => {
                if (el) pageRefs.current.set(pageNum, el);
                else pageRefs.current.delete(pageNum);
              }}
              onBoxClick={(box) => onSelectField?.(box.fieldId)}
            />
          );
        })}
      </Document>
    </div>
  );
}

interface PageWithOverlayProps {
  pageNum: number;
  boxes: CitationBox[];
  onPageRef: (el: HTMLDivElement | null) => void;
  onBoxClick: (box: CitationBox) => void;
}

function PageWithOverlay({
  pageNum,
  boxes,
  onPageRef,
  onBoxClick,
}: PageWithOverlayProps) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(
    null,
  );

  return (
    <div ref={onPageRef} className="relative mx-auto my-4 shadow-md w-fit">
      <Page
        pageNumber={pageNum}
        width={800}
        renderAnnotationLayer={false}
        renderTextLayer={false}
        onRenderSuccess={(page) =>
          setSize({ width: page.width, height: page.height })
        }
      />
      {size &&
        boxes.map((b, i) => (
          <button
            key={`${b.fieldId}-${i}`}
            type="button"
            onClick={() => onBoxClick(b)}
            title={`${b.fieldName}: ${b.citation.content ?? ""}`}
            className={`absolute border-2 transition-all duration-150 cursor-pointer ${
              b.isActive
                ? "border-amber-500 bg-amber-300/40 ring-2 ring-amber-400"
                : "border-blue-400/70 bg-blue-300/15 hover:bg-blue-300/30"
            }`}
            style={{
              left: `${b.citation.left * size.width}px`,
              top: `${b.citation.top * size.height}px`,
              width: `${b.citation.width * size.width}px`,
              height: `${b.citation.height * size.height}px`,
            }}
            data-testid={`citation-box-${b.fieldId}`}
          />
        ))}
    </div>
  );
}
