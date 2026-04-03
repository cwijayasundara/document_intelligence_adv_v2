/** Document list table component. */

import type { DocumentListItem } from "../../types/document";
import DocumentRow from "./DocumentRow";

interface DocumentListProps {
  documents: DocumentListItem[];
  onReparse?: (id: string) => void;
  reparsingId?: string;
  onClassify?: (id: string) => void;
  classifyingId?: string;
  onExtract?: (id: string) => void;
  extractingId?: string;
  onSummarize?: (id: string) => void;
  summarizingId?: string;
  onIngest?: (id: string) => void;
  ingestingId?: string;
  onSelect?: (id: string) => void;
  selectedId?: string;
}

export default function DocumentList({
  documents,
  onReparse,
  reparsingId,
  onClassify,
  classifyingId,
  onExtract,
  extractingId,
  onSummarize,
  summarizingId,
  onIngest,
  ingestingId,
  onSelect,
  selectedId,
}: DocumentListProps) {
  return (
    <div className="overflow-hidden shadow ring-1 ring-black/5 rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              File Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Confidence
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Category
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Size
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Created
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {documents.map((doc) => (
            <DocumentRow
              key={doc.id}
              document={doc}
              onReparse={onReparse}
              isReparsing={reparsingId === doc.id}
              onClassify={onClassify}
              isClassifying={classifyingId === doc.id}
              onExtract={onExtract}
              isExtracting={extractingId === doc.id}
              onSummarize={onSummarize}
              isSummarizing={summarizingId === doc.id}
              onIngest={onIngest}
              isIngesting={ingestingId === doc.id}
              onSelect={onSelect}
              isSelected={selectedId === doc.id}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
