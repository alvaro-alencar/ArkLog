import React, { useEffect, useState } from 'react';
import { ExternalLink, GitBranch, Calendar, Plus, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../lib/api';

interface Project {
  id: number;
  name: string;
  repo_full_name: string;
  description: string;
  created_at: string;
}

const WINDOW_OPTIONS = [
  { value: 1, label: 'Last 1 hour' },
  { value: 6, label: 'Last 6 hours' },
  { value: 12, label: 'Last 12 hours' },
  { value: 24, label: 'Last 24 hours' },
  { value: 48, label: 'Last 48 hours' },
  { value: 168, label: 'Last 7 days' },
  { value: 720, label: 'Last 30 days' },
  { value: -1, label: 'All commits' },
];

const Dashboard: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [instantProjectId, setInstantProjectId] = useState<number | null>(null);
  const [instantWindowHours, setInstantWindowHours] = useState<number>(24);
  const [isGenerating, setIsGenerating] = useState(false);
  const [instantResult, setInstantResult] = useState<{ projectId: number; commits: number } | null>(null);

  useEffect(() => {
    api.get('/projects')
      .then(response => {
        setProjects(response.data.projects);
      })
      .catch(error => console.error('Error fetching projects', error))
      .finally(() => setIsLoading(false));
  }, []);

  const triggerInstantReport = async (projectId: number) => {
    setIsGenerating(true);
    setInstantResult(null);
    try {
      const res = await api.post(`/projects/${projectId}/instant-report`, { window_hours: instantWindowHours });
      setInstantResult({ projectId, commits: res.data.commit_count });
      setInstantProjectId(null);
    } catch (err) {
      console.error(err);
      alert('Failed to trigger report. Check console for details.');
    } finally {
      setIsGenerating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Your Projects</h2>
          <p className="text-gray-400 mt-1">Manage and monitor your tracked repositories.</p>
        </div>
        <Link
          to="/new"
          className="flex items-center gap-2 bg-white text-black px-4 py-2 rounded-md font-medium hover:bg-gray-200 transition-colors"
        >
          <Plus size={18} />
          New Project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="glass-card p-12 text-center space-y-4">
          <p className="text-gray-400">No projects found. Create your first flow to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {projects.map(project => (
            <div key={project.id} className="glass-card p-6 space-y-4 group">
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <h3 className="text-xl font-semibold group-hover:text-gray-300 transition-colors">
                    {project.name}
                  </h3>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <GitBranch size={14} />
                    {project.repo_full_name}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setInstantResult(null);
                      setInstantProjectId(instantProjectId === project.id ? null : project.id);
                    }}
                    title="Run instant report"
                    className={`transition-colors ${instantProjectId === project.id ? 'text-yellow-400' : 'text-gray-500 hover:text-yellow-400'}`}
                  >
                    <Zap size={16} />
                  </button>
                  <a
                    href={`https://github.com/${project.repo_full_name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-500 hover:text-white transition-colors"
                  >
                    <ExternalLink size={18} />
                  </a>
                </div>
              </div>

              <p className="text-sm text-gray-400 line-clamp-2 min-h-[2.5rem]">
                {project.description || 'No description provided.'}
              </p>

              {/* Instant report panel */}
              {instantProjectId === project.id && (
                <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-lg p-3 space-y-2">
                  <p className="text-[10px] text-yellow-400 font-bold uppercase tracking-widest">Instant Report</p>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 bg-black/60 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-yellow-500/50"
                      value={instantWindowHours}
                      onChange={(e) => setInstantWindowHours(Number(e.target.value))}
                    >
                      {WINDOW_OPTIONS.map(o => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => triggerInstantReport(project.id)}
                      disabled={isGenerating}
                      className="px-3 py-1.5 bg-yellow-500/20 border border-yellow-500/30 text-yellow-400 rounded-lg text-xs font-bold hover:bg-yellow-500/30 transition-all flex items-center gap-1.5 disabled:opacity-50"
                    >
                      {isGenerating
                        ? <div className="w-3 h-3 border border-yellow-400/50 border-t-yellow-400 rounded-full animate-spin" />
                        : <Zap size={12} />}
                      Run
                    </button>
                  </div>
                </div>
              )}

              {/* Success feedback */}
              {instantResult?.projectId === project.id && (
                <div className="border border-green-500/20 bg-green-500/5 rounded-lg px-3 py-2 text-[10px] text-green-400 font-bold">
                  Report queued — {instantResult.commits} commit{instantResult.commits !== 1 ? 's' : ''} being processed.
                </div>
              )}

              <div className="flex items-center justify-between pt-4 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <Calendar size={12} />
                  Added {new Date(project.created_at).toLocaleDateString()}
                </div>
                <button className="text-xs font-medium px-3 py-1 bg-white text-black rounded hover:bg-gray-200 transition-colors">
                  View Reports
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
