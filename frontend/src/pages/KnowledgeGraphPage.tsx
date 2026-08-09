import React from 'react';
import { Share2, ArrowRight } from 'lucide-react';
import { useDemo } from '../state/DemoContext';

export const KnowledgeGraphPage: React.FC = () => {
  const { graphNodes, selectedGraphNodeId, setSelectedGraphNodeId } = useDemo();

  const activeNode = graphNodes.find(n => n.id === selectedGraphNodeId) || graphNodes[1];

  return (
    <div className="space-y-6 font-sans">
      {/* Page Title Header */}
      <div className="flex items-center justify-between border-b border-[#1B2638] pb-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Share2 className="w-6 h-6 text-cyan-400" /> Knowledge Graph Ontology
          </h1>
          <p className="text-xs text-slate-400 font-medium mt-0.5">
            Enterprise entity-relationship mapping & Cypher query graph engine
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-[#101726] border border-[#233148] rounded-lg text-xs font-mono text-cyan-400">
            Dependency Layer: Neo4j Ready
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Canvas (2 Cols) matching Screenshot 2 */}
        <div className="lg:col-span-2 bg-[#0B0F19] border border-[#1E293B] rounded-xl p-5 shadow-2xl relative min-h-[500px] flex flex-col justify-between overflow-hidden">
          {/* Top Controls Bar matching Screenshot 2 */}
          <div className="flex items-center justify-between z-10">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-[#152033] border border-[#233148] text-[11px] font-mono text-cyan-400 rounded">
                center_on_filter_strong
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-[#152033] text-[10px] font-mono text-slate-300 rounded border border-slate-700">
                Dependency
              </span>
              <span className="px-2.5 py-1 bg-[#152033] text-[10px] font-mono text-slate-300 rounded border border-slate-700">
                Geospatial
              </span>
            </div>
          </div>

          {/* Canvas SVG Lines Overlay */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
            <defs>
              <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1E293B" strokeWidth="0.5" opacity="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />

            {/* Connecting SVG lines */}
            <line x1="25%" y1="35%" x2="52%" y2="52%" stroke="#38BDF8" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="52%" y1="52%" x2="80%" y2="35%" stroke="#10B981" strokeWidth="1.5" strokeDasharray="4 4" />
            <line x1="52%" y1="52%" x2="80%" y2="72%" stroke="#8B5CF6" strokeWidth="1.5" strokeDasharray="4 4" />
          </svg>

          {/* Node Cards Canvas Container */}
          <div className="relative z-10 w-full h-[400px]">
            {/* Customer Node */}
            <div
              onClick={() => setSelectedGraphNodeId('cust-1')}
              className="absolute top-[25%] left-[10%] cursor-pointer p-3 rounded-lg border border-cyan-500/40 bg-[#101726] shadow-xl w-52 hover:border-cyan-400 transition"
            >
              <div className="text-[9px] font-mono font-bold text-amber-400 uppercase tracking-wider">
                PERSON / CUSTOMER
              </div>
              <div className="font-bold text-xs text-white">Tata Steels Ltd</div>
              <div className="text-[10px] text-slate-400 font-mono">ID: CUST-8842</div>
              <div className="mt-2 text-[9px] font-mono px-2 py-0.5 bg-cyan-500/10 text-cyan-300 rounded border border-cyan-500/30 w-fit">
                PLACED BY
              </div>
            </div>

            {/* Order Node (Center Highlight matching Screenshot 2) */}
            <div
              onClick={() => setSelectedGraphNodeId('ord-1042')}
              className="absolute top-[42%] left-[42%] cursor-pointer p-3.5 rounded-lg border-2 border-rose-500 bg-[#161B29] shadow-2xl w-56 ring-2 ring-rose-500/30"
            >
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-mono font-bold text-rose-400 uppercase">receipt_long ORDER</span>
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
              </div>
              <div className="font-bold text-sm text-white mt-0.5">#ORD-1042</div>
              <div className="flex items-center justify-between text-[10px] font-mono mt-2 pt-2 border-t border-slate-700/50">
                <span className="text-rose-400 font-bold">Processing</span>
                <span className="text-slate-400">High Impact</span>
              </div>
            </div>

            {/* Product Node */}
            <div
              onClick={() => setSelectedGraphNodeId('prod-800')}
              className="absolute top-[25%] right-[5%] cursor-pointer p-3 rounded-lg border border-emerald-500/40 bg-[#101726] shadow-xl w-52 hover:border-emerald-400 transition"
            >
              <div className="text-[9px] font-mono font-bold text-emerald-400 uppercase tracking-wider">
                PRODUCT
              </div>
              <div className="font-bold text-xs text-white">WP-800 Water Pump</div>
              <div className="text-[10px] text-slate-400 font-mono">SKU-WP-800</div>
              <div className="mt-2 text-[9px] font-mono px-2 py-0.5 bg-emerald-500/10 text-emerald-300 rounded border border-emerald-500/30 w-fit">
                CONTAINS (120 UNITS)
              </div>
            </div>

            {/* Warehouse Node */}
            <div
              onClick={() => setSelectedGraphNodeId('wh-nagpur')}
              className="absolute bottom-[10%] right-[5%] cursor-pointer p-3 rounded-lg border border-purple-500/40 bg-[#101726] shadow-xl w-52 hover:border-purple-400 transition"
            >
              <div className="text-[9px] font-mono font-bold text-purple-400 uppercase tracking-wider">
                WAREHOUSE
              </div>
              <div className="font-bold text-xs text-white">Nagpur DC Hub</div>
              <div className="text-[10px] text-slate-400 font-mono">Central Hub</div>
              <div className="mt-2 text-[9px] font-mono px-2 py-0.5 bg-purple-500/10 text-purple-300 rounded border border-purple-500/30 w-fit">
                FULFILLING FROM
              </div>
            </div>
          </div>
        </div>

        {/* Right Detail Panel matching Screenshot 2 */}
        <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-2xl flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between border-b border-[#1E293B] pb-3">
              <div>
                <div className="text-[10px] text-cyan-400 font-mono font-bold uppercase tracking-wider">
                  ORDER ENTITY
                </div>
                <h3 className="text-xl font-extrabold text-white">{activeNode.label}</h3>
              </div>
              <span className="px-2 py-0.5 bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono rounded">
                CLOSE ENTITY
              </span>
            </div>

            <p className="text-xs text-slate-400 mt-2 font-mono">
              Critical path analysis required.
            </p>

            {/* Operational State Box matching Screenshot 2 */}
            <div className="my-4 space-y-1.5">
              <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider">
                OPERATIONAL STATE
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#090D16] p-3 rounded-lg border border-[#1E293B]">
                  <div className="text-[10px] text-slate-400 font-mono">Status</div>
                  <div className="text-sm font-bold text-amber-400 font-mono mt-0.5">
                    {activeNode.status || 'Active'}
                  </div>
                </div>
                <div className="bg-[#090D16] p-3 rounded-lg border border-[#1E293B]">
                  <div className="text-[10px] text-slate-400 font-mono">Impact Score</div>
                  <div className="text-sm font-bold text-white font-mono mt-0.5">
                    8.4 <span className="text-slate-500 text-xs">/10</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Attributes Table matching Screenshot 2 */}
            <div className="space-y-1 my-4">
              <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider mb-2">
                ATTRIBUTES
              </div>
              <div className="space-y-1.5 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-[#1E293B]">
                  <span className="text-slate-400">Date Created</span>
                  <span className="text-slate-200">2026-08-09 14:32Z</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1E293B]">
                  <span className="text-slate-400">Est. Delivery</span>
                  <span className="text-emerald-400 font-bold">2026-08-11</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1E293B]">
                  <span className="text-slate-400">Total Value</span>
                  <span className="text-slate-200 font-bold">₹8,50,000.00</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Priority Tier</span>
                  <span className="text-rose-400 font-bold">Critical</span>
                </div>
              </div>
            </div>

            {/* Direct Relationships matching Screenshot 2 */}
            <div className="space-y-2 my-4">
              <div className="text-[10px] text-slate-400 font-mono uppercase font-bold tracking-wider">
                DIRECT RELATIONSHIPS
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="p-2.5 bg-[#090D16] rounded-lg border border-[#1E293B] flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">Tata Steels Ltd</div>
                    <div className="text-[10px] text-slate-400 font-mono">Customer • Placed By</div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="p-2.5 bg-[#090D16] rounded-lg border border-[#1E293B] flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">WP-800 Water Pump</div>
                    <div className="text-[10px] text-slate-400 font-mono">Product • Contains (120)</div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="p-2.5 bg-[#090D16] rounded-lg border border-[#1E293B] flex items-center justify-between">
                  <div>
                    <div className="font-bold text-white">Nagpur DC Hub</div>
                    <div className="text-[10px] text-slate-400 font-mono">Warehouse • Fulfilling From</div>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Action Buttons matching Screenshot 2 */}
          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#1E293B]">
            <button className="py-2 px-3 bg-[#1A2538] hover:bg-[#22314A] text-slate-200 rounded-lg text-xs font-semibold text-center transition">
              View Details
            </button>
            <button className="py-2 px-3 bg-[#E0F8FF] hover:bg-white text-slate-900 font-bold rounded-lg text-xs text-center transition font-mono">
              Resolve Issue
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
