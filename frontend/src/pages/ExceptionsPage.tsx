import React, { useState, useEffect, useCallback } from 'react';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { DataTable, type Column } from '../components/common/DataTable';
import { StatusBadge } from '../components/common/StatusBadge';
import { DetailDrawer } from '../components/common/DetailDrawer';
import { useDemo } from '../state/DemoContext';
import {
  apiClient,
  type BackendOperationalExceptionSummary,
  type BackendOperationalException,
} from '../services/apiClient';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Play,
  ArrowRight,
  RefreshCw,
  ShieldAlert,
  Sliders,
  FileText,
  UserCheck,
} from 'lucide-react';

interface DisplayExceptionItem {
  id: string;
  orderId: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  type: string;
  cause: string;
  owner: string;
  age: string;
  status: string;
  customerRef?: string;
  entityId?: string;
}

export const ExceptionsPage: React.FC = () => {
  const { dataMode, orders } = useDemo();

  const [typeFilter, setTypeFilter] = useState<string>('All');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [severityFilter, setSeverityFilter] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [liveExceptions, setLiveExceptions] = useState<BackendOperationalExceptionSummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedExceptionId, setSelectedExceptionId] = useState<string | null>(null);
  const [exceptionDetail, setExceptionDetail] = useState<BackendOperationalException | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Form states for operator action proposal
  const [proposedActionType, setProposedActionType] = useState<string>('REQUEST_FINANCE_APPROVAL');
  const [targetEntityId, setTargetEntityId] = useState<string>('');
  const [actionParametersJson, setActionParametersJson] = useState<string>('{}');
  const [actionJustification, setActionJustification] = useState<string>('');
  const [isProposingAction, setIsProposingAction] = useState<boolean>(false);

  // Approval decision state
  const [approvalJustification, setApprovalJustification] = useState<string>('Approved after operator review of supply chain constraints');
  const [isDecidingApproval, setIsDecidingApproval] = useState<boolean>(false);

  // Execution state
  const [isExecutingAction, setIsExecutingAction] = useState<boolean>(false);

  // Resume state
  const [resumeNotes, setResumeNotes] = useState<string>('Exception resolved; resuming sequential fulfillment');
  const [isResumingOrder, setIsResumingOrder] = useState<boolean>(false);

  // General action message
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchExceptions = useCallback(async () => {
    if (dataMode !== 'live') return;
    setIsLoading(true);
    setLoadError(null);
    try {
      const statusParam = statusFilter !== 'All' ? statusFilter : undefined;
      const severityParam = severityFilter !== 'All' ? severityFilter : undefined;
      const data = await apiClient.getExceptions(statusParam, severityParam);
      setLiveExceptions(data || []);
    } catch (err: any) {
      console.error('Failed to fetch exceptions:', err);
      setLoadError(err?.message || 'Failed to load operational exceptions from backend.');
    } finally {
      setIsLoading(false);
    }
  }, [dataMode, statusFilter, severityFilter]);

  useEffect(() => {
    fetchExceptions();
  }, [fetchExceptions]);

  const loadExceptionDetail = useCallback(async (id: string) => {
    setIsDetailLoading(true);
    setDetailError(null);
    setFeedbackMessage(null);
    try {
      if (dataMode === 'live') {
        const detail = await apiClient.getExceptionDetail(id);
        setExceptionDetail(detail);
        // Prepopulate form if AI recommendation is present
        if (detail.ai_recommendation?.recommended_action) {
          setProposedActionType(detail.ai_recommendation.recommended_action);
        }
        if (detail.ai_recommendation?.target_supplier_id) {
          setTargetEntityId(detail.ai_recommendation.target_supplier_id);
        }
        if (detail.ai_recommendation) {
          const { recommended_action: _rec, rationale: _rat, ...params } = detail.ai_recommendation;
          setActionParametersJson(JSON.stringify(params, null, 2));
        }
      } else {
        // Fallback demo detail
        setExceptionDetail({
          exception_id: id,
          order_id: 'ORD-1042',
          severity: 'HIGH',
          exception_type: 'BUDGET_BREACH',
          cause: 'Requisition cost ₹16.6L exceeds allocated raw-material category budget of ₹14.2L',
          owner_role: 'FINANCE',
          status: 'AWAITING_APPROVAL',
          ai_recommendation: {
            recommended_action: 'REQUEST_FINANCE_APPROVAL',
            rationale: 'High-volume requisition exceeding limit requires VP Finance sign-off.',
            risk_level: 'MEDIUM',
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
    } catch (err: any) {
      console.error('Failed to load exception detail:', err);
      setDetailError(err?.message || 'Failed to load exception details.');
    } finally {
      setIsDetailLoading(false);
    }
  }, [dataMode]);

  useEffect(() => {
    if (selectedExceptionId) {
      loadExceptionDetail(selectedExceptionId);
    } else {
      setExceptionDetail(null);
    }
  }, [selectedExceptionId, loadExceptionDetail]);

  // Handle Propose Action
  const handleProposeAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exceptionDetail) return;
    setIsProposingAction(true);
    setFeedbackMessage(null);
    try {
      let parsedParams: Record<string, any> = {};
      try {
        parsedParams = JSON.parse(actionParametersJson || '{}');
      } catch {
        throw new Error('Action parameters must be valid JSON.');
      }

      await apiClient.proposeExceptionAction(exceptionDetail.exception_id, {
        action_type: proposedActionType,
        target_entity_id: targetEntityId.trim() || undefined,
        parameters: parsedParams,
        justification: actionJustification.trim() || undefined,
      });

      setFeedbackMessage({
        type: 'success',
        text: `Action ${proposedActionType} successfully proposed and evaluated by deterministic policies.`,
      });
      await loadExceptionDetail(exceptionDetail.exception_id);
      await fetchExceptions();
    } catch (err: any) {
      setFeedbackMessage({
        type: 'error',
        text: err?.message || 'Failed to propose action.',
      });
    } finally {
      setIsProposingAction(false);
    }
  };

  // Handle Human-in-the-Loop Approval Decision
  const handleApprovalDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!exceptionDetail) return;
    if (approvalJustification.trim().length < 3) {
      setFeedbackMessage({
        type: 'error',
        text: 'Operator audit justification must be at least 3 characters.',
      });
      return;
    }
    setIsDecidingApproval(true);
    setFeedbackMessage(null);
    try {
      await apiClient.approveExceptionAction(
        exceptionDetail.exception_id,
        decision,
        approvalJustification.trim()
      );
      setFeedbackMessage({
        type: 'success',
        text: `Exception action was successfully ${decision}.`,
      });
      await loadExceptionDetail(exceptionDetail.exception_id);
      await fetchExceptions();
    } catch (err: any) {
      setFeedbackMessage({
        type: 'error',
        text: err?.message || 'Failed to submit approval decision.',
      });
    } finally {
      setIsDecidingApproval(false);
    }
  };

  // Handle Action Execution
  const handleExecuteAction = async () => {
    if (!exceptionDetail) return;
    setIsExecutingAction(true);
    setFeedbackMessage(null);
    try {
      const res = await apiClient.executeExceptionAction(exceptionDetail.exception_id);
      setFeedbackMessage({
        type: 'success',
        text: res.message || 'Action executed successfully.',
      });
      await loadExceptionDetail(exceptionDetail.exception_id);
      await fetchExceptions();
    } catch (err: any) {
      setFeedbackMessage({
        type: 'error',
        text: err?.message || 'Failed to execute exception action.',
      });
    } finally {
      setIsExecutingAction(false);
    }
  };

  // Handle Order Resumption
  const handleResumeOrder = async () => {
    if (!exceptionDetail) return;
    setIsResumingOrder(true);
    setFeedbackMessage(null);
    try {
      const res = await apiClient.resumeOrderFromException(
        exceptionDetail.exception_id,
        resumeNotes.trim() || undefined
      );
      setFeedbackMessage({
        type: 'success',
        text: res.message || 'Order returned to processing queue.',
      });
      await loadExceptionDetail(exceptionDetail.exception_id);
      await fetchExceptions();
    } catch (err: any) {
      setFeedbackMessage({
        type: 'error',
        text: err?.message || 'Failed to resume order.',
      });
    } finally {
      setIsResumingOrder(false);
    }
  };

  // Build display queue items
  const displayQueue: DisplayExceptionItem[] =
    dataMode === 'live'
      ? liveExceptions.map((ex) => {
          const sev = (['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(ex.severity?.toUpperCase())
            ? ex.severity.toUpperCase()
            : 'HIGH') as DisplayExceptionItem['severity'];

          let formattedType = ex.exception_type.replace(/_/g, ' ');
          formattedType =
            formattedType.charAt(0).toUpperCase() + formattedType.slice(1).toLowerCase();

          return {
            id: ex.exception_id,
            orderId: ex.order_id || 'N/A',
            severity: sev,
            type: formattedType,
            cause: ex.cause,
            owner: ex.owner_role || 'OPERATOR',
            age: ex.created_at ? new Date(ex.created_at).toLocaleTimeString() : 'Recent',
            status: ex.status,
            customerRef: ex.customer_ref,
            entityId: ex.entity_id,
          };
        })
      : [
          {
            id: 'EXC-2026-081',
            orderId: 'ORD-1042',
            severity: 'HIGH',
            type: 'Budget overrun',
            cause: 'Requisition cost ₹16.6L exceeds allocated raw-material category budget of ₹14.2L',
            owner: 'Finance Controller',
            age: '12m ago',
            status: 'AWAITING_APPROVAL',
            customerRef: orders[0]?.customer || 'Tata Motors',
            entityId: 'EAS-WEST',
          },
          {
            id: 'EXC-2026-080',
            orderId: 'ORD-1044',
            severity: 'CRITICAL',
            type: 'Supplier unavailable',
            cause: 'Primary Bokaro steel mill reported 15 MT slab inventory stockout',
            owner: 'Procurement Lead',
            age: '45m ago',
            status: 'AWAITING_APPROVAL',
            customerRef: 'Mahindra Auto',
            entityId: 'EAS-EAST',
          },
          {
            id: 'EXC-2026-079',
            orderId: 'ORD-1045',
            severity: 'MEDIUM',
            type: 'Delivery delay',
            cause: 'Freight corridor weather bottleneck adds 36 hours beyond promised customer SLA',
            owner: 'Logistics Supervisor',
            age: '2h ago',
            status: 'PROPOSED',
            customerRef: 'Jindal Infrastructure',
            entityId: 'EAS-NORTH',
          },
        ];

  const filteredQueue = displayQueue.filter((item) => {
    const matchesType =
      typeFilter === 'All' ||
      item.type.toLowerCase().includes(typeFilter.toLowerCase()) ||
      item.type === typeFilter;
    const matchesStatus =
      statusFilter === 'All' || item.status.toUpperCase() === statusFilter.toUpperCase();
    const matchesSeverity =
      severityFilter === 'All' || item.severity.toUpperCase() === severityFilter.toUpperCase();
    const matchesSearch =
      !searchQuery.trim() ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.orderId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.cause.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesType && matchesStatus && matchesSeverity && matchesSearch;
  });

  const columns: Column<DisplayExceptionItem>[] = [
    {
      key: 'severity',
      header: 'Severity',
      render: (item) => {
        const squareColor = {
          CRITICAL: 'bg-red-500',
          HIGH: 'bg-amber-500',
          MEDIUM: 'bg-blue-500',
          LOW: 'bg-zinc-400',
        }[item.severity];

        return (
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${squareColor}`} />
            <span className="font-semibold text-[11px] tracking-wide uppercase">
              {item.severity}
            </span>
          </div>
        );
      },
    },
    {
      key: 'type',
      header: 'Exception Type',
      render: (item) => <span className="font-medium text-text">{item.type}</span>,
    },
    {
      key: 'orderId',
      header: 'Order Ref',
      render: (item) => (
        <span className="font-mono text-[12px] text-accent font-semibold">
          {item.orderId}
        </span>
      ),
    },
    {
      key: 'cause',
      header: 'Disruption Cause',
      render: (item) => (
        <span className="text-text-2 text-[12px] max-w-sm truncate block" title={item.cause}>
          {item.cause}
        </span>
      ),
    },
    {
      key: 'owner',
      header: 'Responsible Role',
      render: (item) => (
        <span className="text-text-3 text-[11px] uppercase tracking-wider font-mono">
          {item.owner}
        </span>
      ),
    },
    {
      key: 'age',
      header: 'Reported',
      render: (item) => (
        <span className="font-mono text-[11px] text-text-3">{item.age}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} size="sm" />,
    },
    {
      key: 'action',
      header: '',
      render: (item) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setSelectedExceptionId(item.id);
          }}
          className="px-2.5 py-1 text-[11px] rounded bg-accent/10 border border-accent/20 text-accent hover:bg-accent hover:text-white transition-colors"
        >
          Resolve Case
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Operational Exceptions & Governance Gates"
        description="Unified deterministic disruption queue requiring operator diagnosis, action proposal, policy gating, human sign-off, and order resumption."
      />

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-[6px] border border-border bg-surface flex items-center justify-between">
          <div>
            <div className="text-[11px] text-text-3 uppercase tracking-wider">Total Exceptions</div>
            <div className="text-[20px] font-mono font-bold text-text mt-0.5">
              {displayQueue.length}
            </div>
          </div>
          <AlertTriangle className="w-5 h-5 text-text-3 opacity-60" />
        </div>

        <div className="p-3.5 rounded-[6px] border border-amber-500/30 bg-amber-500/5 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-amber-400 uppercase tracking-wider">Awaiting Sign-off</div>
            <div className="text-[20px] font-mono font-bold text-amber-400 mt-0.5">
              {displayQueue.filter((x) => x.status.toUpperCase() === 'AWAITING_APPROVAL').length}
            </div>
          </div>
          <ShieldAlert className="w-5 h-5 text-amber-400 opacity-80" />
        </div>

        <div className="p-3.5 rounded-[6px] border border-blue-500/30 bg-blue-500/5 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-blue-400 uppercase tracking-wider">Open / Investigating</div>
            <div className="text-[20px] font-mono font-bold text-blue-400 mt-0.5">
              {displayQueue.filter((x) => ['OPEN', 'INVESTIGATING', 'PROPOSED'].includes(x.status.toUpperCase())).length}
            </div>
          </div>
          <Sliders className="w-5 h-5 text-blue-400 opacity-80" />
        </div>

        <div className="p-3.5 rounded-[6px] border border-emerald-500/30 bg-emerald-500/5 flex items-center justify-between">
          <div>
            <div className="text-[11px] text-emerald-400 uppercase tracking-wider">Resolved</div>
            <div className="text-[20px] font-mono font-bold text-emerald-400 mt-0.5">
              {displayQueue.filter((x) => x.status.toUpperCase() === 'RESOLVED').length}
            </div>
          </div>
          <CheckCircle2 className="w-5 h-5 text-emerald-400 opacity-80" />
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-3.5 rounded-[6px] border border-border bg-surface flex flex-col md:flex-row md:items-center justify-between gap-3 text-[12px]">
        <div className="flex items-center gap-2.5 flex-wrap">
          <input
            type="text"
            placeholder="Search by ID, Order, Cause..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-[32px] px-3 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent w-48 sm:w-64"
          />

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
          >
            <option value="All">All types</option>
            <option value="BUDGET_BREACH">Budget Breach</option>
            <option value="SUPPLIER_UNAVAILABLE">Supplier Unavailable</option>
            <option value="STOCK_SHORTFALL">Stock Shortfall</option>
            <option value="DELIVERY_DELAY">Delivery Delay</option>
            <option value="POLICY_VIOLATION">Policy Violation</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
          >
            <option value="All">All statuses</option>
            <option value="OPEN">OPEN</option>
            <option value="PROPOSED">PROPOSED</option>
            <option value="AWAITING_APPROVAL">AWAITING_APPROVAL</option>
            <option value="APPROVED">APPROVED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="REJECTED">REJECTED</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="h-[32px] px-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent cursor-pointer"
          >
            <option value="All">All severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchExceptions}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] border border-border bg-surface-sunk text-text hover:bg-surface text-[12px] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {loadError && (
        <div className="p-3 rounded-[6px] border border-danger/30 bg-danger/10 text-danger text-[12px] flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{loadError}</span>
        </div>
      )}

      {/* Exception Queue Table */}
      <Panel
        title={`Operational Exceptions (${filteredQueue.length} items)`}
        subtitle="Click any row or 'Resolve Case' to open the single-operator resolution workflow."
        padding="none"
      >
        <DataTable<DisplayExceptionItem>
          columns={columns}
          data={filteredQueue}
          keyExtractor={(item) => item.id}
          onRowClick={(item) => setSelectedExceptionId(item.id)}
          emptyMessage="No operational exceptions match current filters."
        />
      </Panel>

      {/* Unified Single-Operator Resolution Drawer */}
      <DetailDrawer
        isOpen={selectedExceptionId != null}
        onClose={() => setSelectedExceptionId(null)}
        title={exceptionDetail ? `Exception Case: ${exceptionDetail.exception_id.slice(0, 13)}...` : 'Exception Case'}
        subtitle={exceptionDetail ? `Order ${exceptionDetail.order_id || 'N/A'} • ${exceptionDetail.exception_type}` : undefined}
        width="760px"
      >
        {isDetailLoading && (
          <div className="flex items-center justify-center p-12 text-text-3 text-[13px] gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-accent" />
            <span>Loading exception case file and policy evaluation...</span>
          </div>
        )}

        {detailError && (
          <div className="p-4 rounded-[6px] border border-danger/30 bg-danger/10 text-danger text-[12px] flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{detailError}</span>
          </div>
        )}

        {exceptionDetail && !isDetailLoading && (
          <div className="space-y-6 text-[12px]">
            {/* Feedback Banner */}
            {feedbackMessage && (
              <div
                className={`p-3 rounded-[6px] border flex items-center gap-2 text-[12px] ${
                  feedbackMessage.type === 'success'
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border-danger/30 bg-danger/10 text-danger'
                }`}
              >
                {feedbackMessage.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                )}
                <span>{feedbackMessage.text}</span>
              </div>
            )}

            {/* Lifecycle Step Indicator */}
            <div className="p-3 rounded-[6px] border border-border bg-surface-sunk">
              <div className="text-[11px] text-text-3 font-semibold uppercase tracking-wider mb-2">
                Resolution Lifecycle Progress
              </div>
              <div className="grid grid-cols-5 gap-1.5 text-center">
                <div className="p-1.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-[10px]">
                  1. DETECTED
                </div>
                <div
                  className={`p-1.5 rounded font-mono text-[10px] border ${
                    exceptionDetail.proposed_action || exceptionDetail.status !== 'OPEN'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : 'bg-surface border-border text-text-3'
                  }`}
                >
                  2. PROPOSED
                </div>
                <div
                  className={`p-1.5 rounded font-mono text-[10px] border ${
                    ['APPROVED', 'ACTION_EXECUTED', 'RESOLVED'].includes(exceptionDetail.status.toUpperCase())
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : exceptionDetail.status.toUpperCase() === 'AWAITING_APPROVAL'
                      ? 'bg-amber-500/20 border-amber-500/40 text-amber-400 font-bold animate-pulse'
                      : 'bg-surface border-border text-text-3'
                  }`}
                >
                  3. GOVERNED
                </div>
                <div
                  className={`p-1.5 rounded font-mono text-[10px] border ${
                    ['ACTION_EXECUTED', 'RESOLVED'].includes(exceptionDetail.status.toUpperCase())
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                      : exceptionDetail.status.toUpperCase() === 'APPROVED'
                      ? 'bg-blue-500/20 border-blue-500/40 text-blue-400 font-bold'
                      : 'bg-surface border-border text-text-3'
                  }`}
                >
                  4. EXECUTED
                </div>
                <div
                  className={`p-1.5 rounded font-mono text-[10px] border ${
                    exceptionDetail.status.toUpperCase() === 'RESOLVED'
                      ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400 font-bold'
                      : 'bg-surface border-border text-text-3'
                  }`}
                >
                  5. RESUMED
                </div>
              </div>
            </div>

            {/* Case Overview Box */}
            <div className="p-4 rounded-[6px] border border-border bg-surface space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-[14px] text-text">
                    Order {exceptionDetail.order_id || 'N/A'}
                  </span>
                  <StatusBadge status={exceptionDetail.status} size="sm" />
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-red-500/10 text-red-400 border border-red-500/30">
                    {exceptionDetail.severity}
                  </span>
                </div>
                <div className="text-[11px] text-text-3 font-mono">
                  Owner: <strong className="text-text">{exceptionDetail.owner_role}</strong>
                </div>
              </div>

              {exceptionDetail.order_details && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-1">
                  <div>
                    <span className="text-text-3 block">Customer:</span>
                    <span className="font-semibold text-text">{exceptionDetail.order_details.customer_ref || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-text-3 block">Entity:</span>
                    <span className="font-semibold text-text">{exceptionDetail.order_details.entity_id || 'N/A'}</span>
                  </div>
                  <div>
                    <span className="text-text-3 block">Order Total:</span>
                    <span className="font-semibold font-mono text-text">
                      ₹{(Number(exceptionDetail.order_details.total_amount_inr) || 0).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-3 block">Order Status:</span>
                    <span className="font-mono text-amber-400">{exceptionDetail.order_details.status}</span>
                  </div>
                </div>
              )}

              {/* Cause Statement */}
              <div className="p-3 rounded bg-red-500/5 border border-red-500/20 text-red-300">
                <div className="flex items-center gap-1.5 font-semibold text-[11px] text-red-400 mb-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Primary Policy / Constraint Violation:</span>
                </div>
                <p className="text-[12px] leading-relaxed">{exceptionDetail.cause}</p>
              </div>
            </div>

            {/* AI Recommendation Box */}
            {exceptionDetail.ai_recommendation && Object.keys(exceptionDetail.ai_recommendation).length > 0 && (
              <div className="p-4 rounded-[6px] border border-accent/30 bg-accent/5 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-accent" />
                    <span className="font-semibold text-text text-[13px]">
                      AI Disruption Analysis & Recommendation
                    </span>
                  </div>
                  {exceptionDetail.ai_recommendation.risk_level && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-accent/20 text-accent">
                      Risk: {exceptionDetail.ai_recommendation.risk_level}
                    </span>
                  )}
                </div>

                {exceptionDetail.ai_recommendation.recommended_action && (
                  <div className="text-[12px]">
                    <span className="text-text-3">Recommended Action: </span>
                    <span className="font-mono font-bold text-accent">
                      {exceptionDetail.ai_recommendation.recommended_action}
                    </span>
                  </div>
                )}

                {exceptionDetail.ai_recommendation.rationale && (
                  <p className="text-text-2 text-[12px] leading-relaxed">
                    {exceptionDetail.ai_recommendation.rationale}
                  </p>
                )}

                {exceptionDetail.ai_recommendation.estimated_cost_inr && (
                  <div className="text-[11px] font-mono text-text-3">
                    Estimated Cost:{' '}
                    <span className="text-text font-semibold">
                      ₹{Number(exceptionDetail.ai_recommendation.estimated_cost_inr).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Step 2: Propose Action Form */}
            <div className="p-4 rounded-[6px] border border-border bg-surface space-y-3">
              <div className="flex items-center gap-2 text-text font-semibold text-[13px]">
                <FileText className="w-4 h-4 text-accent" />
                <span>Operator Action Proposal & Policy Gating</span>
              </div>
              <p className="text-[11px] text-text-3">
                Select an operational mitigation action. The deterministic policy engine will immediately evaluate authority limits, supplier catalogs, and governance gates.
              </p>

              <form onSubmit={handleProposeAction} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-text-3 mb-1">Mitigation Action Type</label>
                    <select
                      value={proposedActionType}
                      onChange={(e) => setProposedActionType(e.target.value)}
                      className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[12px] focus:outline-none focus:border-accent"
                    >
                      <option value="REQUEST_FINANCE_APPROVAL">REQUEST_FINANCE_APPROVAL</option>
                      <option value="REROUTE_SUPPLIER">REROUTE_SUPPLIER</option>
                      <option value="EXPEDITE_FREIGHT">EXPEDITE_FREIGHT</option>
                      <option value="CREATE_PURCHASE_ORDER">CREATE_PURCHASE_ORDER</option>
                      <option value="ALLOCATE_INVENTORY">ALLOCATE_INVENTORY</option>
                      <option value="SPLIT_ORDER">SPLIT_ORDER</option>
                      <option value="RESOLVE_DISRUPTION">RESOLVE_DISRUPTION</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] text-text-3 mb-1">Target Entity / Supplier ID (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. SUP-002, EAS-WEST"
                      value={targetEntityId}
                      onChange={(e) => setTargetEntityId(e.target.value)}
                      className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[12px] focus:outline-none focus:border-accent"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-text-3 mb-1">Action Parameters (JSON)</label>
                  <textarea
                    rows={2}
                    value={actionParametersJson}
                    onChange={(e) => setActionParametersJson(e.target.value)}
                    className="w-full p-2 rounded-[4px] bg-surface-sunk border border-border text-text font-mono text-[11px] focus:outline-none focus:border-accent"
                  />
                </div>

                <div>
                  <label className="block text-[11px] text-text-3 mb-1">Operator Justification</label>
                  <input
                    type="text"
                    placeholder="Rationale for this mitigation approach..."
                    value={actionJustification}
                    onChange={(e) => setActionJustification(e.target.value)}
                    className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
                  />
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    type="submit"
                    disabled={isProposingAction}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] bg-accent text-white font-medium hover:bg-accent-hover transition-colors disabled:opacity-50 text-[12px]"
                  >
                    <Sliders className="w-3.5 h-3.5" />
                    <span>{isProposingAction ? 'Evaluating Policies...' : 'Propose / Update Action'}</span>
                  </button>
                </div>
              </form>

              {/* Display Current Proposed Action & Policy Details if present */}
              {exceptionDetail.action_details && (
                <div className="mt-3 p-3 rounded bg-surface-sunk border border-border text-[11px] space-y-1">
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-text-3">Active Action ID:</span>
                    <span className="text-text font-semibold">{exceptionDetail.action_details.action_id}</span>
                  </div>
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-text-3">Action Status:</span>
                    <span className="text-accent">{exceptionDetail.action_details.status}</span>
                  </div>
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-text-3">Governance Sign-off Required:</span>
                    <span className={exceptionDetail.action_details.requires_approval ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
                      {exceptionDetail.action_details.requires_approval ? 'YES (Policy Flagged)' : 'NO (Auto-Approved)'}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Step 3: Human Governance Gate (Approval / Rejection) */}
            {(exceptionDetail.status.toUpperCase() === 'AWAITING_APPROVAL' ||
              exceptionDetail.approval_details?.status === 'PENDING') && (
              <div className="p-4 rounded-[6px] border border-amber-500/40 bg-amber-500/5 space-y-3">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-[13px]">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Human-in-the-Loop Governance Gate</span>
                </div>
                <p className="text-[12px] text-text-2 leading-relaxed">
                  Deterministic policy rules have gated this action. Required approval role:
                  <strong className="text-text font-mono ml-1">
                    {exceptionDetail.approval_details?.required_domain || exceptionDetail.owner_role || 'OPERATOR'}
                  </strong>
                  .
                </p>

                <div>
                  <label className="block text-[11px] text-text-3 mb-1">
                    Operator Decision Audit Justification (Mandatory)
                  </label>
                  <textarea
                    rows={2}
                    value={approvalJustification}
                    onChange={(e) => setApprovalJustification(e.target.value)}
                    className="w-full p-2 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
                    placeholder="Explain why this policy override or action is justified..."
                  />
                </div>

                <div className="flex items-center justify-end gap-2.5 pt-1">
                  <button
                    type="button"
                    onClick={() => handleApprovalDecision('REJECTED')}
                    disabled={isDecidingApproval}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] border border-red-500/40 text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50 text-[12px]"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject Action</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleApprovalDecision('APPROVED')}
                    disabled={isDecidingApproval}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition-colors disabled:opacity-50 text-[12px]"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Approve & Authorize</span>
                  </button>
                </div>
              </div>
            )}

            {/* Step 4: Governed Execution */}
            {['APPROVED', 'ACTION_PROPOSED'].includes(exceptionDetail.status.toUpperCase()) &&
              exceptionDetail.action_id && (
                <div className="p-4 rounded-[6px] border border-blue-500/30 bg-blue-500/5 space-y-3">
                  <div className="flex items-center gap-2 text-blue-400 font-semibold text-[13px]">
                    <Play className="w-4 h-4" />
                    <span>Governed Action Execution</span>
                  </div>
                  <p className="text-[12px] text-text-2 leading-relaxed">
                    Action has met all policy checks and required authorizations. Execute to update ERP state, notify vendors, or reroute allocation.
                  </p>

                  <div className="flex justify-end pt-1">
                    <button
                      type="button"
                      onClick={handleExecuteAction}
                      disabled={isExecutingAction}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-[4px] bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors disabled:opacity-50 text-[12px]"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>{isExecutingAction ? 'Executing Action...' : 'Execute Governed Action'}</span>
                    </button>
                  </div>
                </div>
              )}

            {/* Step 5: Order Resumption to Queue */}
            {['ACTION_EXECUTED', 'APPROVED', 'RESOLVED'].includes(exceptionDetail.status.toUpperCase()) && (
              <div className="p-4 rounded-[6px] border border-emerald-500/30 bg-emerald-500/5 space-y-3">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-[13px]">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Resumption of Sequential Order Queue</span>
                </div>
                <p className="text-[12px] text-text-2 leading-relaxed">
                  Mitigation completed. Return order <strong className="text-text font-mono">{exceptionDetail.order_id}</strong> to the sequential processing queue to resume governed fulfillment.
                </p>

                {exceptionDetail.status.toUpperCase() !== 'RESOLVED' && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-[11px] text-text-3 mb-1">Resolution Summary Notes</label>
                      <input
                        type="text"
                        value={resumeNotes}
                        onChange={(e) => setResumeNotes(e.target.value)}
                        className="w-full h-[32px] px-2.5 rounded-[4px] bg-surface-sunk border border-border text-text text-[12px] focus:outline-none focus:border-accent"
                      />
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        type="button"
                        onClick={handleResumeOrder}
                        disabled={isResumingOrder}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-[4px] bg-emerald-600 hover:bg-emerald-500 text-white font-semibold transition-colors disabled:opacity-50 text-[12px]"
                      >
                        <ArrowRight className="w-3.5 h-3.5" />
                        <span>{isResumingOrder ? 'Resuming Order...' : 'Resume Order to Queue'}</span>
                      </button>
                    </div>
                  </div>
                )}

                {exceptionDetail.status.toUpperCase() === 'RESOLVED' && (
                  <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono text-[11px]">
                    ✓ Order has been successfully resumed in the processing queue. Exception resolved.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </DetailDrawer>
    </div>
  );
};
