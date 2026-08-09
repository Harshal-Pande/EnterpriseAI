import React from 'react';
import { TrendingDown, Download } from 'lucide-react';
import { ExceptionsPage } from './ExceptionsPage';

export const BenchmarksPage: React.FC = () => {
  return (
    <div className="space-y-6 font-sans">
      {/* Page Title Header matching Screenshot 1 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1B2638] pb-5">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Benchmarks & Exceptions
          </h1>
          <p className="text-sm text-slate-400 font-medium mt-1">
            Comparative analysis and real-time stress testing simulator.
          </p>
        </div>

        <button className="px-4 py-2 bg-[#162035] hover:bg-[#1E2C4A] text-slate-200 font-semibold rounded-lg text-xs border border-[#233148] shadow transition flex items-center gap-2 font-mono shrink-0 self-start md:self-auto">
          <Download className="w-3.5 h-3.5" /> Export Report
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Latency vs Throughput Chart & Efficiency Metrics matching Screenshot 1 */}
        <div className="lg:col-span-2 space-y-6">
          {/* Chart Card */}
          <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white tracking-tight">
                Latency vs. Throughput
              </h2>
              <div className="flex items-center gap-4 text-xs font-mono">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 bg-[#2D3A52] rounded-sm"></span>
                  <span className="text-slate-400">Deterministic Pipeline</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 bg-[#B0DEDE] rounded-sm"></span>
                  <span className="text-slate-200">Enterprise AI Mesh</span>
                </div>
              </div>
            </div>

            {/* Custom SVG Bar Chart Simulation matching Screenshot 1 */}
            <div className="relative h-64 border-b border-l border-slate-700/60 pt-4 pb-6 px-4 flex items-end justify-around font-mono text-xs text-slate-400">
              <div className="absolute top-2 left-1 text-[10px] text-slate-500">100ms</div>
              <div className="absolute top-1/2 left-1 text-[10px] text-slate-500">50ms</div>
              <div className="absolute bottom-6 left-1 text-[10px] text-slate-500">0</div>

              {/* Group 1: Query Resolution */}
              <div className="flex flex-col items-center gap-2 h-full justify-end">
                <div className="flex items-end gap-2 h-44">
                  <div className="w-12 bg-[#2B384E] rounded-t h-32" title="Legacy: 75ms"></div>
                  <div className="w-12 bg-[#B0DEDE] rounded-t h-12" title="AI Mesh: 22ms"></div>
                </div>
                <span className="text-[11px] text-slate-300">Query Resolution</span>
              </div>

              {/* Group 2: Data Aggregation */}
              <div className="flex flex-col items-center gap-2 h-full justify-end">
                <div className="flex items-end gap-2 h-44">
                  <div className="w-12 bg-[#2B384E] rounded-t h-40" title="Legacy: 95ms"></div>
                  <div className="w-12 bg-[#B0DEDE] rounded-t h-16" title="AI Mesh: 38ms"></div>
                </div>
                <span className="text-[11px] text-slate-300">Data Aggregation</span>
              </div>

              {/* Group 3: Decision Engine */}
              <div className="flex flex-col items-center gap-2 h-full justify-end">
                <div className="flex items-end gap-2 h-44">
                  <div className="w-12 bg-[#2B384E] rounded-t h-28" title="Legacy: 60ms"></div>
                  <div className="w-12 bg-[#B0DEDE] rounded-t h-8" title="AI Mesh: 14ms"></div>
                </div>
                <span className="text-[11px] text-slate-300">Decision Engine</span>
              </div>
            </div>
          </div>

          {/* Efficiency Metric Cards matching Screenshot 1 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Card 1: MTTR */}
            <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl space-y-3">
              <div className="text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
                MEAN TIME TO RECOVERY (MTTR)
              </div>
              <div className="flex items-baseline gap-3">
                <div className="text-4xl font-extrabold text-white font-mono">1.2s</div>
                <div className="text-xs font-mono text-emerald-400 font-bold flex items-center">
                  <TrendingDown className="w-3.5 h-3.5 mr-0.5" /> 94% improvement
                </div>
              </div>
              <div className="space-y-1 pt-2">
                <div className="w-full h-2 bg-[#1B2638] rounded-full overflow-hidden flex">
                  <div className="w-[15%] bg-[#B0DEDE] h-full"></div>
                  <div className="w-[85%] bg-[#2B384E] h-full opacity-40"></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>AI Mesh: 1.2s</span>
                  <span>Legacy: 24.5s</span>
                </div>
              </div>
            </div>

            {/* Card 2: Compute Efficiency */}
            <div className="bg-[#111827] border border-[#1E293B] rounded-xl p-5 shadow-xl space-y-3">
              <div className="text-[10px] text-slate-400 font-mono font-bold uppercase tracking-wider">
                COMPUTE EFFICIENCY
              </div>
              <div className="flex items-baseline gap-3">
                <div className="text-4xl font-extrabold text-white font-mono">42%</div>
                <div className="text-xs font-mono text-emerald-400 font-bold flex items-center">
                  <TrendingDown className="w-3.5 h-3.5 mr-0.5" /> Less Overhead
                </div>
              </div>
              <div className="space-y-1 pt-2">
                <div className="grid grid-cols-3 gap-1 h-3">
                  <div className="bg-[#B0DEDE] rounded-sm"></div>
                  <div className="bg-[#789BB0] rounded-sm"></div>
                  <div className="bg-[#1B2638] rounded-sm"></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                  <span>• Mesh Core</span>
                  <span>• Agents</span>
                  <span>• Idle</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Exception Simulators Stack matching Screenshot 1 */}
        <div className="lg:col-span-1">
          <ExceptionsPage />
        </div>
      </div>
    </div>
  );
};
