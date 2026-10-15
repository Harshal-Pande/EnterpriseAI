import { SourceBadge } from '../common/SourceBadge';
import { StatusBadge } from '../common/StatusBadge';

interface CaseHeaderProps {
  orderId: string;
  customer: string;
  scenario?: string;
  priority?: string;
  status: string;
  outcomeText?: string;
  startedAt?: string;
  durationMs?: number;
  isSimulated?: boolean;
  className?: string;
}

export const CaseHeader: React.FC<CaseHeaderProps> = ({
  orderId,
  customer,
  scenario = 'Normal order fulfillment',
  priority = 'Medium',
  status,
  outcomeText,
  startedAt = 'Today, 19:15',
  durationMs = 420,
  isSimulated = false,
  className = '',
}) => {
  // Format default outcome if not provided
  const derivedOutcome =
    outcomeText ||
    (status === 'Approved' || status === 'Completed'
      ? 'Allowed: inventory reserved, supplier quote accepted, within budget limits.'
      : status === 'Exception' || status === 'Delayed'
      ? 'Awaiting approval: policy check flagged constraint exception requiring operator review.'
      : 'In progress: multi-agent mesh evaluating supply chain feasibility.');

  return (
    <div
      className={`rounded-[6px] border border-border bg-surface p-4 text-text space-y-3 ${className}`}
    >
      {/* Top row: Order ID, customer, badges */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-mono text-[20px] font-semibold text-text tracking-tight">
            {orderId}
          </span>
          <span className="text-[14px] text-text-2 font-medium">
            {customer}
          </span>
          <span className="px-2 py-0.5 rounded-[4px] border border-border bg-surface-sunk text-text-3 font-mono text-[11px]">
            Priority: {priority}
          </span>
          <span className="px-2 py-0.5 rounded-[4px] border border-border bg-surface-sunk text-text-3 text-[11px]">
            Scenario: {scenario}
          </span>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <SourceBadge forcedState={isSimulated ? 'simulated' : undefined} />
          <StatusBadge status={status} />
        </div>
      </div>

      {/* Outcome sentence */}
      <div className="p-2.5 rounded-[4px] bg-surface-2 border border-border text-[13px] text-text-2 leading-normal">
        <strong className="text-text font-medium mr-1.5">Outcome:</strong>
        <span>{derivedOutcome}</span>
      </div>

      {/* Metadata strip */}
      <div className="flex items-center gap-6 text-[12px] text-text-3 pt-0.5 border-t border-border">
        <div>
          <span>Started: </span>
          <span className="font-mono text-text-2">{startedAt}</span>
        </div>
        <div>
          <span>Duration: </span>
          <span className="font-mono text-text-2">{durationMs}ms</span>
        </div>
        <div>
          <span>Investigation: </span>
          <span className="text-text-2">5 Specialists</span>
        </div>
      </div>
    </div>
  );
};
