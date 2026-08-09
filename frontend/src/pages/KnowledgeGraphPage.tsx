import React, { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { GraphNode } from '../types';

/* ─────────────────────────────────────────────────
   Node visual config per entity type
───────────────────────────────────────────────── */
const NODE_STYLE: Record<GraphNode['type'], {
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
};

/* ─────────────────────────────────────────────────
   Structured layout positions
   Canvas is 700 × 440 (SVG viewBox)
   Nodes are 160 × 76 cards.
   Positions are the CENTER of each node.
───────────────────────────────────────────────── */
const NODE_CENTERS: Record<string, { cx: number; cy: number }> = {
  'cust-1':    { cx: 350, cy: 60  },  // top center
  'ord-1042':  { cx: 350, cy: 190 },  // center
  'prod-800':  { cx: 175, cy: 340 },  // bottom left
  'wh-nagpur': { cx: 350, cy: 390 },  // bottom center (slightly lower)
  'sup-b':     { cx: 525, cy: 340 },  // bottom right
};

// Half-dimensions of the node card in SVG units
const NODE_W2 = 80; // half-width
const NODE_H2 = 38; // half-height

/* ─────────────────────────────────────────────────
   Edge label: midpoint between two centers
───────────────────────────────────────────────── */
function midpoint(a: { cx: number; cy: number }, b: { cx: number; cy: number }) {
  return { x: (a.cx + b.cx) / 2, y: (a.cy + b.cy) / 2 };
}

/* ─────────────────────────────────────────────────
   Clamp line endpoint to the node border
───────────────────────────────────────────────── */
function clampToBox(
  fromCenter: { cx: number; cy: number },
  toCenter:   { cx: number; cy: number }
): { x: number; y: number } {
  const dx = toCenter.cx - fromCenter.cx;
  const dy = toCenter.cy - fromCenter.cy;
  const len = Math.sqrt(dx * dx + dy * dy) || 1;
  const nx = dx / len;
  const ny = dy / len;
  // Step inward from toCenter by half-box dimensions
  const tMaxX = NODE_W2 / Math.abs(nx || 0.001);
  const tMaxY = NODE_H2 / Math.abs(ny || 0.001);
  const t = Math.min(tMaxX, tMaxY);
  return { x: toCenter.cx - nx * t, y: toCenter.cy - ny * t };
}

/* ─────────────────────────────────────────────────
   Node Card component (rendered as foreignObject)
───────────────────────────────────────────────── */
interface NodeCardProps {
  node: GraphNode;
  isSelected: boolean;
  isDimmed: boolean;
  onClick: () => void;
}

const NodeCard: React.FC<NodeCardProps> = ({ node, isSelected, isDimmed, onClick }) => {
  const s = NODE_STYLE[node.type];
  const pos = NODE_CENTERS[node.id];
  if (!pos) return null;

  // Expand Order node slightly (it's the central entity)
  const isOrder = node.type === 'Order';
  const w = isOrder ? 176 : 160;
  const h = isOrder ? 86  : 76;

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
        title={node.label}
        style={{
          width: `${w}px`,
          height: `${h}px`,
          background:  isSelected ? s.activeBg : s.bg,
          border:      `${isSelected ? '2px' : '1px'} solid ${isSelected ? s.color : isDimmed ? '#1E293B' : s.border}`,
          borderRadius: '10px',
          padding:     '8px 12px',
          cursor:      'pointer',
          opacity:     isDimmed ? 0.35 : 1,
          boxShadow:   isSelected ? `0 0 16px ${s.color}25` : 'none',
          transition:  'all 0.15s ease',
          display:     'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: '2px',
          userSelect: 'none',
        }}
      >
        <div style={{ fontSize: '9px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: s.color, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          {s.typeLabel}
        </div>
        <div style={{ fontSize: isOrder ? '13px' : '12px', fontWeight: 700, color: '#F1F5F9', lineHeight: '1.2', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {node.label}
        </div>
        {node.status && (
          <div style={{ fontSize: '9px', fontFamily: 'JetBrains Mono, monospace', color: s.color, marginTop: '1px' }}>
            ● {node.status}
          </div>
        )}
        {!node.status && (
          <div style={{ fontSize: '9px', color: '#475569', fontFamily: 'JetBrains Mono, monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {Object.entries(node.details).map(([k, v]) => `${k}: ${v}`).slice(0, 1).join(' · ')}
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
  const { graphNodes, graphEdges, selectedGraphNodeId, setSelectedGraphNodeId } = useDemo();
  const [queryText, setQueryText] = useState('');

  const selectedNode = graphNodes.find(n => n.id === selectedGraphNodeId) ?? graphNodes[1];
  const selectedStyle = NODE_STYLE[selectedNode.type];

  // Which node IDs are directly connected to the selected node?
  const relatedNodeIds = new Set<string>();
  if (selectedGraphNodeId) {
    graphEdges.forEach(e => {
      if (e.source === selectedGraphNodeId) relatedNodeIds.add(e.target);
      if (e.target === selectedGraphNodeId) relatedNodeIds.add(e.source);
    });
    relatedNodeIds.add(selectedGraphNodeId);
  }

  const hasSelection = selectedGraphNodeId != null;

  // Edges connected to selection
  const highlightedEdgeIds = new Set(
    graphEdges
      .filter(e => e.source === selectedGraphNodeId || e.target === selectedGraphNodeId)
      .map(e => e.id)
  );

  // Canvas dimensions
  const SVG_W = 700;
  const SVG_H = 460;

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Knowledge Graph Ontology</h1>
          <p className="text-sm text-slate-500 mt-1">
            Entity relationship canvas — click any node to inspect connections
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <input
              type="text"
              id="graph-query"
              placeholder="Query entities, IDs, or relationships…"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              className="h-9 pl-3 pr-4 w-64 text-[12px] text-slate-200 placeholder-slate-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              style={{ background: '#0F172A', border: '1px solid #1E293B' }}
            />
          </div>
          <span
            className="px-2.5 py-1.5 rounded-lg text-[10px] font-mono text-indigo-300 font-bold shrink-0"
            style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}
          >
            Neo4j Ready
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap">
        {Object.entries(NODE_STYLE).map(([type, s]) => (
          <div key={type} className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: s.color, opacity: 0.7 }} />
            {type}
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="flex gap-5" style={{ alignItems: 'flex-start' }}>

        {/* ── Graph Canvas ── */}
        <div
          className="flex-1 min-w-0 rounded-xl overflow-hidden canvas-dot-grid relative"
          style={{
            background: '#080C14',
            border: '1px solid #1E293B',
            // Maintain aspect ratio
          }}
        >
          <svg
            id="knowledge-graph-canvas"
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            width="100%"
            style={{ display: 'block', minHeight: '420px' }}
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Arrow marker */}
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
            </defs>

            {/* Draw edges */}
            {graphEdges.map(edge => {
              const fromCenter = NODE_CENTERS[edge.source];
              const toCenter   = NODE_CENTERS[edge.target];
              if (!fromCenter || !toCenter) return null;

              const isHighlighted = highlightedEdgeIds.has(edge.id);
              const isDimmed      = hasSelection && !isHighlighted;

              // Clamp to node border so arrow doesn't overlap card
              const fromPt = clampToBox(toCenter, fromCenter);
              const toPt   = clampToBox(fromCenter, toCenter);
              const mid    = midpoint(fromCenter, toCenter);

              // Offset label slightly so it doesn't sit on the line
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
                    stroke={isHighlighted ? '#38BDF8' : isDimmed ? '#1A2336' : '#243350'}
                    strokeWidth={isHighlighted ? 1.5 : 1}
                    markerEnd={`url(#${isHighlighted ? 'arrow-active' : 'arrow-dim'})`}
                    strokeDasharray={isHighlighted ? '0' : '4 4'}
                    className={isHighlighted ? 'animate-dash-flow' : ''}
                    opacity={isDimmed ? 0.3 : 1}
                  />
                  {/* Edge label */}
                  <text
                    x={mid.x + perpX}
                    y={mid.y + perpY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    fill={isHighlighted ? '#94A3B8' : isDimmed ? '#1E293B' : '#334155'}
                    opacity={isDimmed ? 0 : 1}
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Draw nodes */}
            {graphNodes.map(node => {
              const isSelected = node.id === selectedGraphNodeId;
              const isDimmed   = hasSelection && !relatedNodeIds.has(node.id);
              return (
                <NodeCard
                  key={node.id}
                  node={node}
                  isSelected={isSelected}
                  isDimmed={isDimmed}
                  onClick={() => setSelectedGraphNodeId(node.id)}
                />
              );
            })}
          </svg>

          {/* Workflow hint */}
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 text-[9px] font-mono text-slate-700 whitespace-nowrap">
            CUSTOMER → ORDER → PRODUCT → SUPPLIER / WAREHOUSE
          </div>
        </div>

        {/* ── Right Inspector ── */}
        <div
          className="rounded-xl overflow-hidden flex flex-col shrink-0"
          style={{
            width: '320px',
            background: '#0F172A',
            border: `1px solid ${selectedStyle.border}`,
          }}
        >
          {/* Inspector Header */}
          <div
            className="px-4 py-4 border-b"
            style={{ borderColor: selectedStyle.border, background: selectedStyle.activeBg }}
          >
            <div
              className="text-[9px] font-mono font-bold uppercase tracking-widest mb-1"
              style={{ color: selectedStyle.color }}
            >
              {selectedStyle.typeLabel} ENTITY
            </div>
            <h2 className="text-base font-extrabold text-white leading-tight">{selectedNode.label}</h2>
            {selectedNode.status && (
              <div className="text-[11px] font-mono mt-1 font-bold" style={{ color: selectedStyle.color }}>
                ● {selectedNode.status}
              </div>
            )}
          </div>

          <div className="p-4 space-y-4 overflow-y-auto flex-1">
            {/* Attributes */}
            <div>
              <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-2">Attributes</div>
              <div className="space-y-1.5">
                {Object.entries(selectedNode.details).map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between px-3 py-1.5 rounded-lg"
                    style={{ background: '#080C14', border: '1px solid #1E293B' }}
                  >
                    <span className="text-[11px] text-slate-500 font-mono">{k}</span>
                    <span className="text-[11px] text-slate-200 font-mono font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Direct Relationships */}
            <div>
              <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-2">
                Direct Relationships
              </div>
              {graphEdges
                .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                .map(edge => {
                  const otherId    = edge.source === selectedNode.id ? edge.target : edge.source;
                  const otherNode  = graphNodes.find(n => n.id === otherId);
                  const otherStyle = otherNode ? NODE_STYLE[otherNode.type] : null;
                  return (
                    <button
                      key={edge.id}
                      onClick={() => setSelectedGraphNodeId(otherId)}
                      className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg mb-1.5 transition"
                      style={{ background: '#080C14', border: '1px solid #1E293B' }}
                    >
                      <div className="text-left min-w-0">
                        <div className="text-[12px] font-bold text-white truncate">{otherNode?.label ?? otherId}</div>
                        <div className="text-[10px] font-mono mt-0.5" style={{ color: otherStyle?.color ?? '#64748B' }}>
                          {otherNode?.type ?? '—'} · <span className="text-slate-500">{edge.label}</span>
                        </div>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0 ml-2" />
                    </button>
                  );
                })}

              {graphEdges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length === 0 && (
                <div className="text-[11px] text-slate-700 font-mono">No direct relationships.</div>
              )}
            </div>

            {/* Cypher Preview */}
            <div
              className="rounded-lg p-3"
              style={{ background: '#080C14', border: '1px solid rgba(99,102,241,0.2)' }}
            >
              <div className="text-[9px] font-mono font-bold text-indigo-400 uppercase tracking-widest mb-1.5">
                Cypher Query (Neo4j)
              </div>
              <div className="font-mono text-[10px] text-slate-400 leading-relaxed">
                {'MATCH (n {id: "'}<span style={{ color: selectedStyle.color }}>{selectedNode.id}</span>{'"})'}<br />
                {'-[r]->(m)'}<br />
                {'RETURN n, r, m LIMIT 10'}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              <button
                className="flex-1 py-2 rounded-lg text-[11px] font-semibold transition"
                style={{ background: selectedStyle.activeBg, color: selectedStyle.color, border: `1px solid ${selectedStyle.border}` }}
              >
                View Details
              </button>
              <button
                className="flex-1 py-2 rounded-lg text-[11px] font-semibold transition"
                style={{ background: '#1E293B', color: '#94A3B8', border: '1px solid #1E293B' }}
              >
                Resolve Issue
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
