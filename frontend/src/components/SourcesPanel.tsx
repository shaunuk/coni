interface Source {
  source_name: string;
  raw_response: string;
  confidence: number | null;
  source_url: string | null;
}

export default function SourcesPanel({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-3">Sources ({sources.length})</h3>
      <div className="space-y-3">
        {sources.map((source, i) => (
          <div key={i} className="border-l-2 border-gray-200 pl-3">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{source.source_name}</span>
              {source.confidence !== null && (
                <span className="text-xs text-gray-500">
                  {Math.round(source.confidence * 100)}% confidence
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 mt-1 line-clamp-3">
              {source.raw_response}
            </p>
            {source.source_url && (
              <a
                href={source.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline"
              >
                View source
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
