import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Zap, Clock, GitCommit, ChevronDown, ChevronUp, Filter, X } from 'lucide-react';
import api from '../lib/api';

interface ReportSummary {
  id: number;
  project_id: number;
  project_name: string;
  trigger: string;
  status: string;
  summary: string;
  commit_count: number;
  generated_at: string;
}

interface ReportDetail extends ReportSummary {
  content: string;
}

interface Project { id: number; name: string; }

const TRIGGER_LABEL: Record<string, string> = {
  instant: 'Instant',
  daily_scheduled: 'Scheduled',
  weekly_scheduled: 'Scheduled',
  webhook: 'Webhook',
};

const TRIGGER_COLOR: Record<string, string> = {
  instant: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  daily_scheduled: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  weekly_scheduled: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  webhook: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
};

const ReportCard: React.FC<{ report: ReportSummary }> = ({ report }) => {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const handleExpand = async () => {
    if (!expanded && !detail) {
      setLoading(true);
      try {
        const res = await api.get(`/reports/${report.id}`);
        setDetail(res.data);
      } catch {
        setDetail({ ...report, content: 'Failed to load report content.' });
      } finally {
        setLoading(false);
      }
    }
    setExpanded(v => !v);
  };

  const lines = report.summary?.split('\n').filter(Boolean) ?? [];
  const preview = lines.slice(0, 3).join(' · ').replace(/^#+\s*/gm, '').slice(0, 160);

  return (
    <motion.div
      layout
      className="glass-card overflow-hidden border border-white/5 hover:border-white/10 transition-colors"
    >
      <div
        className="p-5 cursor-pointer select-none"
        onClick={handleExpand}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${TRIGGER_COLOR[report.trigger] ?? 'text-gray-400 bg-white/5 border-white/10'}`}>
                {TRIGGER_LABEL[report.trigger] ?? report.trigger}
              </span>
              <span className="text-[10px] text-gray-600 font-medium">{report.project_name}</span>
            </div>

            <p className="text-sm text-gray-300 line-clamp-2">
              {preview || 'No summary available.'}
            </p>

            <div className="flex items-center gap-4 text-[11px] text-gray-600">
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {new Date(report.generated_at).toLocaleString()}
              </span>
              {report.commit_count > 0 && (
                <span className="flex items-center gap-1">
                  <GitCommit size={11} />
                  {report.commit_count} commit{report.commit_count !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>

          <button className="text-gray-600 hover:text-gray-300 transition-colors mt-1 shrink-0">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/5 p-5 bg-black/30">
              {loading ? (
                <div className="flex justify-center py-6">
                  <div className="w-5 h-5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                  {detail?.content ?? ''}
                </pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const Reports: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const projectFilter = searchParams.get('project') ? Number(searchParams.get('project')) : null;

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const limit = 10;

  const load = useCallback(async (pid: number | null, p: number) => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { limit, offset: p * limit };
      if (pid) params.project_id = pid;
      const res = await api.get('/reports', { params });
      setReports(res.data.reports);
      setTotal(res.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.get('/projects').then(r => setProjects(r.data.projects ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    setPage(0);
    load(projectFilter, 0);
  }, [projectFilter, load]);

  const handleProjectFilter = (id: number | null) => {
    setPage(0);
    if (id) setSearchParams({ project: String(id) });
    else setSearchParams({});
  };

  const handlePage = (p: number) => {
    setPage(p);
    load(projectFilter, p);
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">All Reports</h2>
          <p className="text-gray-400 mt-1">{total} report{total !== 1 ? 's' : ''} generated.</p>
        </div>

        {/* Project filter */}
        <div className="flex items-center gap-2">
          {projectFilter && (
            <button
              onClick={() => handleProjectFilter(null)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-white border border-white/10 px-2.5 py-1.5 rounded-lg transition-colors"
            >
              <X size={12} /> Clear filter
            </button>
          )}
          <div className="relative">
            <select
              className="appearance-none bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500 pr-7"
              value={projectFilter ?? ''}
              onChange={e => handleProjectFilter(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">All projects</option>
              {projects.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <Filter size={11} className="absolute right-2.5 top-2.5 text-gray-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : reports.length === 0 ? (
        <div className="glass-card p-14 text-center space-y-3">
          <FileText size={32} className="text-gray-700 mx-auto" />
          <p className="text-gray-500 text-sm">No reports yet. Run an instant report or wait for a scheduled one.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map(r => <ReportCard key={r.id} report={r} />)}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center gap-2 pt-2">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              onClick={() => handlePage(i)}
              className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
                i === page ? 'bg-white text-black' : 'bg-white/5 text-gray-400 hover:bg-white/10'
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default Reports;
