import React, { useState } from 'react';
import { Share2 as _Share2, ArrowRight } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { GraphNode } from '../types';

// Node visual styles per type
const NODE_STYLE: Record<GraphNode['type'], { color: string; border: string; bg: string; typeLabel: string }> = {
  Customer:  { color: '#38BDF8', border: 'rgba(56,189,248,0.5)',   bg: 'rgba(56,189,248,0.07)',   typeLabel: 'CUSTOMER'  },
  Order:     { color: '#F8FAFC', border: 'rgba(239,68,68,0.6)',    bg: 'rgba(239,68,68,0.06)',    typeLabel: 'ORDER'     },
  Product:   { color: '#34D399', border: 'rgba(52,211,153,0.5)',   bg: 'rgba(52,211,153,0.06)',   typeLabel: 'PRODUCT'   },
  Supplier:  { color: '#FCD34D', border: 'rgba(252,211,77,0.5)',   bg: 'rgba(252,211,77,0.06)',   typeLabel: 'SUPPLIER'  },
  Warehouse: { color: '#C084FC', border: 'rgba(192,132,252,0.5)',  bg: 'rgba(192,132,252,0.06)',  typeLabel: 'WAREHOUSE' },
};

// Positions as % of canvas — designed to avoid overlap
const NODE_POSITIONS: Record<string, { left: string; top: string }> = {
  'cust-1':     { left: '5%',   top: '35%' },
  'ord-1042':   { left: '38%',  top: '35%' },
  'prod-800':   { left: '70%',  top: '10%' },
  'sup-b':      { left: '70%',  top: '60%' },
  'wh-nagpur':  { left: '38%',  top: '68%' },
};

// Canvas dimensions for SVG line endpoints (relative to 100%x100%)
// We map from the center of each node (width ~180px, height ~70px)
function getCenter(nodeId: string): [string, string] {
  const pos = NODE_POSITIONS[nodeId];
  if (!pos) return ['50%', '50%'];
  // approximate center offset for node cards (~90px wide, ~35px tall)
  return [pos.left, pos.top];
}

