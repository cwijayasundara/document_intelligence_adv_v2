interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

/** Reusable page header with title, optional description, and action buttons. */
export default function PageHeader({
  title,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between px-8 py-6 border-b border-gray-200 bg-white">
      <div>
        <h1 className="text-2xl font-heading font-semibold text-gray-900">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-sm text-gray-500">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}
