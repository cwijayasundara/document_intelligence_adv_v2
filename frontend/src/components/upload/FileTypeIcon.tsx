/** File type icon component for upload display. */

const typeIcons: Record<string, string> = {
  pdf: "PDF",
  docx: "DOC",
  xlsx: "XLS",
  png: "PNG",
  jpg: "JPG",
  tiff: "TIF",
};

const typeColors: Record<string, string> = {
  pdf: "bg-red-100 text-red-700",
  docx: "bg-blue-100 text-blue-700",
  xlsx: "bg-green-100 text-green-700",
  png: "bg-purple-100 text-purple-700",
  jpg: "bg-purple-100 text-purple-700",
  tiff: "bg-purple-100 text-purple-700",
};

interface FileTypeIconProps {
  fileName: string;
}

export default function FileTypeIcon({ fileName }: FileTypeIconProps) {
  const ext = fileName.split(".").pop()?.toLowerCase() ?? "";
  const label = typeIcons[ext] ?? "FILE";
  const colorClass = typeColors[ext] ?? "bg-gray-100 text-gray-700";

  return (
    <span
      className={`inline-flex items-center justify-center w-10 h-10 rounded-lg text-xs font-bold ${colorClass}`}
    >
      {label}
    </span>
  );
}