export const KnowledgeGraphPage: React.FC = () => {
  const { graphNodes, graphEdges, selectedGraphNodeId, setSelectedGraphNodeId } = useDemo();
  const [queryText, setQueryText] = useState('');

  const selectedNode = graphNodes.find(n => n.id === selectedGraphNodeId) ?? graphNodes[1];
  const selectedStyle = NODE_STYLE[selectedNode.type];

  // Edges connected to selected node
  const relatedEdges = graphEdges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id);
  const relatedNodeIds = new Set([
    ...relatedEdges.map(e => e.source),
    ...relatedEdges.map(e => e.target)
  ]);

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-[#1E293B]">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Knowledge Graph Ontology</h1>
          <p className="text-sm text-slate-500 mt-1">Entity relationship canvas · Click a node to inspect</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <input
              type="text"
              id="graph-query"
              placeholder="Query entities, IDs, or relationships…"
              value={queryText}
              onChange={e => setQueryText(e.target.value)}
              className="h-9 pl-3 pr-4 w-72 text-[12px] text-slate-200 placeholder-slate-600 rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-500/50"
              style={{ background: '#0F172A', border: '1px solid #1E293B' }}
            />
          </div>
          <span className="px-2.5 py-1.5 rounded-lg text-[10px] font-mono text-indigo-300 font-bold"
            style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)' }}>
            Neo4j Ready
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Canvas */}
        <div
          className="lg:col-span-2 relative rounded-xl overflow-hidden canvas-dot-grid"
          style={{
            background: '#080C14',
            border: '1px solid #1E293B',
            minHeight: '480px'
          }}
        >
          {/* SVG edge lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
            {graphEdges.map(edge => {
              const [sx, sy] = getCenter(edge.source);
              const [tx, ty] = getCenter(edge.target);
              const isHighlighted = relatedNodeIds.has(edge.source) && relatedNodeIds.has(edge.target);
              return (
                <g key={edge.id}>
                  <line
                    x1={sx} y1={sy} x2={tx} y2={ty}
                    stroke={isHighlighted ? 'rgba(56,189,248,0.5)' : 'rgba(30,41,59,0.8)'}
                    strokeWidth={isHighlighted ? '1.5' : '1'}
                    strokeDasharray={isHighlighted ? '0' : '4 4'}
                  />
                  {/* Edge label at midpoint */}
                  <text
                    x={`calc(${sx} / 2 + ${tx} / 2)`}
                    textAnchor="middle"
                    fill={isHighlighted ? 'rgba(148,163,184,0.8)' : 'rgba(71,85,105,0.8)'}
                    fontSize="9"
                    fontFamily="JetBrains Mono, monospace"
                    dy="-4"
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Node cards */}
          {graphNodes.map(node => {
            const style    = NODE_STYLE[node.type];
            const pos      = NODE_POSITIONS[node.id];
            const isSelected = node.id === selectedGraphNodeId;
            const isRelated  = relatedNodeIds.has(node.id) && !isSelected;

            if (!pos) return null;
            return (
              <div
                key={node.id}
                id={`graph-node-${node.id}`}
                onClick={() => setSelectedGraphNodeId(node.id)}
                className="absolute z-10 cursor-pointer rounded-xl transition-all duration-200"
                style={{
                  left: pos.left,
                  top: pos.top,
                  width: '185px',
                  background: isSelected ? style.bg : '#0F172A',
                  border: `${isSelected ? '2px' : '1px'} solid ${isSelected ? style.border : isRelated ? 'rgba(56,189,248,0.2)' : '#1E293B'}`,
                  boxShadow: isSelected ? `0 0 20px ${style.bg}` : 'none',
                  padding: '10px 12px',
                }}
              >
                <div
                  className="text-[9px] font-mono font-bold uppercase tracking-widest mb-0.5"
                  style={{ color: style.color }}
                >
                  {style.typeLabel}
                </div>
                <div className="font-bold text-[13px] text-white leading-snug">{node.label}</div>
                {node.status && (
                  <div className="text-[10px] font-mono mt-1 font-bold" style={{ color: style.color }}>
                    ● {node.status}
                  </div>
                )}
                <div className="mt-1 space-y-0.5">
                  {Object.entries(node.details).slice(0, 2).map(([k, v]) => (
                    <div key={k} className="text-[9px] text-slate-500 font-mono truncate">
                      {k}: <span className="text-slate-400">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}

          {/* Legend */}
          <div
            className="absolute bottom-3 left-3 flex flex-wrap gap-2 z-10"
          >
            {Object.entries(NODE_STYLE).map(([type, s]) => (
              <div key={type} className="flex items-center gap-1.5 text-[9px] font-mono text-slate-500">
                <span className="w-2 h-2 rounded-sm" style={{ background: s.color, opacity: 0.7 }} />
                {type}
              </div>
            ))}
          </div>
        </div>

        {/* Detail Panel */}
        <div
          className="rounded-xl overflow-hidden flex flex-col"
          style={{ background: '#0F172A', border: `1px solid ${selectedStyle.border}` }}
        >
          {/* Panel Header */}
          <div
            className="px-5 py-4 border-b"
            style={{ borderColor: selectedStyle.border, background: selectedStyle.bg }}
          >
            <div
              className="text-[10px] font-mono font-bold uppercase tracking-widest mb-1"
              style={{ color: selectedStyle.color }}
            >
              {selectedStyle.typeLabel} ENTITY
            </div>
            <h2 className="text-lg font-extrabold text-white leading-tight">{selectedNode.label}</h2>
            {selectedNode.status && (
              <div className="text-[11px] font-mono mt-1 font-bold" style={{ color: selectedStyle.color }}>
                ● {selectedNode.status}
              </div>
            )}
          </div>

          <div className="p-5 space-y-4 flex-1">
            {/* Operational State */}
            <div>
              <div className="text-[9px] font-mono font-bold text-slate-600 uppercase tracking-widest mb-2">
                Attributes
              </div>
              <div className="space-y-1.5">
                {Object.entries(selectedNode.details).map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between px-3 py-2 rounded-lg"
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
              <div className="space-y-2">
                {graphEdges
                  .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map(edge => {
                    const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                    const otherNode = graphNodes.find(n => n.id === otherId);
                    const otherStyle = otherNode ? NODE_STYLE[otherNode.type] : null;
                    return (
                      <button
                        key={edge.id}
                        onClick={() => setSelectedGraphNodeId(otherId)}
                        className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition hover:opacity-80"
                        style={{ background: '#080C14', border: '1px solid #1E293B' }}
                      >
                        <div className="text-left">
                          <div className="text-[12px] font-bold text-white">{otherNode?.label ?? otherId}</div>
                          <div className="text-[10px] font-mono mt-0.5" style={{ color: otherStyle?.color ?? '#64748B' }}>
                            {otherNode?.type} · {edge.label}
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                      </button>
                    );
                  })}
              </div>
            </div>

            {/* Cypher Query Preview */}
            <div
              className="rounded-lg p-3"
              style={{ background: '#080C14', border: '1px solid rgba(99,102,241,0.2)' }}
            >
              <div className="text-[9px] font-mono font-bold text-indigo-400 uppercase tracking-widest mb-1.5">
                Cypher Query (Neo4j)
              </div>
              <div className="font-mono text-[10px] text-slate-400 leading-relaxed">
                {'MATCH (n {id: "'}
                <span style={{ color: selectedStyle.color }}>{selectedNode.id}</span>
                {'"})-[r]->(m)'}
                <br />
                {'RETURN n, r, m LIMIT 10'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
