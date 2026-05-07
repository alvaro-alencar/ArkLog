import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cpu,
  ChevronDown,
  Plus,
  Clock,
  MessageSquare,
  Check,
  ArrowRight,
  Timer,
  X,
  RotateCw,
} from 'lucide-react';
import api from '../lib/api';
import { useNavigate } from 'react-router-dom';

const GitHubIcon = ({ size = 20, className = "" }: { size?: number, className?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
  </svg>
);

const ClickUpIcon = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2L2 12l2 2 8-8 8 8 2-2L12 2zM12 22l10-10-2-2-8 8-8-8-2 2 10 10z" />
  </svg>
);

const ArkLogLogo = ({ size = 48, className = "" }: { size?: number, className?: string }) => (
  <svg width={size} height={size} fill="none" viewBox="0 0 48 46" className={className}>
    <path fill="currentColor" d="M25.946 44.938c-.664.845-2.021.375-2.021-.698V33.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0-3.579 1.842-3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 44.94z" />
  </svg>
);

interface Repo {
  id: number;
  full_name: string;
}

interface ClickUpTeam {
  id: string;
  name: string;
}

interface ClickUpTask {
  id: string;
  name: string;
}

const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>('');
  const [destination, setDestination] = useState<string>('');

  const [clickupTeams, setClickupTeams] = useState<ClickUpTeam[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<string>('');
  const [clickupTasks, setClickupTasks] = useState<ClickUpTask[]>([]);
  const [selectedTask, setSelectedTask] = useState<string>('');
  const [isLoadingTasks, setIsLoadingTasks] = useState(false);

  const [promptStyle, setPromptStyle] = useState<'technical' | 'executive'>('technical');
  const [scheduleType, setScheduleType] = useState<'daily' | 'weekly'>('daily');
  const [scheduleTimes, setScheduleTimes] = useState<string[]>(['09:00']);
  const [timeInput, setTimeInput] = useState<string>('09:00');
  const [weeklyDay, setWeeklyDay] = useState<string>('friday');
  const [weeklyTime, setWeeklyTime] = useState<string>('18:00');
  const [windowHours, setWindowHours] = useState<number>(-1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    api.get('/github/repos')
      .then(res => setRepos(res.data))
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    if (destination === 'clickup') {
      api.get('/clickup/teams')
        .then(res => setClickupTeams(res.data))
        .catch(err => console.error(err));
    }
  }, [destination]);

  const fetchTasks = (teamId: string) => {
    setIsLoadingTasks(true);
    api.get(`/clickup/teams/${teamId}/tasks`)
      .then(res => setClickupTasks(res.data))
      .catch(err => console.error(err))
      .finally(() => setIsLoadingTasks(false));
  };

  useEffect(() => {
    if (selectedTeam) fetchTasks(selectedTeam);
  }, [selectedTeam]);

  const handleConnect = async () => {
    if (!selectedRepo || !selectedTask) return;

    setIsSubmitting(true);
    try {
      const repoName = selectedRepo.split('/').pop() || selectedRepo;
      await api.post('/projects', {
        name: `${repoName} - ${destination}`,
        repo_full_name: selectedRepo,
        report_style: promptStyle,
        reports: [
          {
            label: "Main Reports",
            clickup_task_id: selectedTask,
            schedule: scheduleType,
            times: scheduleType === 'daily' ? scheduleTimes : [],
            day: weeklyDay,
            time: weeklyTime,
            report_style: promptStyle,
            window_hours: windowHours,
          }
        ]
      });
      navigate('/');
    } catch (err) {
      console.error(err);
      alert('Failed to connect flow. Check console for details.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center py-12 px-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-purple-900/10 blur-[120px] rounded-full -z-20" />

      <div className="text-center mb-16">
        <motion.h2
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl font-extrabold tracking-tight text-white mb-4"
        >
          Connect your Flow
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="text-gray-400 max-w-md mx-auto"
        >
          Map your source code to intelligent delivery. Automate your progress reports with AI.
        </motion.p>
      </div>

      {/* Nodes */}
      <div className="relative flex items-center justify-between w-full max-w-5xl gap-8 px-4">
        {/* Connection Lines */}
        <div className="absolute top-1/2 left-[15%] right-[15%] h-[2px] -translate-y-1/2 -z-10">
          <div className="w-full h-full bg-gradient-to-r from-transparent via-purple-500/20 to-transparent relative">
             {selectedRepo && (
               <motion.div
                 initial={{ width: 0 }}
                 animate={{ width: '50%' }}
                 className="absolute left-0 top-0 h-full bg-gradient-to-r from-purple-500 to-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.5)]"
               />
             )}
             {selectedTask && (
               <motion.div
                 initial={{ width: 0 }}
                 animate={{ width: '50%' }}
                 className="absolute right-0 top-0 h-full bg-gradient-to-l from-purple-500 to-purple-400 shadow-[0_0_15px_rgba(168,85,247,0.5)]"
               />
             )}
          </div>
        </div>

        {/* Node 1: GitHub */}
        <div className="flex flex-col items-center gap-6 w-1/3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`w-24 h-24 rounded-3xl flex items-center justify-center border-2 transition-all duration-500 shadow-2xl relative group ${
              selectedRepo ? 'bg-white border-white text-black' : 'bg-[#0a0a0a] border-[#1f1f1f] text-gray-500'
            }`}
          >
            <GitHubIcon size={40} />
            {selectedRepo && (
              <div className="absolute -top-2 -right-2 bg-green-500 rounded-full p-1 text-white scale-110 shadow-lg">
                <Check size={14} strokeWidth={4} />
              </div>
            )}
          </motion.button>

          <div className="w-full max-w-[200px] relative group">
            <label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold mb-1 block text-center">Source</label>
            <div className="relative">
              <select
                className="w-full bg-black/50 backdrop-blur-md border border-[#1f1f1f] rounded-xl px-4 py-2.5 text-xs appearance-none focus:outline-none focus:border-purple-500 transition-all text-white pr-10 cursor-pointer"
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
              >
                <option value="">Select Repository</option>
                {repos.map(r => (
                  <option key={r.id} value={r.full_name}>{r.full_name}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-2.5 text-gray-500 pointer-events-none" size={16} />
            </div>
          </div>
        </div>

        {/* Node 2: ArkLog */}
        <div className="flex flex-col items-center gap-4 w-1/3">
          <motion.div
            animate={{
              boxShadow: ["0 0 10px rgba(168,85,247,0.1)", "0 0 25px rgba(168,85,247,0.3)", "0 0 10px rgba(168,85,247,0.1)"]
            }}
            transition={{ repeat: Infinity, duration: 4 }}
            className="w-32 h-32 rounded-full bg-black border-2 border-white/20 flex items-center justify-center relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-tr from-purple-600/20 to-transparent" />
            <ArkLogLogo size={64} className="text-white" />
          </motion.div>
          <p className="text-[10px] text-gray-600 font-medium uppercase tracking-widest">AI Engine</p>
        </div>

        {/* Node 3: Destination */}
        <div className="flex flex-col items-center gap-6 w-1/3">
          <motion.div
            className={`w-24 h-24 rounded-3xl flex items-center justify-center border-2 transition-all duration-500 shadow-2xl relative ${
              selectedTask
                ? 'bg-[#7b68ee] border-[#7b68ee] text-white'
                : destination
                  ? 'bg-black border-purple-500/50 text-purple-400'
                  : 'bg-[#0a0a0a] border-[#1f1f1f] text-gray-500'
            }`}
          >
            {destination === 'clickup' ? <ClickUpIcon size={40} /> : <Plus size={40} />}
            {selectedTask && (
              <div className="absolute -top-2 -right-2 bg-green-500 rounded-full p-1 text-white scale-110 shadow-lg">
                <Check size={14} strokeWidth={4} />
              </div>
            )}
          </motion.div>

          <div className="w-full max-w-[200px] space-y-2">
            <label className="text-[10px] uppercase tracking-widest text-gray-500 font-bold mb-1 block text-center">Destination</label>

            <div className="relative">
              <select
                className="w-full bg-black/50 backdrop-blur-md border border-[#1f1f1f] rounded-xl px-4 py-2.5 text-xs appearance-none focus:outline-none focus:border-purple-500 transition-all text-white pr-10 cursor-pointer"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
              >
                <option value="">Select Platform</option>
                <option value="clickup">ClickUp</option>
                <option value="slack" disabled>Slack (Soon)</option>
              </select>
              <ChevronDown className="absolute right-3 top-2.5 text-gray-500 pointer-events-none" size={16} />
            </div>

            <AnimatePresence>
              {destination === 'clickup' && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 5 }}
                  className="space-y-2"
                >
                  <div className="relative">
                    <select
                      className="w-full bg-black/30 border border-white/5 rounded-xl px-4 py-2.5 text-xs appearance-none text-white focus:border-purple-500/50 outline-none transition-all"
                      value={selectedTeam}
                      onChange={(e) => setSelectedTeam(e.target.value)}
                    >
                      <option value="">Select Workspace</option>
                      {clickupTeams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                    </select>
                  </div>

                  {selectedTeam && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-1.5">
                      <div className="relative flex-1">
                        <select
                          className="w-full bg-black/30 border border-white/5 rounded-xl px-4 py-2.5 text-xs appearance-none text-white focus:border-purple-500/50 outline-none transition-all"
                          value={selectedTask}
                          onChange={(e) => setSelectedTask(e.target.value)}
                        >
                          <option value="">Select Target Task</option>
                          {clickupTasks.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                        </select>
                      </div>
                      <button
                        onClick={() => fetchTasks(selectedTeam)}
                        disabled={isLoadingTasks}
                        title="Refresh tasks"
                        className="px-2.5 bg-black/30 border border-white/5 rounded-xl text-gray-500 hover:text-white hover:border-white/20 transition-all disabled:opacity-40"
                      >
                        <RotateCw size={13} className={isLoadingTasks ? 'animate-spin' : ''} />
                      </button>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* AI Engine Settings — always visible */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="w-full max-w-2xl mt-12"
      >
        <div className="glass-card p-6 space-y-5 border border-white/10">
          <h4 className="text-xs font-bold uppercase tracking-widest text-gray-400 flex items-center gap-2">
            <Cpu size={14} className="text-purple-400" /> AI Engine Settings
          </h4>

          <div className="grid grid-cols-2 gap-5">
            {/* Report Style */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Report Style</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setPromptStyle('technical')}
                  className={`py-2 rounded-lg text-[10px] font-bold transition-all border ${promptStyle === 'technical' ? 'bg-purple-500 border-purple-400 text-white' : 'bg-black border-white/5 text-gray-500 hover:border-white/20'}`}
                >Technical</button>
                <button
                  onClick={() => setPromptStyle('executive')}
                  className={`py-2 rounded-lg text-[10px] font-bold transition-all border ${promptStyle === 'executive' ? 'bg-purple-500 border-purple-400 text-white' : 'bg-black border-white/5 text-gray-500 hover:border-white/20'}`}
                >Executive</button>
              </div>
            </div>

            {/* Commit Window */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Commit Window</label>
              <div className="relative">
                <select
                  className="w-full bg-black border border-white/10 rounded-lg px-3 py-2 text-xs text-white appearance-none focus:outline-none focus:border-purple-500"
                  value={windowHours}
                  onChange={(e) => setWindowHours(Number(e.target.value))}
                >
                  <option value={-1}>All commits</option>
                  <option value={1}>Last 1 hour</option>
                  <option value={6}>Last 6 hours</option>
                  <option value={12}>Last 12 hours</option>
                  <option value={24}>Last 24 hours</option>
                  <option value={48}>Last 48 hours</option>
                  <option value={168}>Last 7 days</option>
                  <option value={720}>Last 30 days</option>
                </select>
                <Timer className="absolute right-2 top-2 text-gray-600 pointer-events-none" size={14} />
              </div>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Schedule Type</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setScheduleType('daily')}
                  className={`py-2 rounded-lg text-[10px] font-bold transition-all border ${scheduleType === 'daily' ? 'bg-purple-500 border-purple-400 text-white' : 'bg-black border-white/5 text-gray-500 hover:border-white/20'}`}
                >Daily</button>
                <button
                  onClick={() => setScheduleType('weekly')}
                  className={`py-2 rounded-lg text-[10px] font-bold transition-all border ${scheduleType === 'weekly' ? 'bg-purple-500 border-purple-400 text-white' : 'bg-black border-white/5 text-gray-500 hover:border-white/20'}`}
                >Weekly</button>
              </div>
            </div>

            {/* Times */}
            <div>
              {scheduleType === 'daily' ? (
                <>
                  <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Report Times</label>
                  <div className="flex gap-2">
                    <input
                      type="time"
                      value={timeInput}
                      onChange={(e) => setTimeInput(e.target.value)}
                      className="flex-1 bg-black border border-white/10 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                    />
                    <button
                      onClick={() => {
                        if (timeInput && !scheduleTimes.includes(timeInput)) {
                          setScheduleTimes([...scheduleTimes, timeInput].sort());
                        }
                      }}
                      className="px-3 py-1.5 bg-purple-500 text-white rounded-lg text-xs font-bold hover:bg-purple-400 transition-all"
                    >Add</button>
                  </div>
                  {scheduleTimes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {scheduleTimes.map(t => (
                        <span key={t} className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-full px-2 py-0.5 text-[10px] text-gray-300">
                          <Clock size={9} />{t}
                          <button onClick={() => setScheduleTimes(scheduleTimes.filter(x => x !== t))} className="text-gray-500 hover:text-red-400 transition-colors ml-0.5">
                            <X size={9} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Day & Time</label>
                  <div className="space-y-2">
                    <div className="relative">
                      <select
                        className="w-full bg-black border border-white/10 rounded-lg px-3 py-2 text-xs text-white appearance-none focus:outline-none focus:border-purple-500"
                        value={weeklyDay}
                        onChange={(e) => setWeeklyDay(e.target.value)}
                      >
                        <option value="monday">Monday</option>
                        <option value="tuesday">Tuesday</option>
                        <option value="wednesday">Wednesday</option>
                        <option value="thursday">Thursday</option>
                        <option value="friday">Friday</option>
                        <option value="saturday">Saturday</option>
                        <option value="sunday">Sunday</option>
                      </select>
                      <ChevronDown className="absolute right-2 top-2 text-gray-600 pointer-events-none" size={14} />
                    </div>
                    <input
                      type="time"
                      value={weeklyTime}
                      onChange={(e) => setWeeklyTime(e.target.value)}
                      className="w-full bg-black border border-white/10 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Live summary */}
          <div className="flex gap-2 pt-1 border-t border-white/5">
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-full px-2 py-0.5 flex items-center gap-1.5 text-[9px] text-purple-400 font-bold uppercase tracking-tighter">
              <Clock size={10} />
              {scheduleType === 'daily'
                ? (scheduleTimes.length ? scheduleTimes.join(', ') : '—')
                : `${weeklyDay.slice(0, 3)} ${weeklyTime}`}
            </div>
            <div className="bg-white/5 border border-white/10 rounded-full px-2 py-0.5 flex items-center gap-1.5 text-[9px] text-gray-400 font-bold uppercase tracking-tighter">
              <Timer size={10} />
              {windowHours === -1 ? 'all' : windowHours < 24 ? `${windowHours}h` : windowHours === 168 ? '7d' : windowHours === 720 ? '30d' : `${windowHours}h`}
            </div>
            <div className="bg-white/5 border border-white/10 rounded-full px-2 py-0.5 flex items-center gap-1.5 text-[9px] text-gray-400 font-bold uppercase tracking-tighter">
              <MessageSquare size={10} /> {promptStyle}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Connect button */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="mt-12"
      >
        <motion.button
          disabled={!selectedRepo || !selectedTask || isSubmitting}
          onClick={handleConnect}
          whileHover={{ scale: 1.05, boxShadow: "0 0 20px rgba(168,85,247,0.4)" }}
          whileTap={{ scale: 0.95 }}
          className={`px-16 py-4 rounded-2xl font-black text-xl transition-all flex items-center gap-3 ${
            selectedRepo && selectedTask
            ? 'bg-gradient-to-r from-purple-500 to-purple-400 text-white shadow-xl'
            : 'bg-[#111] text-gray-600 border border-[#222] cursor-not-allowed opacity-50'
          }`}
        >
          {isSubmitting ? (
            <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              CONNECT FLOW <ArrowRight size={24} strokeWidth={3} />
            </>
          )}
        </motion.button>

        {(!selectedRepo || !selectedTask) && (
          <p className="text-center mt-4 text-[10px] text-gray-500 font-bold uppercase tracking-widest">
            Complete the connections above to start
          </p>
        )}
      </motion.div>

      {/* Connection info footer */}
      {selectedRepo && selectedTask && !isSubmitting && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-8 flex items-center gap-8 text-[11px] font-bold text-gray-500 uppercase tracking-tighter"
        >
          <div className="flex items-center gap-1.5 bg-black/50 px-3 py-1.5 rounded-full border border-white/5">
            <GitHubIcon size={14} className="text-white" /> {selectedRepo}
          </div>
          <ArrowRight size={14} className="text-purple-500" />
          <div className="flex items-center gap-1.5 bg-black/50 px-3 py-1.5 rounded-full border border-white/5">
            <ClickUpIcon size={14} className="text-purple-400" /> Task Connected
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default NewProject;
