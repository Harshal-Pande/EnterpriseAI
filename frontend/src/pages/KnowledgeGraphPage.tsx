import React from 'react';
import { Share2, Database, Code } from 'lucide-react';
import { useDemo } from '../state/DemoContext';
import type { GraphNode } from '../types';

export const KnowledgeGraphPage: React.FC = () => {
  const { graphNodes, selectedGraphNodeId, setSelectedGraphNodeId } = useDemo();

  const activeNode = graphNodes.find(n => n.id === selectedGraphNodeId) || graphNodes[1];

  const getNodeColor = (type: GraphNode['type']) => {
    switch (type) {
      case 'Customer': return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:border-cyan-400';
      case 'Order': return 'bg-blue-500/20 text-blue-300 border-blue-500/40 hover:border-blue-400';
      case 'Product': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 hover:border-emerald-400';
      case 'Supplier': return 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:border-amber-400';
      case 'Warehouse': return 'bg-purple-500/20 text-purple-300 border-purple-500/40 hover:border-purple-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Share2 className="w-5 h-5 text-cyan-400" /> Neo4j Knowledge Graph & Entity Ontology
          </h2>
          <p className="text-xs text-slate-400">
            Semantic entity relationship mapping for order contextualization & RAG indexing
          </p>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 flex items-center gap-1.5">
            <Database className="w-3.5 h-3.5" /> Neo4j Cypher Engine Ready
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Graph Canvas */}
        <div className="lg:col-span-2 bg-[#121929] border border-[#24334D] rounded-2xl p-6 shadow-xl relative min-h-[460px] flex flex-col justify-between overflow-hidden">
          {/* SVG Background Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
            {/* Customer (100, 150) -> Order (300, 150) */}
            <line x1="180" y1="150" x2="300" y2="150" stroke="#38BDF8" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
            {/* Order (300, 150) -> Product (500, 100) */}
            <line x1="380" y1="150" x2="500" y2="100" stroke="#38BDF8" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
            {/* Product (500, 100) -> Supplier (700, 100) */}
            <line x1="580" y1="100" x2="700" y2="100" stroke="#F59E0B" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
            {/* Order (300, 150) -> Warehouse (500, 250) */}
            <line x1="380" y1="150" x2="500" y2="250" stroke="#8B5CF6" strokeWidth="2" strokeDasharray="4 4" className="animate-pulse" />
          </svg>

          {/* Canvas Nodes */}
          <div className="relative z-10 w-full h-[360px]">
            {graphNodes.map((node) => {
              const isSelected = selectedGraphNodeId === node.id;
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedGraphNodeId(node.id)}
                  style={{ left: `${(node.x / 800) * 100}%`, top: `${(node.y / 320) * 100}%` }}
                  className={`absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer p-3 rounded-xl border transition-all duration-200 shadow-xl flex flex-col items-center justify-center text-center w-36 ${getNodeColor(
                    node.type
                  )} ${isSelected ? 'ring-4 ring-cyan-500/40 scale-105 bg-[#17233B]' : ''}`}
                >
                  <div className="text-[10px] font-mono uppercase tracking-wider font-bold opacity-80 mb-0.5">
                    {node.type}
                  </div>
                  <div className="font-bold text-xs text-white truncate max-w-[130px]">
                    {node.label}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="z-10 bg-[#0B111E] p-2.5 rounded-xl border border-[#1E293B] flex items-center justify-between text-xs">
            <span className="text-slate-400">Interactive Entity Explorer</span>
            <span className="text-cyan-400 font-mono text-[11px]">Click any node to view entity attributes</span>
          </div>
        </div>

        {/* Right Column (1 Col): Node Inspector & Cypher Code preview */}
        <div className="space-y-6">
          <div className="bg-[#121929] border border-[#24334D] rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#24334D] pb-3">
              <div>
                <span className="text-[10px] text-cyan-400 font-mono font-bold uppercase tracking-wider">
                  Entity Inspector
                </span>
                <h3 className="font-bold text-base text-white">{activeNode.label}</h3>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                {activeNode.type}
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mb-1">
                Node Properties & Metadata
              </div>
              {Object.entries(activeNode.details).map(([key, val]) => (
                <div key={key} className="flex justify-between p-2 bg-[#0A0F1D] rounded border border-slate-800 font-mono">
                  <span className="text-slate-400">{key}:</span>
                  <span className="text-slate-200 font-semibold">{val}</span>
                </div>
              ))}
            </div>

            {/* Simulated Neo4j Cypher query for future binding */}
            <div className="space-y-2 pt-2 border-t border-[#24334D]">
              <div className="text-[10px] text-indigo-300 font-mono font-semibold uppercase tracking-wider flex items-center gap-1">
                <Code className="w-3.5 h-3.5 text-indigo-400" /> Future Neo4j Cypher Pattern
              </div>
              <div className="p-3 bg-[#080C14] rounded-lg border border-slate-800 font-mono text-[11px] text-cyan-400 leading-relaxed overflow-x-auto">
                MATCH (c:Customer &#123;id: '{activeNode.id}'&#125;)<br />
                -[:PLACED]-&gt;(o:Order)<br />
                -[:CONTAINS]-&gt;(p:Product)<br />
                RETURN c, o, p LIMIT 10
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
