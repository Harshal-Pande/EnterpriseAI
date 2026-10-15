import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useDemo } from '../state/DemoContext';
import { PageHeader } from '../components/common/PageHeader';
import { Panel } from '../components/common/Panel';
import { KeyValueList } from '../components/common/KeyValueList';
import { apiClient, type BackendGraphStatus } from '../services/apiClient';
import type { GraphNode, GraphEdge } from '../types';

interface ExtendedGraphNode extends GraphNode {
  category: 'Customer' | 'Order' | 'Product' | 'Warehouse' | 'Supplier' | 'Shipment';
  x: number;
  y: number;
}

const CATEGORY_CSS_VARS: Record<string, string> = {
  Customer: '--n-customer',
  Order: '--n-order',
  Product: '--n-product',
  Warehouse: '--n-warehouse',
  Supplier: '--n-supplier',
  Shipment: '--n-shipment',
};

export const KnowledgeGraphPage: React.FC<{ onNavigate?: (screen: any) => void }> = ({ onNavigate }) => {
  const {
    graphNodes: demoNodes,
    graphEdges: demoEdges,
    selectedGraphNodeId,
    setSelectedGraphNodeId,
  } = useDemo();

  const [graphStatus, setGraphStatus] = useState<BackendGraphStatus | null>(null);
  const [nodes, setNodes] = useState<ExtendedGraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<Record<string, boolean>>({
    Customer: true,
    Order: true,
    Product: true,
    Warehouse: true,
    Supplier: true,
    Shipment: true,
  });

  // Zoom & Pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // Impact Tracing state
  const [impactHops, setImpactHops] = useState(2);
  const [impactedNodeIds, setImpactedNodeIds] = useState<Set<string> | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Fetch backend graph status on mount
  useEffect(() => {
    let isMounted = true;
    apiClient
      .getGraphStatus()
      .then(st => {
        if (isMounted) setGraphStatus(st);
      })
      .catch(() => {
        // Fallback status
      });

    apiClient
      .getKnowledgeGraph(undefined, undefined, 100)
      .then(res => {
        if (!isMounted || !res.nodes || res.nodes.length === 0) return;
        const mappedNodes: ExtendedGraphNode[] = res.nodes.map((n, idx) => {
          const type = (n.type as any) || 'Product';
          const angle = (idx / res.nodes.length) * 2 * Math.PI;
          const radius = 180;
          return {
            id: n.id,
            label: n.label,
            type,
            category: (['Customer', 'Order', 'Product', 'Warehouse', 'Supplier', 'Shipment'].includes(type)
              ? type
              : 'Product') as any,
            status: n.status,
            details: n.properties || {},
            x: 360 + Math.cos(angle) * radius,
            y: 260 + Math.sin(angle) * radius,
          };
        });
        const mappedEdges: GraphEdge[] = res.edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || e.type,
        }));
        setNodes(mappedNodes);
        setEdges(mappedEdges);
      })
      .catch(() => {
        // Use demo nodes with structured layout
        const structured: ExtendedGraphNode[] = [
          { ...demoNodes[0], category: 'Customer', x: 200, y: 140 },
          { ...demoNodes[1], category: 'Order', x: 380, y: 220 },
          { ...demoNodes[2], category: 'Product', x: 560, y: 150 },
          { ...demoNodes[3], category: 'Supplier', x: 620, y: 310 },
          { ...demoNodes[4], category: 'Warehouse', x: 260, y: 340 },
          {
            id: 'shp-8841',
            label: 'SHP-8841 (Concor Rail)',
            type: 'Shipment' as any,
            category: 'Shipment',
            status: 'In Transit',
            details: { Carrier: 'Concor Express', Mode: 'Rail Freight', SLA: '48h buffer' },
            x: 460,
            y: 370,
          },
        ];
        const structuredEdges: GraphEdge[] = [
          ...demoEdges,
          { id: 'e5', source: 'ord-1042', target: 'shp-8841', label: 'dispatched via' },
        ];
        setNodes(structured);
        setEdges(structuredEdges);
      });

    return () => {
      isMounted = false;
    };
  }, [demoNodes, demoEdges]);

  // Compute active nodes based on search and type filters
  const filteredNodes = useMemo(() => {
    return nodes.filter(n => {
      if (!selectedTypes[n.category]) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q);
      }
      return true;
    });
  }, [nodes, selectedTypes, searchQuery]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map(n => n.id)), [filteredNodes]);

  const filteredEdges = useMemo(() => {
    return edges.filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [edges, filteredNodeIds]);

  // Selected node & neighbors
  const selectedNode = useMemo(() => {
    return nodes.find(n => n.id === selectedGraphNodeId) || null;
  }, [nodes, selectedGraphNodeId]);

  const neighborNodeIds = useMemo(() => {
    if (!selectedGraphNodeId) return new Set<string>();
    const neighbors = new Set<string>();
    for (const edge of edges) {
      if (edge.source === selectedGraphNodeId) neighbors.add(edge.target);
      if (edge.target === selectedGraphNodeId) neighbors.add(edge.source);
    }
    return neighbors;
  }, [edges, selectedGraphNodeId]);

  // Trace Impact BFS
  const handleTraceImpact = useCallback(() => {
    if (!selectedGraphNodeId) return;
    const visited = new Set<string>([selectedGraphNodeId]);
    let currentLevel = [selectedGraphNodeId];

    for (let hop = 0; hop < impactHops; hop++) {
      const nextLevel: string[] = [];
      for (const curr of currentLevel) {
        for (const e of edges) {
          const neighbor = e.source === curr ? e.target : e.target === curr ? e.source : null;
          if (neighbor && !visited.has(neighbor)) {
            visited.add(neighbor);
            nextLevel.push(neighbor);
          }
        }
      }
      currentLevel = nextLevel;
      if (currentLevel.length === 0) break;
    }
    setImpactedNodeIds(visited);
  }, [selectedGraphNodeId, impactHops, edges]);

  const handleClearImpact = () => {
    setImpactedNodeIds(null);
  };

  // Canvas drawing loop throttled to rAF
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;

    if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }

    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    // Apply zoom & pan
    ctx.translate(width / 2 + pan.x, height / 2 + pan.y);
    ctx.scale(zoom, zoom);
    ctx.translate(-width / 2, -height / 2);

    // Read resolved design tokens from DOM
    const computed = getComputedStyle(canvas);
    const getVar = (name: string) => computed.getPropertyValue(name).trim();
    const accentColor = getVar('--accent');
    const borderStrong = getVar('--border-strong');
    const borderNormal = getVar('--border');
    const textColor = getVar('--text');
    const surface2 = getVar('--surface-2');
    const surfaceColor = getVar('--surface');

    // Node lookup map for positions
    const nodeMap = new Map(filteredNodes.map(n => [n.id, n]));

    // Draw Edges (1px)
    for (const edge of filteredEdges) {
      const src = nodeMap.get(edge.source);
      const tgt = nodeMap.get(edge.target);
      if (!src || !tgt) continue;

      const isImpactedEdge =
        impactedNodeIds && impactedNodeIds.has(src.id) && impactedNodeIds.has(tgt.id);

      ctx.beginPath();
      ctx.moveTo(src.x, src.y);
      ctx.lineTo(tgt.x, tgt.y);
      ctx.lineWidth = 1;
      ctx.strokeStyle = isImpactedEdge ? accentColor : borderStrong;
      ctx.globalAlpha = impactedNodeIds && !isImpactedEdge ? 0.2 : 0.6;
      ctx.stroke();
    }

    // Draw Nodes
    for (const node of filteredNodes) {
      const isSelected = node.id === selectedGraphNodeId;
      const isHovered = node.id === hoveredNodeId;
      const isNeighbor = neighborNodeIds.has(node.id);
      const isImpacted = impactedNodeIds?.has(node.id);
      const isDimmed = impactedNodeIds && !isImpacted;

      ctx.globalAlpha = isDimmed ? 0.2 : 1.0;

      const varName = CATEGORY_CSS_VARS[node.category] || '--text-3';
      const nodeColor = getVar(varName);

      // Outer ring for selected / impact
      if (isSelected || isImpacted) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 22, 0, 2 * Math.PI);
        ctx.fillStyle = isSelected ? `${accentColor}33` : `${borderStrong}33`;
        ctx.fill();
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.strokeStyle = isSelected ? accentColor : borderStrong;
        ctx.stroke();
      } else if (isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 20, 0, 2 * Math.PI);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = accentColor;
        ctx.stroke();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, 16, 0, 2 * Math.PI);
      ctx.fillStyle = nodeColor;
      ctx.fill();
      ctx.lineWidth = 1;
      ctx.strokeStyle = surfaceColor;
      ctx.stroke();

      // Labels: only on hover, selection, and for the selected node's neighbors
      if (isSelected || isHovered || isNeighbor) {
        ctx.font = '500 12px "IBM Plex Sans", sans-serif';
        ctx.fillStyle = textColor;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';

        // Background label pill
        const text = node.label;
        const textWidth = ctx.measureText(text).width;
        ctx.fillStyle = surface2;
        ctx.fillRect(node.x - textWidth / 2 - 4, node.y - 34, textWidth + 8, 16);
        ctx.strokeStyle = borderNormal;
        ctx.lineWidth = 0.5;
        ctx.strokeRect(node.x - textWidth / 2 - 4, node.y - 34, textWidth + 8, 16);

        ctx.fillStyle = textColor;
        ctx.fillText(text, node.x, node.y - 21);
      }
    }

    ctx.restore();
  }, [
    filteredNodes,
    filteredEdges,
    pan,
    zoom,
    selectedGraphNodeId,
    hoveredNodeId,
    neighborNodeIds,
    impactedNodeIds,
  ]);

  // Request Animation Frame loop
  useEffect(() => {
    let animId: number;
    const renderLoop = () => {
      draw();
      animId = requestAnimationFrame(renderLoop);
    };
    animId = requestAnimationFrame(renderLoop);
    return () => cancelAnimationFrame(animId);
  }, [draw]);

  // Transform canvas mouse coordinates to world coordinates
  const getWorldCoord = (clientX: number, clientY: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const canvasX = clientX - rect.left;
    const canvasY = clientY - rect.top;

    // Inverse transform
    const worldX = (canvasX - width / 2 - pan.x) / zoom + width / 2;
    const worldY = (canvasY - height / 2 - pan.y) / zoom + height / 2;
    return { x: worldX, y: worldY };
  };

  // Find node under cursor
  const findNodeAt = (clientX: number, clientY: number) => {
    const { x, y } = getWorldCoord(clientX, clientY);
    for (const node of filteredNodes) {
      const dx = node.x - x;
      const dy = node.y - y;
      if (Math.sqrt(dx * dx + dy * dy) <= 20) {
        return node;
      }
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const clickedNode = findNodeAt(e.clientX, e.clientY);
    if (clickedNode) {
      setSelectedGraphNodeId(clickedNode.id);
      return;
    }
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
      return;
    }
    const node = findNodeAt(e.clientX, e.clientY);
    setHoveredNodeId(node ? node.id : null);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom(z => Math.max(0.4, Math.min(3.0, z * factor)));
  };

  const handleFit = () => {
    if (filteredNodes.length === 0) return;
    setPan({ x: 0, y: 0 });
    setZoom(1);
  };

  const handleReset = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    setSelectedGraphNodeId(null);
    setImpactedNodeIds(null);
  };

  // Determine truthful backend status
  const isNeo4j =
    graphStatus?.connected &&
    (graphStatus?.engine?.toLowerCase().includes('neo4j') || false);

  const nodeCount = graphStatus?.node_count || nodes.length;
  const edgeCount = graphStatus?.relationship_count || edges.length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supply Chain Knowledge Graph"
        description="Multi-tier provenance, material dependencies, and disruption impact tracing."
        actions={
          <div className="flex items-center gap-2">
            <span
              className={`px-2.5 py-1 rounded-[4px] border text-12 font-medium ${
                isNeo4j
                  ? 'bg-ok-soft text-ok border-ok/40'
                  : 'bg-warn-soft text-warn border-warn/40'
              }`}
            >
              {isNeo4j ? 'Neo4j (live)' : 'Relational fallback'} · {nodeCount} nodes · {edgeCount} relationships
            </span>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 items-start">
        {/* Left Column: Search & Entity Filters */}
        <div className="space-y-4">
          <Panel title="Graph Filters" subtitle="Entity classes & search">
            <div className="space-y-4">
              <div>
                <label className="block text-12 text-text-3 mb-1">Search Nodes</label>
                <input
                  type="text"
                  placeholder="ID or label..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-[4px] border border-border bg-surface text-13 text-text focus:outline-none focus:border-accent"
                />
              </div>

              <div>
                <label className="block text-12 text-text-3 mb-2">Entity Types</label>
                <div className="space-y-2">
                  {Object.entries(CATEGORY_CSS_VARS).map(([cat, varName]) => (
                    <label key={cat} className="flex items-center gap-2 text-13 text-text cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!!selectedTypes[cat]}
                        onChange={e =>
                          setSelectedTypes(prev => ({ ...prev, [cat]: e.target.checked }))
                        }
                        className="rounded-[2px] border-border text-accent focus:ring-0"
                      />
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-[2px] shrink-0"
                        style={{ backgroundColor: `var(${varName})` }}
                      />
                      <span>{cat}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Trace Impact Tool */}
              <div className="pt-3 border-t border-border">
                <label className="block text-12 font-medium text-text mb-1">Trace Impact</label>
                <p className="text-12 text-text-3 mb-2">
                  Find all entities connected within N hops of the selected node.
                </p>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-12 text-text-2">Hops:</span>
                  <select
                    value={impactHops}
                    onChange={e => setImpactHops(Number(e.target.value))}
                    className="px-2 py-1 rounded-[4px] border border-border bg-surface text-12 font-mono text-text"
                  >
                    <option value={1}>1 hop</option>
                    <option value={2}>2 hops</option>
                    <option value={3}>3 hops</option>
                    <option value={4}>4 hops</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleTraceImpact}
                    disabled={!selectedGraphNodeId}
                    className="flex-1 px-3 py-1.5 rounded-[4px] bg-accent text-white text-12 font-medium hover:bg-accent-hover disabled:bg-surface-2 disabled:text-text-3 disabled:cursor-not-allowed"
                  >
                    Trace impact
                  </button>
                  {impactedNodeIds && (
                    <button
                      onClick={handleClearImpact}
                      className="px-3 py-1.5 rounded-[4px] border border-border bg-surface text-12 text-text-2 hover:bg-surface-2"
                    >
                      Clear
                    </button>
                  )}
                </div>
                {impactedNodeIds && (
                  <p className="text-12 text-accent mt-2 font-mono">
                    ● {impactedNodeIds.size} impacted nodes identified
                  </p>
                )}
              </div>
            </div>
          </Panel>
        </div>

        {/* Center: Canvas Viewport */}
        <div className="lg:col-span-2 space-y-4">
          <Panel
            title="Topology Canvas"
            subtitle="Interactive knowledge graph with 1px edge hierarchy"
            actions={
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleFit}
                  className="px-2 py-1 rounded-[4px] border border-border bg-surface text-12 text-text-2 hover:bg-surface-2"
                >
                  Fit
                </button>
                <button
                  onClick={handleReset}
                  className="px-2 py-1 rounded-[4px] border border-border bg-surface text-12 text-text-2 hover:bg-surface-2"
                >
                  Reset
                </button>
              </div>
            }
            padding="none"
          >
            <div className="relative w-full h-[520px] bg-surface-sunk overflow-hidden cursor-grab active:cursor-grabbing">
              <canvas
                ref={canvasRef}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onWheel={handleWheel}
                className="w-full h-full block"
              />
              <div className="absolute bottom-2 left-3 text-11 font-mono text-text-3 pointer-events-none">
                Zoom: {(zoom * 100).toFixed(0)}% · Click node to inspect · Drag to pan
              </div>
            </div>
          </Panel>

          {/* Accessible Text Alternative */}
          <Panel title="Visible Nodes Summary" subtitle="Accessible list view of active graph entities">
            <div className="text-12 text-text-2 space-y-1 max-h-36 overflow-y-auto">
              {filteredNodes.map(n => (
                <div key={n.id} className="flex items-center justify-between py-0.5 border-b border-border/50">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: `var(${CATEGORY_CSS_VARS[n.category] || '--text-3'})` }}
                    />
                    <span className="font-mono text-12 text-text">{n.id}</span>
                    <span className="text-12 text-text-2">· {n.label}</span>
                  </div>
                  <span className="text-11 text-text-3">{n.category}</span>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        {/* Right Column: Node Inspector */}
        <div className="space-y-4">
          <Panel title="Node Inspector" subtitle="Entity properties and relationships">
            {selectedNode ? (
              <div className="space-y-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className="w-3 h-3 rounded-[2px]"
                      style={{ backgroundColor: `var(${CATEGORY_CSS_VARS[selectedNode.category] || '--text-3'})` }}
                    />
                    <span className="text-11 uppercase font-semibold text-text-3 tracking-wide">
                      {selectedNode.category}
                    </span>
                  </div>
                  <h3 className="text-15 font-semibold text-text">{selectedNode.label}</h3>
                  <div className="font-mono text-12 text-text-3">{selectedNode.id}</div>
                </div>

                {/* Properties definition list */}
                <div>
                  <h4 className="text-12 font-medium text-text mb-2">Properties</h4>
                  <KeyValueList
                    items={Object.entries(selectedNode.details || {}).map(([k, v]) => ({
                      label: k,
                      value: String(v),
                    }))}
                  />
                </div>

                {/* Direct Neighbors */}
                <div>
                  <h4 className="text-12 font-medium text-text mb-2">Neighbors ({neighborNodeIds.size})</h4>
                  <div className="space-y-1.5">
                    {Array.from(neighborNodeIds).map(nbrId => {
                      const nbr = nodes.find(n => n.id === nbrId);
                      if (!nbr) return null;
                      return (
                        <button
                          key={nbrId}
                          onClick={() => setSelectedGraphNodeId(nbrId)}
                          className="w-full text-left p-2 rounded-[4px] border border-border bg-surface hover:bg-surface-2 flex items-center justify-between"
                        >
                          <div>
                            <div className="text-12 font-medium text-text">{nbr.label}</div>
                            <div className="text-11 font-mono text-text-3">{nbr.id}</div>
                          </div>
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: `var(${CATEGORY_CSS_VARS[nbr.category] || '--text-3'})` }}
                          />
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Open source record link */}
                <div className="pt-2 border-t border-border">
                  <button
                    onClick={() => {
                      if (!onNavigate) return;
                      if (selectedNode.category === 'Order') onNavigate('orders');
                      else if (selectedNode.category === 'Product' || selectedNode.category === 'Warehouse') onNavigate('inventory');
                      else if (selectedNode.category === 'Supplier') onNavigate('procurement');
                      else if (selectedNode.category === 'Shipment') onNavigate('logistics');
                    }}
                    className="text-12 font-medium text-accent hover:underline flex items-center gap-1"
                  >
                    Open source record →
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-13 text-text-3 py-6 text-center">
                Select any node on the topology canvas to inspect properties, dependencies, and trace impact.
              </p>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
};
