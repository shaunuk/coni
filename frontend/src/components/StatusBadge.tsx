const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  preliminary: { label: "Preliminary", color: "bg-yellow-100 text-yellow-800" },
  debating: { label: "Debating", color: "bg-blue-100 text-blue-800" },
  consensus_reached: { label: "Consensus Reached", color: "bg-green-100 text-green-800" },
  sealed: { label: "Sealed", color: "bg-purple-100 text-purple-800" },
  contested: { label: "Contested", color: "bg-red-100 text-red-800" },
};

export default function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || { label: status, color: "bg-gray-100 text-gray-800" };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}
