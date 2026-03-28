/** Renders key topics as styled tag chips. */

interface TopicTagsProps {
  topics: string[];
}

const TAG_COLORS = [
  "bg-blue-100 text-blue-800",
  "bg-green-100 text-green-800",
  "bg-purple-100 text-purple-800",
  "bg-yellow-100 text-yellow-800",
  "bg-pink-100 text-pink-800",
  "bg-indigo-100 text-indigo-800",
];

export default function TopicTags({ topics }: TopicTagsProps) {
  if (topics.length === 0) {
    return null;
  }

  return (
    <div className="p-6 pt-0" data-testid="topic-tags">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Key Topics</h3>
      <div className="flex flex-wrap gap-2">
        {topics.map((topic, index) => (
          <span
            key={topic}
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${TAG_COLORS[index % TAG_COLORS.length]}`}
          >
            {topic}
          </span>
        ))}
      </div>
    </div>
  );
}
