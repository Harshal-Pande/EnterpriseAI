import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowRight,
  RefreshCw,
  AlertTriangle,
  Database,
  Layers,
  Network,
  Activity,
  ShieldCheck,
} from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import { apiClient } from '../services/apiClient';
import type {
  BackendGraphStatus,
  BackendDisruptionImpactResponse,
  BackendGraphResponse,
} from '../services/apiClient';
import type { GraphNode, GraphEdge } from '../types';

/* ─────────────────────────────────────────────────
   Node visual config per entity type
───────────────────────────────────────────────── */
const NODE_STYLE: Record<string, {
  color: string;
  border: string;
  bg: string;
  activeBg: string;
  typeLabel: string;
}> = {
  Customer:  { color: '#38BDF8', border: '#1D4ED8',             bg: 'rgba(56,189,248,0.07)',  activeBg: 'rgba(56,189,248,0.15)',  typeLabel: 'CUSTOMER'  },
  Order:     { color: '#F8FAFC', border: 'rgba(248,250,252,0.4)',bg: 'rgba(248,250,252,0.05)', activeBg: 'rgba(248,250,252,0.12)', typeLabel: 'ORDER'     },
  Product:   { color: '#34D399', border: '#065F46',             bg: 'rgba(52,211,153,0.07)',  activeBg: 'rgba(52,211,153,0.15)',  typeLabel: 'PRODUCT'   },
  Supplier:  { color: '#FCD34D', border: '#92400E',             bg: 'rgba(252,211,77,0.07)',  activeBg: 'rgba(252,211,77,0.15)',  typeLabel: 'SUPPLIER'  },
  Warehouse: { color: '#C084FC', border: '#4C1D95',             bg: 'rgba(192,132,252,0.07)', activeBg: 'rgba(192,132,252,0.15)', typeLabel: 'WAREHOUSE' },
  InventoryItem: { color: '#FB923C', border: '#9A3412',         bg: 'rgba(251,146,60,0.07)',  activeBg: 'rgba(251,146,60,0.15)',  typeLabel: 'INVENTORY' },
};

const DEFAULT_STYLE = {
  color: '#94A3B8',
  border: '#334155',
  bg: 'rgba(148,163,184,0.07)',
  activeBg: 'rgba(148,163,184,0.15)',
  typeLabel: 'ENTITY',
};

/* ─────────────────────────────────────────────────
   Structured layout positions
   Canvas is 740 × 480 (SVG viewBox)
───────────────────────────────────────────────── */
const BASE_CENTERS: Record<string, { cx: number; cy: number }> = {
  'cust-1':    { cx: 370, cy: 55  },  // top center
  'ord-1042':  { cx: 370, cy: 190 },  // center
  'prod-800':  { cx: 185, cy: 335 },  // bottom left
  'wh-nagpur': { cx: 370, cy: 395 },  // bottom center
  'sup-b':     { cx: 555, cy: 335 },  // bottom right
};

const NODE_W2 = 80;
const NODE_H2 = 38;

function midpoint(a: { cx: number; cy: number }, b: { cx: number; cy: number }) {
  return { x: (a.cx + b.cx) / 2, y: (a.cy + b.cy) / 2 };
}

function clampToBox(
  fromCenter: { cx: number; cy: number },
  toCenter:   { cx: number; cy: number }
): { x: number; y: number } {
  const dx = toCenter.cx - fromCenter.cx;
  const dy = toCenter.cy - fromCenter.cy;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const nx = dx / len;
  const ny = dy / len;
  const tMaxX = NODE_W2 / Math.abs(nx || 0.001);
  const tMaxY = NODE_H2 / Math.abs(ny || 0.001);
  const t = Math.min(tMaxX, tMaxY);
  return { x: toCenter.cx - nx * t, y: toCenter.cy - ny * t };
}

/* ─────────────────────────────────────────────────
   Node Card component
───────────────────────────────────────────────── */
interface NodeCardProps {
  node: GraphNode;
  pos: { cx: number; cy: number };
  isSelected: boolean;
  isDimmed: boolean;
  isAffected: boolean;
  onClick: () => void;
}

