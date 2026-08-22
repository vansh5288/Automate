const MAP = {
  COMPLETED: ["ok", "🟢", "Completed"],
  AUTO_PROCESSED: ["ok", "🟢", "Auto-Processed"],
  PENDING_APPROVAL: ["warn", "🟡", "Pending Approval"],
  APPROVED: ["ok", "🟢", "Approved"],
  PROCESSING: ["info", "🔵", "Processing"],
  RECEIVED: ["info", "🔵", "Received"],
  REJECTED: ["danger", "🔴", "Rejected"],
  FAILED: ["danger", "🔴", "Failed"],
  ACTION_FAILED: ["danger", "🔴", "Action Failed"],
  NEEDS_REVIEW: ["gray", "⚪", "Needs Review"],
};

export default function StatusBadge({ status }) {
  const [cls, dot, label] = MAP[status] || ["gray", "⚪", status];
  return <span className={`badge badge-${cls}`}>{dot} {label}</span>;
}