const NodeCard: React.FC<NodeCardProps> = ({
  node,
  pos,
  isSelected,
  isDimmed,
  isAffected,
  onClick,
}) => {
  const s = NODE_STYLE[node.type] || DEFAULT_STYLE;
  const isOrder = node.type === 'Order';
  const w = isOrder ? 176 : 160;
  const h = isOrder ? 86 : 76;

  return (
    <foreignObject
      x={pos.cx - w / 2}
      y={pos.cy - h / 2}
      width={w}
      height={h}
      style={{ overflow: 'visible' }}
    >
      <div
        onClick={onClick}
        title={`${node.type}: ${node.label}`}
        style={{
          width: `${w}px`,
          height: `${h}px`,
          background: isAffected
            ? 'rgba(239,68,68,0.15)'
            : isSelected
            ? s.activeBg
            : s.bg,
          border: `${isSelected ? '2px' : '1px'} solid ${
            isAffected
              ? '#EF4444'
              : isSelected
              ? s.color
              : isDimmed
              ? '#1E293B'
              : s.border
          }`,
          borderRadius: '10px',
          padding: '8px 12px',
          cursor: 'pointer',
          opacity: isDimmed ? 0.35 : 1,
          boxShadow: isAffected
            ? '0 0 18px rgba(239,68,68,0.35)'
            : isSelected
            ? `0 0 16px ${s.color}25`
            : 'none',
          transition: 'all 0.15s ease',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: '2px',
          userSelect: 'none',
        }}
      >
        <div className="flex items-center justify-between">
          <div
            style={{
              fontSize: '9px',
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 700,
              color: isAffected ? '#EF4444' : s.color,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
            }}
          >
            {s.typeLabel}
          </div>
          {isAffected && (
            <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
          )}
        </div>
        <div
          style={{
            fontSize: isOrder ? '13px' : '12px',
            fontWeight: 700,
            color: '#F1F5F9',
            lineHeight: '1.2',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {node.label}
        </div>
        {node.status && (
          <div
            style={{
              fontSize: '9px',
              fontFamily: 'JetBrains Mono, monospace',
              color: isAffected ? '#F87171' : s.color,
              marginTop: '1px',
            }}
          >
            ● {node.status}
          </div>
        )}
        {!node.status && (
          <div
            style={{
              fontSize: '9px',
              color: '#475569',
              fontFamily: 'JetBrains Mono, monospace',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {Object.entries(node.details || {})
              .map(([k, v]) => `${k}: ${v}`)
              .slice(0, 1)
              .join(' · ')}
          </div>
        )}
      </div>
    </foreignObject>
  );
};

/* ─────────────────────────────────────────────────
   Main Page
───────────────────────────────────────────────── */
export const KnowledgeGraphPage: React.FC = () => {
  const {
    graphNodes: demoNodes,
    graphEdges: demoEdges,
    selectedGraphNodeId,
    setSelectedGraphNodeId,
  } = useDemo();

  const [graphStatus, setGraphStatus] = useState<BackendGraphStatus | null>(null);
  const [liveNodes, setLiveNodes] = useState<GraphNode[]>(demoNodes);
  const [liveEdges, setLiveEdges] = useState<GraphEdge[]>(demoEdges);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<string | null>(null);

  const [queryText, setQueryText] = useState('');
  const [activeTab, setActiveTab] = useState<'inspector' | 'impact' | 'provenance'>('inspector');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');

  // Disruption Impact Simulator state
  const [impactOrigin, setImpactOrigin] = useState<string>('sup-b');
  const [impactSeverity, setImpactSeverity] = useState<string>('HIGH');
  const [impactResult, setImpactResult] = useState<BackendDisruptionImpactResponse | null>(null);
  const [isAnalyzingImpact, setIsAnalyzingImpact] = useState<boolean>(false);

  // Provenance inspection state
  const [provenanceResponse, setProvenanceResponse] = useState<BackendGraphResponse | null>(null);
  const [isLoadingProvenance, setIsLoadingProvenance] = useState<boolean>(false);

  // Load Graph Status & Live Nodes on mount
  useEffect(() => {
    let isMounted = true;
    apiClient
      .getGraphStatus()
      .then((status) => {
        if (isMounted) setGraphStatus(status);
      })
      .catch((err) => {
        console.warn('Backend graph status check failed:', err);
      });

    apiClient
      .getKnowledgeGraph(undefined, undefined, 150)
      .then((res) => {
        if (!isMounted || !res.nodes || res.nodes.length === 0) return;
        const convertedNodes: GraphNode[] = res.nodes.map((n) => ({
          id: n.id,
          label: n.label,
          type: (n.type as any) || 'Product',
          status: n.status || 'Active',
          details: n.properties || {},
          x: 0,
          y: 0,
        }));
        const convertedEdges: GraphEdge[] = res.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || e.type,
        }));
        setLiveNodes(convertedNodes);
        setLiveEdges(convertedEdges);
      })
      .catch((err) => {
        console.warn('Fallback to context demo graph nodes:', err);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSyncGraph = async () => {
    try {
      setIsSyncing(true);
      setSyncFeedback(null);
      const res = await apiClient.syncKnowledgeGraph();
      setSyncFeedback(`Synced ${res.synced_nodes} nodes & ${res.synced_edges} edges in ${res.duration_ms.toFixed(1)}ms`);
      const updatedStatus = await apiClient.getGraphStatus();
      setGraphStatus(updatedStatus);
    } catch (err: any) {
      setSyncFeedback(`Sync error: ${err.message || 'Failed to sync'}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleRunImpactAnalysis = async () => {
    try {
      setIsAnalyzingImpact(true);
      const res = await apiClient.analyzeDisruptionImpact({
        entity_type: 'Supplier',
        entity_id: impactOrigin,
        severity: impactSeverity,
        simulate_alternatives: true,
      });
      setImpactResult(res);
      setActiveTab('impact');
    } catch (err: any) {
      console.error('Impact analysis error:', err);
    } finally {
      setIsAnalyzingImpact(false);
    }
  };

  const handleFetchProvenance = async (entityId: string) => {
    try {
      setIsLoadingProvenance(true);
      setActiveTab('provenance');
      const res = await apiClient.getEntityProvenance(entityId, 2);
      setProvenanceResponse(res);
    } catch (err: any) {
      console.error('Provenance fetch error:', err);
    } finally {
      setIsLoadingProvenance(false);
    }
  };

  // Node position map with dynamic placement for novel nodes
  const nodeCenters = useMemo(() => {
    const centers: Record<string, { cx: number; cy: number }> = { ...BASE_CENTERS };
    let dynamicIdx = 0;
    liveNodes.forEach((node) => {
      if (!centers[node.id]) {
        // Place around canvas perimeter dynamically
        const angle = (dynamicIdx * (2 * Math.PI)) / 10;
        centers[node.id] = {
          cx: Math.round(370 + 260 * Math.cos(angle)),
          cy: Math.round(230 + 160 * Math.sin(angle)),
        };
        dynamicIdx++;
      }
    });
    return centers;
  }, [liveNodes]);

  // Selected node
  const selectedNode =
    liveNodes.find((n) => n.id === selectedGraphNodeId) ??
    liveNodes[0] ?? {
      id: 'ord-1042',
      label: 'Order #1042',
      type: 'Order',
      status: 'Delayed',
      details: {},
      x: 0,
      y: 0,
    };

  const selectedStyle = NODE_STYLE[selectedNode.type] || DEFAULT_STYLE;

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    return liveNodes.filter((node) => {
      const matchesType = typeFilter === 'ALL' || node.type === typeFilter;
      const matchesQuery =
        !queryText ||
        node.label.toLowerCase().includes(queryText.toLowerCase()) ||
        node.id.toLowerCase().includes(queryText.toLowerCase()) ||
        node.type.toLowerCase().includes(queryText.toLowerCase());
      return matchesType && matchesQuery;
    });
  }, [liveNodes, typeFilter, queryText]);

  // Affected node IDs from active disruption simulation
  const affectedNodeIds = useMemo(() => {
    if (!impactResult) return new Set<string>();
    const ids = new Set<string>();
    ids.add(impactResult.disruption_origin);
    impactResult.affected_order_ids.forEach((id) => ids.add(id));
    impactResult.affected_product_ids.forEach((id) => ids.add(id));
    impactResult.affected_warehouse_ids.forEach((id) => ids.add(id));
    return ids;
  }, [impactResult]);

  // Connected nodes to selection
  const relatedNodeIds = useMemo(() => {
    const set = new Set<string>();
    if (selectedGraphNodeId) {
      liveEdges.forEach((e) => {
        if (e.source === selectedGraphNodeId) set.add(e.target);
        if (e.target === selectedGraphNodeId) set.add(e.source);
      });
      set.add(selectedGraphNodeId);
    }
    return set;
  }, [liveEdges, selectedGraphNodeId]);

  const hasSelection = selectedGraphNodeId != null;

  // Highlighted edges
  const highlightedEdgeIds = useMemo(() => {
    return new Set(
      liveEdges
        .filter(
          (e) =>
            e.source === selectedGraphNodeId || e.target === selectedGraphNodeId
        )
        .map((e) => e.id)
    );
  }, [liveEdges, selectedGraphNodeId]);

  const SVG_W = 740;
  const SVG_H = 480;

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Knowledge Graph & Impact Ontology
            </h1>
            <span
              className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5"
              style={{
                background: graphStatus?.connected
                  ? 'rgba(16,185,129,0.1)'
                  : 'rgba(99,102,241,0.1)',
                border: `1px solid ${
                  graphStatus?.connected
                    ? 'rgba(16,185,129,0.3)'
                    : 'rgba(99,102,241,0.3)'
                }`,
                color: graphStatus?.connected ? '#34D399' : '#818CF8',
              }}
            >
              <Database className="w-3 h-3" />
              {graphStatus?.engine
                ? graphStatus.engine.toUpperCase()
                : 'RELATIONAL HYBRID'}
              {graphStatus?.connected ? ' (LIVE)' : ' (ACTIVE)'}
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Enterprise relationship mesh: Multi-hop disruption traversal, entity provenance, and AI dependency grounding
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSyncGraph}
            disabled={isSyncing}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[11px] font-medium transition cursor-pointer"
            style={{
              background: '#0F172A',
              border: '1px solid #1E293B',
              color: '#94A3B8',
            }}
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-cyan-400 ${
                isSyncing ? 'animate-spin' : ''
              }`}
            />
            {isSyncing ? 'Syncing...' : 'Sync Graph'}
          </button>

          <div className="relative">
            <input
              type="text"
              id="graph-query"
              placeholder="Query entities, IDs..."
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              className="h-9 pl-3 pr-4 w-52 text-[12px] text-slate-200 placeholder-slate-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              style={{ background: '#0F172A', border: '1px solid #1E293B' }}
            />
          </div>
        </div>
      </div>

      {syncFeedback && (
        <div
          className="p-3 rounded-lg text-xs font-mono flex items-center justify-between"
          style={{
            background: 'rgba(56,189,248,0.08)',
            border: '1px solid rgba(56,189,248,0.2)',
            color: '#38BDF8',
          }}
        >
          <span>{syncFeedback}</span>
          <button
            onClick={() => setSyncFeedback(null)}
            className="text-slate-500 hover:text-white"
          >
            ×
          </button>
        </div>
      )}

      {/* Filter and Legend Bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap pb-1">
        <div className="flex items-center gap-1.5">
          {['ALL', 'Order', 'Product', 'Supplier', 'Warehouse', 'Customer'].map(
            (t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className="px-2.5 py-1 rounded-md text-[10px] font-mono transition"
                style={{
                  background:
                    typeFilter === t ? 'rgba(56,189,248,0.15)' : '#0F172A',
                  border: `1px solid ${
                    typeFilter === t ? '#38BDF8' : '#1E293B'
                  }`,
                  color: typeFilter === t ? '#38BDF8' : '#64748B',
                }}
              >
                {t}
              </button>
            )
          )}
        </div>

        <div className="flex items-center gap-3">
          {Object.entries(NODE_STYLE)
            .slice(0, 5)
            .map(([type, s]) => (
              <div
                key={type}
                className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500"
              >
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ background: s.color, opacity: 0.8 }}
                />
                {type}
              </div>
            ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex flex-col lg:flex-row gap-5 items-start">
        {/* ── Left / Canvas ── */}
        <div
          className="flex-1 w-full rounded-xl overflow-hidden canvas-dot-grid relative"
          style={{
            background: '#080C14',
            border: '1px solid #1E293B',
          }}
        >
          <svg
            id="knowledge-graph-canvas"
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            width="100%"
            style={{ display: 'block', minHeight: '440px' }}
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Arrow markers */}
            <defs>
              <marker
                id="arrow-dim"
                markerWidth="6"
                markerHeight="6"
                refX="5"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L6,3 L0,6 Z" fill="#1E293B" />
              </marker>
              <marker
                id="arrow-active"
                markerWidth="6"
                markerHeight="6"
                refX="5"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L6,3 L0,6 Z" fill="#38BDF8" />
              </marker>
              <marker
                id="arrow-affected"
                markerWidth="6"
                markerHeight="6"
                refX="5"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L6,3 L0,6 Z" fill="#EF4444" />
              </marker>
            </defs>

            {/* Render Edges */}
            {liveEdges.map((edge) => {
              const fromCenter = nodeCenters[edge.source];
              const toCenter = nodeCenters[edge.target];
              if (!fromCenter || !toCenter) return null;

              const isHighlighted = highlightedEdgeIds.has(edge.id);
              const isAffected =
                affectedNodeIds.has(edge.source) &&
                affectedNodeIds.has(edge.target);
              const isDimmed = hasSelection && !isHighlighted && !isAffected;

              const fromPt = clampToBox(toCenter, fromCenter);
              const toPt = clampToBox(fromCenter, toCenter);
              const mid = midpoint(fromCenter, toCenter);

              const dx = toCenter.cx - fromCenter.cx;
              const dy = toCenter.cy - fromCenter.cy;
              const len = Math.sqrt(dx * dx + dy * dy) || 1;
              const perpX = (-dy / len) * 10;
              const perpY = (dx / len) * 10;

              return (
                <g key={edge.id}>
                  <line
                    x1={fromPt.x}
                    y1={fromPt.y}
                    x2={toPt.x}
                    y2={toPt.y}
                    stroke={
                      isAffected
                        ? '#EF4444'
                        : isHighlighted
                        ? '#38BDF8'
                        : isDimmed
                        ? '#1A2336'
                        : '#243350'
                    }
                    strokeWidth={isAffected ? 2 : isHighlighted ? 1.5 : 1}
                    markerEnd={`url(#${
                      isAffected
                        ? 'arrow-affected'
                        : isHighlighted
                        ? 'arrow-active'
                        : 'arrow-dim'
                    })`}
                    strokeDasharray={isHighlighted || isAffected ? '0' : '4 4'}
                    className={
                      isHighlighted || isAffected ? 'animate-dash-flow' : ''
                    }
                    opacity={isDimmed ? 0.25 : 1}
                  />
                  <text
                    x={mid.x + perpX}
                    y={mid.y + perpY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    fill={
                      isAffected
                        ? '#F87171'
                        : isHighlighted
                        ? '#94A3B8'
                        : isDimmed
                        ? '#1E293B'
                        : '#334155'
                    }
                    opacity={isDimmed ? 0 : 1}
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Render Nodes */}
            {filteredNodes.map((node) => {
              const pos = nodeCenters[node.id];
              if (!pos) return null;
              const isSelected = node.id === selectedGraphNodeId;
              const isAffected = affectedNodeIds.has(node.id);
              const isDimmed =
                hasSelection &&
                !relatedNodeIds.has(node.id) &&
                !affectedNodeIds.has(node.id);

              return (
                <NodeCard
                  key={node.id}
                  node={node}
                  pos={pos}
                  isSelected={isSelected}
                  isDimmed={isDimmed}
                  isAffected={isAffected}
                  onClick={() => setSelectedGraphNodeId(node.id)}
                />
              );
            })}
          </svg>

          {/* Canvas Bottom Overlay */}
          <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between text-[10px] font-mono text-slate-500">
            <span>
              ENTITIES: {filteredNodes.length} / {liveNodes.length} · EDGES: {liveEdges.length}
            </span>
            <span>
              SOURCE OF TRUTH: PostgreSQL · GRAPH TRAVERSAL: Active
            </span>
          </div>
        </div>

        {/* ── Right Inspector & Tool Panel ── */}
        <div
          className="w-full lg:w-96 rounded-xl overflow-hidden flex flex-col shrink-0"
          style={{
            background: '#0F172A',
            border: `1px solid ${selectedStyle.border}`,
          }}
        >
          {/* Tabs */}
          <div className="flex border-b border-[#1E293B] bg-[#0A0F1D]">
            <button
              onClick={() => setActiveTab('inspector')}
              className={`flex-1 py-2.5 text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                activeTab === 'inspector'
                  ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-950/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Inspector
            </button>
            <button
              onClick={() => setActiveTab('impact')}
              className={`flex-1 py-2.5 text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                activeTab === 'impact'
                  ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-950/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Impact Simulator
            </button>
            <button
              onClick={() => setActiveTab('provenance')}
              className={`flex-1 py-2.5 text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                activeTab === 'provenance'
                  ? 'text-indigo-400 border-b-2 border-indigo-400 bg-indigo-950/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Provenance
            </button>
          </div>

          {/* Tab 1: Entity Inspector */}
          {activeTab === 'inspector' && (
            <div>
              <div
                className="px-4 py-4 border-b"
                style={{
                  borderColor: selectedStyle.border,
                  background: selectedStyle.activeBg,
                }}
              >
                <div
                  className="text-[9px] font-mono font-bold uppercase tracking-widest mb-1"
                  style={{ color: selectedStyle.color }}
                >
                  {selectedStyle.typeLabel} ENTITY
                </div>
                <h2 className="text-base font-extrabold text-white leading-tight">
                  {selectedNode.label}
                </h2>
                {selectedNode.status && (
                  <div
                    className="text-[11px] font-mono mt-1 font-bold"
                    style={{ color: selectedStyle.color }}
                  >
                    ● {selectedNode.status}
                  </div>
                )}
              </div>

              <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
                {/* Properties */}
                <div>
                  <div className="text-[9px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-2">
                    Properties & Relational State
                  </div>
                  <div className="space-y-1.5">
                    {Object.entries(selectedNode.details || {}).map(([k, v]) => (
                      <div
                        key={k}
                        className="flex items-center justify-between px-3 py-1.5 rounded-lg"
                        style={{
                          background: '#080C14',
                          border: '1px solid #1E293B',
                        }}
                      >
                        <span className="text-[11px] text-slate-500 font-mono">
                          {k}
                        </span>
                        <span className="text-[11px] text-slate-200 font-mono font-medium">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Direct Relationships */}
                <div>
                  <div className="text-[9px] font-mono font-bold text-slate-500 uppercase tracking-widest mb-2">
                    Direct Relationships ({liveEdges.filter((e) => e.source === selectedNode.id || e.target === selectedNode.id).length})
                  </div>
                  {liveEdges
                    .filter(
                      (e) =>
                        e.source === selectedNode.id ||
                        e.target === selectedNode.id
                    )
                    .map((edge) => {
                      const otherId =
                        edge.source === selectedNode.id
                          ? edge.target
                          : edge.source;
                      const otherNode = liveNodes.find((n) => n.id === otherId);
                      const otherStyle = otherNode
                        ? NODE_STYLE[otherNode.type] || DEFAULT_STYLE
                        : DEFAULT_STYLE;
                      return (
                        <button
                          key={edge.id}
                          onClick={() => setSelectedGraphNodeId(otherId)}
                          className="w-full flex items-center justify-between px-3 py-2 rounded-lg mb-1.5 transition text-left cursor-pointer"
                          style={{
                            background: '#080C14',
                            border: '1px solid #1E293B',
                          }}
                        >
                          <div className="min-w-0">
                            <div className="text-[11px] font-bold text-white truncate">
                              {otherNode?.label ?? otherId}
                            </div>
                            <div
                              className="text-[10px] font-mono mt-0.5"
                              style={{ color: otherStyle.color }}
                            >
                              {otherNode?.type ?? 'Entity'} ·{' '}
                              <span className="text-slate-500">
                                {edge.label}
                              </span>
                            </div>
                          </div>
                          <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0 ml-2" />
                        </button>
                      );
                    })}
                </div>

                {/* Cypher Query Preview */}
                <div
                  className="rounded-lg p-3"
                  style={{
                    background: '#080C14',
                    border: '1px solid rgba(99,102,241,0.2)',
                  }}
                >
                  <div className="text-[9px] font-mono font-bold text-indigo-400 uppercase tracking-widest mb-1.5">
                    Parameterized Cypher Pattern
                  </div>
                  <div className="font-mono text-[10px] text-slate-400 leading-relaxed break-all">
                    MATCH (n {'{'}id: &quot;{selectedNode.id}&quot;{'}'})-[r]-(m)
                    <br />
                    RETURN n, r, m LIMIT 25;
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleFetchProvenance(selectedNode.id)}
                    className="flex-1 py-2 rounded-lg text-[11px] font-semibold transition cursor-pointer flex items-center justify-center gap-1.5"
                    style={{
                      background: selectedStyle.activeBg,
                      color: selectedStyle.color,
                      border: `1px solid ${selectedStyle.border}`,
                    }}
                  >
                    <Network className="w-3.5 h-3.5" />
                    Inspect Lineage
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Disruption Impact Simulator */}
          {activeTab === 'impact' && (
            <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
              <div>
                <div className="text-[10px] font-mono uppercase text-slate-500 font-bold tracking-wider mb-1">
                  Simulate Supply Disruption
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Traverse downstream dependencies across Products, Purchase Orders, and Warehouses to quantify financial exposure.
                </p>

                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] font-mono text-slate-400 uppercase">
                      Origin Entity ID:
                    </label>
                    <input
                      type="text"
                      value={impactOrigin}
                      onChange={(e) => setImpactOrigin(e.target.value)}
                      className="w-full mt-1 px-3 py-1.5 text-xs font-mono text-white rounded-lg focus:outline-none"
                      style={{
                        background: '#080C14',
                        border: '1px solid #1E293B',
                      }}
                      placeholder="e.g. sup-b or sup-1"
                    />
                  </div>

                  <div>
                    <label className="text-[10px] font-mono text-slate-400 uppercase">
                      Severity:
                    </label>
                    <select
                      value={impactSeverity}
                      onChange={(e) => setImpactSeverity(e.target.value)}
                      className="w-full mt-1 px-3 py-1.5 text-xs font-mono text-white rounded-lg focus:outline-none"
                      style={{
                        background: '#080C14',
                        border: '1px solid #1E293B',
                      }}
                    >
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="MEDIUM">MEDIUM</option>
                    </select>
                  </div>

                  <button
                    onClick={handleRunImpactAnalysis}
                    disabled={isAnalyzingImpact}
                    className="w-full py-2 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer"
                    style={{
                      background: 'linear-gradient(135deg, #EF4444 0%, #B91C1C 100%)',
                      color: '#FFFFFF',
                    }}
                  >
                    <Activity
                      className={`w-3.5 h-3.5 ${
                        isAnalyzingImpact ? 'animate-spin' : ''
                      }`}
                    />
                    {isAnalyzingImpact ? 'Traversing Graph...' : 'Execute Impact Analysis'}
                  </button>
                </div>
              </div>

              {/* Impact Results */}
              {impactResult && (
                <div
                  className="rounded-lg p-3 space-y-3"
                  style={{
                    background: '#080C14',
                    border: '1px solid rgba(239,68,68,0.3)',
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold text-red-400 uppercase tracking-widest flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Disruption Assessment
                    </span>
                    <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800">
                      {impactResult.severity}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800">
                      <div className="text-[9px] font-mono text-slate-500">
                        REVENUE AT RISK
                      </div>
                      <div className="text-sm font-bold text-red-400 mt-0.5">
                        ₹
                        {impactResult.total_revenue_at_risk_inr.toLocaleString(
                          'en-IN'
                        )}
                      </div>
                    </div>
                    <div className="p-2 rounded bg-slate-900 border border-slate-800">
                      <div className="text-[9px] font-mono text-slate-500">
                        ORDERS AT RISK
                      </div>
                      <div className="text-sm font-bold text-white mt-0.5">
                        {impactResult.affected_order_ids.length}
                      </div>
                    </div>
                  </div>

                  {impactResult.alternative_suppliers.length > 0 && (
                    <div>
                      <div className="text-[9px] font-mono text-emerald-400 font-bold uppercase mb-1 flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3" />
                        Discovered Alternative Suppliers
                      </div>
                      <div className="space-y-1">
                        {impactResult.alternative_suppliers.map((alt: any) => (
                          <div
                            key={alt.supplier_id}
                            className="p-1.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono flex items-center justify-between"
                          >
                            <span className="text-white font-medium">
                              {alt.name}
                            </span>
                            <span className="text-emerald-400">
                              ₹{alt.unit_cost_inr} · {alt.lead_time_days}d
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <div className="text-[9px] font-mono text-cyan-400 font-bold uppercase mb-1">
                      Graph Mitigative Action
                    </div>
                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {impactResult.mitigation_recommendation}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Lineage & Provenance */}
          {activeTab === 'provenance' && (
            <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
              <div>
                <div className="text-[10px] font-mono uppercase text-slate-500 font-bold tracking-wider mb-1">
                  Entity Lineage & Grounding
                </div>
                <p className="text-xs text-slate-400">
                  Audit trail and relational source references confirming entity integrity.
                </p>
              </div>

              {isLoadingProvenance ? (
                <div className="text-center py-8 text-xs font-mono text-slate-500">
                  Traversing provenance hops...
                </div>
              ) : provenanceResponse ? (
                <div className="space-y-3">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                    <div className="text-[9px] font-mono text-indigo-400 uppercase font-bold mb-1">
                      Traversal Scope
                    </div>
                    <div className="text-slate-300 font-mono text-[11px]">
                      {provenanceResponse.node_count} nodes connected across{' '}
                      {provenanceResponse.edge_count} relationships in{' '}
                      {provenanceResponse.query_time_ms.toFixed(1)}ms.
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    {provenanceResponse.nodes.map((n) => (
                      <div
                        key={n.id}
                        className="p-2 rounded bg-[#080C14] border border-[#1E293B] text-[11px] font-mono flex items-center justify-between"
                      >
                        <div>
                          <div className="text-white font-bold">{n.label}</div>
                          <div className="text-[9px] text-slate-500">
                            Source: {n.source_table || 'Authoritative DB'} [ID:{' '}
                            {n.source_id || n.id}]
                          </div>
                        </div>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                          {n.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-xs font-mono text-slate-500">
                  Select an entity in the Inspector and click &quot;Inspect Lineage&quot; to trace graph provenance.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
