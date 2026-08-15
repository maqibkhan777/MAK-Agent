import React, { useState, useEffect, useRef } from 'react';
import {
  BrainCircuit,
  Brain,
  Megaphone,
  Target,
  Globe,
  Landmark,
  Code2,
  Video,
  GraduationCap,
  Send,
  Paperclip,
  RotateCcw,
  Bot,
  User,
  Copy,
  Check,
  Server,
  Activity,
  AlertCircle,
  Clock,
  Terminal,
  Zap,
  Layers,
  ChevronRight,
  Sparkles,
  Volume2,
  VolumeX,
  Play,
  Pause,
  Square,
  Key,
  ShieldCheck,
  Cpu,
  Calendar,
  CalendarPlus,
  PlayCircle,
  Trash2,
  UploadCloud,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
  X,
  Settings,
  Sliders,
  Database,
  RefreshCw,
  ExternalLink,
  Link2
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

const MAK_DEPARTMENTS = [
  {
    id: 'triage',
    name: 'Chief of Staff',
    role: 'Triage & Clarification Engine',
    activeSubtext: 'Consulting Knowledge & Clarifying...',
    icon: BrainCircuit,
    color: 'from-cyan-500 to-blue-600',
    prompt: 'Review current enterprise objectives, clarify requirements, and route tasks to specialized departments.'
  },
  {
    id: 'general_ops',
    name: 'General Ops & Research',
    role: 'Live Web Search & Browsing',
    activeSubtext: 'Browsing & Scraping Live Internet...',
    icon: Globe,
    color: 'from-emerald-400 to-teal-500',
    prompt: 'Search the live web for the latest advancements and architecture benchmarks in autonomous AI agent systems.'
  },
  {
    id: 'marketing',
    name: 'Marketing Studio',
    role: 'SEO & Growth Campaigns',
    activeSubtext: 'Synthesizing Market Intelligence...',
    icon: Megaphone,
    color: 'from-pink-500 to-rose-600',
    prompt: 'Analyze competitor market positioning and formulate a high-converting 30-day organic growth strategy.'
  },
  {
    id: 'sales',
    name: 'Sales Desk',
    role: 'B2B Lead Outreach & Cold Email',
    activeSubtext: 'Prospecting & Drafting Sequences...',
    icon: Target,
    color: 'from-blue-500 to-indigo-600',
    prompt: 'Draft a high-converting personalized cold outreach sequence targeting enterprise VP of Engineering prospects.'
  },
  {
    id: 'engineering',
    name: 'Software Engineering',
    role: 'Code Synthesis & Architecture',
    activeSubtext: 'Writing & Auditing Source Code...',
    icon: Code2,
    color: 'from-amber-500 to-orange-600',
    prompt: 'Design and implement a thread-safe distributed cache in Python with LRU eviction and TTL expiration.'
  },
  {
    id: 'finance',
    name: 'Corporate Finance',
    role: 'DCF, M&A & Valuation Models',
    activeSubtext: 'Calculating Financial Models...',
    icon: Landmark,
    color: 'from-green-500 to-emerald-600',
    prompt: 'Conduct a discounted cash flow valuation for a project with $5M initial outlay and $1.5M annual cash flows for 5 years at 10% discount rate.'
  },
  {
    id: 'content',
    name: 'Content House',
    role: 'Omnichannel Media & Scripts',
    activeSubtext: 'Drafting Scripts & Social Copy...',
    icon: Video,
    color: 'from-purple-500 to-violet-600',
    prompt: 'Write an engaging educational video script breaking down how multi-agent LLM graphs work for technical leaders.'
  },
  {
    id: 'research',
    name: 'Academic Research',
    role: 'ArXiv & Peer-Review Scraper',
    activeSubtext: 'Querying ArXiv & Synthesizing Papers...',
    icon: GraduationCap,
    color: 'from-sky-500 to-indigo-600',
    prompt: 'Scrape ArXiv for the newest research papers on test-time compute scaling and summarize key breakthroughs.'
  }
];

// Helper: Parse inline markdown tokens (links, bold, italic, code, URLs)
function renderInlineMarkdown(text) {
  if (!text) return '';

  // Regex pattern matching [Link Text](url), bare URLs, `code`, **bold**, *italic*
  const pattern = /(!?\[(?:[^\]]+)\]\((?:[^)]+)\)|https?:\/\/[^\s<>)"]+|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const tokens = text.split(pattern);

  return tokens.map((token, i) => {
    if (!token) return null;

    // 1. Markdown Links [Text](url)
    const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      const [, linkText, url] = linkMatch;
      return (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 underline underline-offset-2 hover:decoration-cyan-400 font-medium transition-colors mx-0.5"
        >
          <ExternalLink className="w-3 h-3 inline text-cyan-400 shrink-0" />
          <span>{linkText}</span>
        </a>
      );
    }

    // 2. Bare URLs http:// or https://
    if (token.startsWith('http://') || token.startsWith('https://')) {
      const cleanUrl = token.replace(/[.,;)]+$/, '');
      return (
        <a
          key={i}
          href={cleanUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 underline underline-offset-2 font-mono text-xs transition-colors mx-0.5"
        >
          <Link2 className="w-3 h-3 inline text-cyan-400 shrink-0" />
          <span>{cleanUrl.length > 40 ? cleanUrl.slice(0, 37) + '...' : cleanUrl}</span>
        </a>
      );
    }

    // 3. Inline Code `code`
    if (token.startsWith('`') && token.endsWith('`') && token.length > 2) {
      return (
        <code
          key={i}
          className="px-1.5 py-0.5 rounded bg-slate-900/90 border border-cyan-500/20 text-cyan-300 font-mono text-xs mx-0.5"
        >
          {token.slice(1, -1)}
        </code>
      );
    }

    // 4. Bold Text **text**
    if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
      return (
        <strong key={i} className="text-white font-semibold">
          {token.slice(2, -2)}
        </strong>
      );
    }

    // 5. Italic Text *text*
    if (token.startsWith('*') && token.endsWith('*') && token.length > 2) {
      return (
        <em key={i} className="text-slate-200 italic">
          {token.slice(1, -1)}
        </em>
      );
    }

    // Regular plain text
    return <span key={i}>{token}</span>;
  });
}

// Helper: Check and render Markdown Tables (| col1 | col2 |)
function renderMarkdownTable(block, key) {
  const lines = block.trim().split('\n').filter(l => l.includes('|'));
  if (lines.length < 2) return null;

  const headerLine = lines[0];
  const headers = headerLine.split('|').map(h => h.trim()).filter(Boolean);
  const dataLines = lines.slice(1).filter(l => !l.includes('---'));

  return (
    <div key={key} className="my-4 overflow-x-auto rounded-xl border border-cyan-500/20 bg-slate-950/80 shadow-lg">
      <table className="w-full text-left text-xs font-mono border-collapse">
        <thead>
          <tr className="bg-slate-900/90 border-b border-cyan-500/30 text-cyan-300">
            {headers.map((h, hIdx) => (
              <th key={hIdx} className="p-3 font-bold tracking-wider uppercase text-[11px]">
                {renderInlineMarkdown(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {dataLines.map((row, rIdx) => {
            const cells = row.split('|').map(c => c.trim()).filter(Boolean);
            return (
              <tr key={rIdx} className="hover:bg-slate-900/50 transition-colors">
                {cells.map((cell, cIdx) => (
                  <td key={cIdx} className="p-3 text-slate-300">
                    {renderInlineMarkdown(cell)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Helper: Extract clickable choices / options (Option A / Option B / 1 / 2) from assistant responses
function extractOptionsFromMessage(content) {
  if (!content || typeof content !== 'string') return [];
  const options = [];
  const lines = content.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();
    // 1. Matches "Option A: ...", "**Option A**: ...", "A) ...", "A. ..."
    let optMatch = trimmed.match(/^(?:[-*]\s*)?(?:\*\*)?(?:Option\s+([A-D0-9])|([A-D0-9])[\.\)])(?:\*\*)?[:\s-]+(.+)$/i);
    if (!optMatch) {
      // 2. Matches "1. **...**: ...", "1) ..."
      optMatch = trimmed.match(/^(?:[-*]\s*)?(\d+)[\.\)]\s+(?:\*\*)?(.+?)(?:\*\*)?$/);
    }

    if (optMatch) {
      const optId = (optMatch[1] || optMatch[2] || '').trim().toUpperCase();
      const rawText = (optMatch[3] || optMatch[2] || '').trim();
      const cleanText = rawText.replace(/^\*\*/, '').replace(/\*\*$/, '').replace(/^["']/, '').replace(/["']$/, '').trim();

      if (optId && cleanText && cleanText.length > 2 && cleanText.length < 140 && !options.some(o => o.id === optId)) {
        options.push({
          id: optId,
          label: `Option ${optId}`,
          text: cleanText,
          fullPrompt: `Option ${optId}: ${cleanText}`
        });
      }
    }
  }

  return options.slice(0, 4);
}

export default function App() {
  // Session ID Management for Multi-Turn Continuity
  const [sessionId, setSessionId] = useState(() => {
    try {
      return localStorage.getItem('mak_session_id') || `session-${Date.now()}`;
    } catch {
      return `session-${Date.now()}`;
    }
  });

  // Chat & Agency State
  const [messages, setMessages] = useState([
    {
      id: 'init-1',
      role: 'assistant',
      department: 'Chief of Staff',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      content: "### MAK Autonomous Cognitive Core Online 🟢\n\nI am **MAK**, your autonomous multi-department cognitive orchestrator with persistent session memory. I clarify requirements, dispatch specialized autonomous crews, perform live internet intelligence, execute financial valuations, and schedule recurring tasks.\n\n* **Clarify & Direct**: Ask me any question or assign a complex enterprise directive.\n* **Live Web Intelligence**: Request live search, website scraping, or competitor monitoring.\n* **Multi-Turn Context**: All follow-up questions, options (A/B), and commands retain full memory context.",
      status: 'idle'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeDepartment, setActiveDepartment] = useState('triage');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [copiedCodeId, setCopiedCodeId] = useState(null);
  const [executionStartTime, setExecutionStartTime] = useState(null);
  const [executionDuration, setExecutionDuration] = useState(0);

  // File Uploads & Drag & Drop State
  const [attachments, setAttachments] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Voice Output (Text-to-Speech) State
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [speechRate, setSpeechRate] = useState(1.0);
  const [speechPitch, setSpeechPitch] = useState(1.0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speakingMsgId, setSpeakingMsgId] = useState(null);
  const [isVoicePaused, setIsVoicePaused] = useState(false);
  const [voiceSettingsOpen, setVoiceSettingsOpen] = useState(false);

  // Multi-LLM Key Vault Modal State
  const [keyVaultOpen, setKeyVaultOpen] = useState(false);
  const [keyVaultData, setKeyVaultData] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState('groq');
  const [newKeyInput, setNewKeyInput] = useState('');
  const [keySaving, setKeySaving] = useState(false);

  // Autonomous Task Scheduler Modal State
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [schedulesList, setSchedulesList] = useState([]);
  const [scheduleHistory, setScheduleHistory] = useState([]);
  const [schedulerTab, setSchedulerTab] = useState('active'); // 'active' | 'create' | 'history'
  const [newSchedule, setNewSchedule] = useState({
    name: '',
    prompt: '',
    schedule_type: 'interval',
    interval_minutes: 60,
    daily_time: '09:00',
    cron_expr: '0 9 * * *',
    department: 'auto'
  });

  // Cognitive Memory & Adaptive Persona Impression State
  const [memoryModalOpen, setMemoryModalOpen] = useState(false);
  const [memoryProfile, setMemoryProfile] = useState(null);
  const [memoryLoading, setMemoryLoading] = useState(false);

  // Server health state
  const [serverHealth, setServerHealth] = useState('connecting'); // 'online' | 'offline' | 'connecting'
  const [backendStats, setBackendStats] = useState({ totalKeys: 1, activeJobs: 0 });

  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  // -------------------------------------------------------------
  // Initial Voice Loading & Health Polling
  // -------------------------------------------------------------
  useEffect(() => {
    // Load voices
    const loadVoices = () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const available = window.speechSynthesis.getVoices();
        if (available.length > 0) {
          setVoices(available);
          const englishVoice = available.find(v => v.lang.includes('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Microsoft') || v.name.includes('Enhanced'))) || available[0];
          if (englishVoice && !selectedVoice) {
            setSelectedVoice(englishVoice.name);
          }
        }
      }
    };

    loadVoices();
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    // Health check & stats polling
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        if (res.ok) {
          const data = await res.json();
          setServerHealth('online');
          if (data.key_vault) {
            setKeyVaultData(data.key_vault);
            const groqKeys = data.key_vault.groq?.total_keys || 1;
            setBackendStats(prev => ({ ...prev, totalKeys: groqKeys }));
          }
        } else {
          setServerHealth('offline');
        }
      } catch (err) {
        setServerHealth('offline');
      }
    };

    checkHealth();
    fetchMemoryProfile();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Execution Timer Tracker
  useEffect(() => {
    let timer;
    if (isLoading && executionStartTime) {
      timer = setInterval(() => {
        setExecutionDuration(Math.floor((Date.now() - executionStartTime) / 1000));
      }, 1000);
    } else {
      setExecutionDuration(0);
    }
    return () => clearInterval(timer);
  }, [isLoading, executionStartTime]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // -------------------------------------------------------------
  // Voice Text-to-Speech (TTS) Engine
  // -------------------------------------------------------------
  const cleanMarkdownForSpeech = (text) => {
    if (!text) return '';
    return text
      .replace(/###?\s+/g, '')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/`{1,3}[^`]*`{1,3}/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/[-*]\s+/g, '')
      .replace(/#{1,6}\s+/g, '')
      .replace(/---/g, '')
      .replace(/\|/g, ' ')
      .trim();
  };

  const handleSpeak = (msgId, text) => {
    if (!('speechSynthesis' in window)) {
      alert('Speech synthesis not supported in this browser environment.');
      return;
    }

    if (isSpeaking && speakingMsgId === msgId) {
      if (isVoicePaused) {
        window.speechSynthesis.resume();
        setIsVoicePaused(false);
      } else {
        window.speechSynthesis.pause();
        setIsVoicePaused(true);
      }
      return;
    }

    // Cancel current speech
    window.speechSynthesis.cancel();

    const cleanText = cleanMarkdownForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const chosen = voices.find(v => v.name === selectedVoice);
    if (chosen) utterance.voice = chosen;
    utterance.rate = speechRate;
    utterance.pitch = speechPitch;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setSpeakingMsgId(msgId);
      setIsVoicePaused(false);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setSpeakingMsgId(null);
      setIsVoicePaused(false);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setSpeakingMsgId(null);
      setIsVoicePaused(false);
    };

    window.speechSynthesis.speak(utterance);
  };

  const handleStopSpeech = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      setSpeakingMsgId(null);
      setIsVoicePaused(false);
    }
  };

  // -------------------------------------------------------------
  // File Upload & Drag-and-Drop Parser
  // -------------------------------------------------------------
  const handleFileSelect = (files) => {
    if (!files || files.length === 0) return;

    Array.from(files).forEach(file => {
      const reader = new FileReader();
      const isText = file.type.startsWith('text/') || 
                     file.name.endsWith('.py') || 
                     file.name.endsWith('.js') || 
                     file.name.endsWith('.jsx') || 
                     file.name.endsWith('.ts') || 
                     file.name.endsWith('.tsx') || 
                     file.name.endsWith('.json') || 
                     file.name.endsWith('.csv') || 
                     file.name.endsWith('.md') || 
                     file.name.endsWith('.txt') || 
                     file.name.endsWith('.html') || 
                     file.name.endsWith('.css') || 
                     file.name.endsWith('.sql') || 
                     file.name.endsWith('.yml') || 
                     file.name.endsWith('.yaml') || 
                     file.name.endsWith('.log');

      reader.onload = (e) => {
        const content = isText ? e.target.result : `[Binary file: ${file.name}, size: ${file.size} bytes]`;
        setAttachments(prev => [
          ...prev,
          {
            id: `file-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
            name: file.name,
            type: file.type || 'text/plain',
            size: file.size,
            content: content
          }
        ]);
      };

      if (isText) {
        reader.readAsText(file);
      } else {
        reader.readAsDataURL(file);
      }
    });
  };

  const removeAttachment = (id) => {
    setAttachments(prev => prev.filter(att => att.id !== id));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const getFileIcon = (fileName) => {
    if (fileName.endsWith('.csv') || fileName.endsWith('.xlsx')) return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
    if (fileName.endsWith('.py') || fileName.endsWith('.js') || fileName.endsWith('.ts') || fileName.endsWith('.json')) return <FileCode className="w-4 h-4 text-cyan-400" />;
    if (fileName.endsWith('.md') || fileName.endsWith('.txt')) return <FileText className="w-4 h-4 text-indigo-400" />;
    return <File className="w-4 h-4 text-slate-400" />;
  };

  // -------------------------------------------------------------
  // API Key Vault Management
  // -------------------------------------------------------------
  const fetchKeyVault = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings/keys`);
      if (res.ok) {
        const data = await res.json();
        setKeyVaultData(data.providers);
      }
    } catch (err) {
      console.error('Failed to fetch key vault:', err);
    }
  };

  const handleAddKey = async () => {
    if (!newKeyInput.trim()) return;
    setKeySaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings/keys/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          key: newKeyInput.trim()
        })
      });
      if (res.ok) {
        const data = await res.json();
        setKeyVaultData(data.providers);
        setNewKeyInput('');
      } else {
        alert('Failed to add key. Ensure key is valid.');
      }
    } catch (err) {
      alert(`Error connecting to server: ${err.message}`);
    } finally {
      setKeySaving(false);
    }
  };

  const handleDeleteKey = async (provider, index) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/settings/keys/${provider}/${index}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        const data = await res.json();
        setKeyVaultData(data.providers);
      }
    } catch (err) {
      alert(`Error removing key: ${err.message}`);
    }
  };

  // -------------------------------------------------------------
  // Task Scheduler Management
  // -------------------------------------------------------------
  const fetchSchedules = async () => {
    try {
      const [schedRes, histRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/schedules`),
        fetch(`${API_BASE_URL}/api/schedules/history`)
      ]);
      if (schedRes.ok) {
        const sData = await schedRes.json();
        setSchedulesList(sData.active_jobs || []);
        setBackendStats(prev => ({ ...prev, activeJobs: sData.total_jobs || 0 }));
      }
      if (histRes.ok) {
        const hData = await histRes.json();
        setScheduleHistory(hData.history || []);
      }
    } catch (err) {
      console.error('Failed to fetch schedules:', err);
    }
  };

  const handleCreateSchedule = async (e) => {
    e.preventDefault();
    if (!newSchedule.name || !newSchedule.prompt) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/schedules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSchedule)
      });
      if (res.ok) {
        await fetchSchedules();
        setSchedulerTab('active');
        setNewSchedule({
          name: '',
          prompt: '',
          schedule_type: 'interval',
          interval_minutes: 60,
          daily_time: '09:00',
          cron_expr: '0 9 * * *',
          department: 'auto'
        });
      }
    } catch (err) {
      alert(`Failed to create schedule: ${err.message}`);
    }
  };

  const handleDeleteSchedule = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/schedules/${jobId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchSchedules();
      }
    } catch (err) {
      alert(`Error deleting schedule: ${err.message}`);
    }
  };

  const handleRunScheduleNow = async (jobId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/schedules/${jobId}/run`, {
        method: 'POST'
      });
      if (res.ok) {
        alert('Job triggered immediately in background. Check History in a moment.');
        setTimeout(fetchSchedules, 2000);
      }
    } catch (err) {
      alert(`Error triggering job: ${err.message}`);
    }
  };

  // -------------------------------------------------------------
  // Cognitive Memory & Adaptive Persona Management
  // -------------------------------------------------------------
  const fetchMemoryProfile = async () => {
    setMemoryLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/profile`);
      if (res.ok) {
        const data = await res.json();
        setMemoryProfile(data.profile);
      }
    } catch (err) {
      console.error('Failed to fetch cognitive memory profile:', err);
    } finally {
      setMemoryLoading(false);
    }
  };

  const handleClearMemory = async () => {
    if (!window.confirm("Are you sure you want to reset multi-turn conversation memory history?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/memory/clear`, { method: 'POST' });
      if (res.ok) {
        await fetchMemoryProfile();
        alert('Conversation memory history cleared successfully.');
      }
    } catch (err) {
      alert(`Error clearing memory: ${err.message}`);
    }
  };

  // -------------------------------------------------------------
  // Session & Multi-Turn Controls
  // -------------------------------------------------------------
  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    setSessionId(newId);
    try {
      localStorage.setItem('mak_session_id', newId);
    } catch (e) {
      console.warn('LocalStorage error:', e);
    }
    setMessages([
      {
        id: `init-${Date.now()}`,
        role: 'assistant',
        department: 'Chief of Staff',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: "### 🟢 New Multi-Turn Session Initialized\n\nI am **MAK**, your autonomous multi-department cognitive orchestrator. How can I assist you?\n\n* All subsequent queries in this session maintain complete conversational memory.\n* Click any quick-select options or enter a new command below.",
        status: 'idle'
      }
    ]);
  };

  const handleCopyCode = (code, codeId) => {
    navigator.clipboard.writeText(code);
    setCopiedCodeId(codeId);
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const handleOptionSelect = (promptText) => {
    handleSubmit(null, promptText);
  };

  // -------------------------------------------------------------
  // Message Submission & Execution
  // -------------------------------------------------------------
  const handleSubmit = async (e, customPrompt = null) => {
    if (e) e.preventDefault();
    const effectivePrompt = (customPrompt !== null ? customPrompt : input).trim();
    if ((!effectivePrompt && attachments.length === 0) || isLoading) return;

    const userPrompt = effectivePrompt;
    const currentAttachments = [...attachments];
    const userTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Detect department intent for dynamic UI feedback
    const lower = userPrompt.toLowerCase();
    let targetDept = 'triage';
    if (lower.includes('search') || lower.includes('google') || lower.includes('look up') || lower.includes('http') || lower.includes('www.') || lower.includes('news') || lower.includes('find on web')) {
      targetDept = 'general_ops';
    } else if (lower.includes('lead') || lower.includes('cold email') || lower.includes('outreach') || lower.includes('prospect')) {
      targetDept = 'sales';
    } else if (lower.includes('code') || lower.includes('python') || lower.includes('script') || lower.includes('bug') || lower.includes('fix')) {
      targetDept = 'engineering';
    } else if (lower.includes('finance') || lower.includes('dcf') || lower.includes('wacc') || lower.includes('valuation') || lower.includes('cash flow')) {
      targetDept = 'finance';
    } else if (lower.includes('marketing') || lower.includes('seo') || lower.includes('campaign') || lower.includes('ad copy')) {
      targetDept = 'marketing';
    } else if (lower.includes('video') || lower.includes('content') || lower.includes('script') || lower.includes('post')) {
      targetDept = 'content';
    } else if (lower.includes('arxiv') || lower.includes('paper') || lower.includes('academic') || lower.includes('study')) {
      targetDept = 'research';
    }

    setActiveDepartment(targetDept);

    const newUserMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userPrompt,
      attachments: currentAttachments,
      timestamp: userTimestamp
    };

    // Build multi-turn conversational history to maintain LLM context
    const currentHistory = messages
      .filter(m => m.status !== 'error')
      .map(m => ({
        role: m.role,
        content: m.content,
        department: m.department || 'agent'
      }));

    setMessages(prev => [...prev, newUserMsg]);
    setInput('');
    setAttachments([]);
    setIsLoading(true);
    setExecutionStartTime(Date.now());

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userPrompt || 'Analyze attached file context and generate findings.',
          session_id: sessionId,
          chat_history: currentHistory,
          attachments: currentAttachments.map(a => ({
            name: a.name,
            type: a.type,
            content: a.content,
            size: a.size
          }))
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const aiMsgId = `ai-${Date.now()}`;
      const newAiMsg = {
        id: aiMsgId,
        role: 'assistant',
        department: data.active_department || 'Chief of Staff',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: data.response || 'Task executed successfully.',
        status: 'complete'
      };

      setMessages(prev => [...prev, newAiMsg]);
      fetchMemoryProfile();

      // Auto-voice readout if enabled
      if (autoSpeak && data.response) {
        handleSpeak(aiMsgId, data.response);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'assistant',
          department: 'System Failover',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          content: `⚠️ **Execution Error**: ${err.message}\n\n*Check that the headless backend is active at \`http://localhost:8000\` or test key failover in Settings.*`,
          status: 'error'
        }
      ]);
    } finally {
      setIsLoading(false);
      setExecutionStartTime(null);
    }
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleDepartmentPillClick = (dept) => {
    setActiveDepartment(dept.id);
    setInput(dept.prompt);
  };

  // -------------------------------------------------------------
  // Full Markdown & Link Renderer
  // -------------------------------------------------------------
  const renderFormattedContent = (content) => {
    if (!content) return null;

    // Split code blocks first
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, index) => {
      // 1. Fenced Code Blocks with Dedicated Copy Button & Syntax Styling
      if (part.startsWith('```') && part.endsWith('```')) {
        const lines = part.slice(3, -3).trim().split('\n');
        const language = lines[0].trim();
        const code = lines.slice(language ? 1 : 0).join('\n');
        const codeBlockId = `code-block-${index}`;
        const isCodeCopied = copiedCodeId === codeBlockId;

        return (
          <div key={index} className="my-3.5 rounded-xl overflow-hidden border border-cyan-500/30 bg-slate-950 shadow-2xl">
            <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900/90 border-b border-cyan-500/20 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5 text-cyan-400 font-medium uppercase tracking-wider text-[11px]">
                <Terminal className="w-3.5 h-3.5" />
                {language || 'code'}
              </span>
              <button
                type="button"
                onClick={() => handleCopyCode(code, codeBlockId)}
                className="hover:text-cyan-300 transition-colors flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-800 border border-cyan-500/20 hover:border-cyan-400/40 cursor-pointer text-xs font-mono text-slate-300"
                title="Copy code snippet"
              >
                {isCodeCopied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400 font-semibold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Code</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-4 text-xs font-mono text-cyan-100/95 overflow-x-auto selection:bg-cyan-500/40 select-text leading-relaxed">
              <code>{code}</code>
            </pre>
          </div>
        );
      }

      // 2. Prose / Paragraph / Table / List Blocks
      const paragraphs = part.split(/\n\n+/);
      return (
        <div key={index} className="space-y-3 leading-relaxed text-sm text-slate-200 select-text">
          {paragraphs.map((para, pIdx) => {
            const trimmed = para.trim();
            if (!trimmed) return null;

            // Check if paragraph is a Markdown Table
            if (trimmed.includes('|') && trimmed.includes('\n') && (trimmed.includes('---') || trimmed.includes('|:--'))) {
              const renderedTable = renderMarkdownTable(trimmed, pIdx);
              if (renderedTable) return renderedTable;
            }

            // Headers
            if (trimmed.startsWith('### ')) {
              return (
                <h3 key={pIdx} className="text-base font-semibold text-cyan-300 mt-4 mb-2 flex items-center gap-2 border-b border-cyan-500/20 pb-1 font-display">
                  <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>{renderInlineMarkdown(trimmed.replace(/^###\s+/, ''))}</span>
                </h3>
              );
            }
            if (trimmed.startsWith('## ')) {
              return (
                <h2 key={pIdx} className="text-lg font-bold text-white mt-5 mb-2 font-display flex items-center gap-2">
                  <span>{renderInlineMarkdown(trimmed.replace(/^##\s+/, ''))}</span>
                </h2>
              );
            }
            if (trimmed.startsWith('# ')) {
              return (
                <h1 key={pIdx} className="text-xl font-extrabold text-cyan-200 mt-6 mb-3 font-orbitron tracking-wide">
                  {renderInlineMarkdown(trimmed.replace(/^#\s+/, ''))}
                </h1>
              );
            }

            // Blockquotes
            if (trimmed.startsWith('> ')) {
              return (
                <blockquote key={pIdx} className="my-2.5 pl-3.5 py-1.5 border-l-2 border-cyan-400 bg-cyan-950/30 rounded-r-lg text-slate-300 italic text-xs font-mono">
                  {renderInlineMarkdown(trimmed.replace(/^>\s+/, ''))}
                </blockquote>
              );
            }

            // Bullet or numbered lists
            if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || /^\d+\.\s+/.test(trimmed)) {
              const listLines = trimmed.split('\n');
              return (
                <ul key={pIdx} className="space-y-1.5 my-2.5 pl-1">
                  {listLines.map((line, lIdx) => {
                    const cleanLine = line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '');
                    return (
                      <li key={lIdx} className="flex items-start gap-2 text-slate-300">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-2 shrink-0 shadow-[0_0_6px_rgba(6,182,212,0.6)]" />
                        <span className="flex-1">{renderInlineMarkdown(cleanLine)}</span>
                      </li>
                    );
                  })}
                </ul>
              );
            }

            // Standard Paragraph
            return (
              <p key={pIdx} className="text-slate-300 leading-relaxed select-text">
                {renderInlineMarkdown(trimmed)}
              </p>
            );
          })}
        </div>
      );
    });
  };

  return (
    <div 
      className="flex flex-col h-screen w-screen overflow-hidden bg-[#06080d] text-slate-100 font-sans"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* ------------------------------------------------------------- */}
      {/* 1. TOP STATUS HUD & DRAG HEADER */}
      {/* ------------------------------------------------------------- */}
      <header className="h-14 border-b border-white/10 glass-panel px-4 flex items-center justify-between select-none z-30 shrink-0">
        <div className="flex items-center gap-3">
          {/* Futuristic MAK Glyph */}
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 shadow-[0_0_15px_rgba(6,182,212,0.5)]">
            <Bot className="w-5 h-5 text-white" />
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 border-2 border-slate-900 rounded-full animate-pulse" />
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-orbitron font-extrabold text-base tracking-wider bg-gradient-to-r from-cyan-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent">
                MAK
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold bg-cyan-950/80 text-cyan-400 border border-cyan-500/30 rounded">
                v2.5 COGNITIVE
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-mono tracking-tight">
              Autonomous Multi-Agent Swarm Orchestrator
            </span>
          </div>
        </div>

        {/* Center Live Health & Failover HUD */}
        <div className="hidden md:flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-white/5">
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${serverHealth === 'online' ? 'bg-emerald-400' : 'bg-rose-400'}`} />
              <span className={`relative inline-flex rounded-full h-2 w-2 ${serverHealth === 'online' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            </span>
            <span className="text-slate-300">
              CORE: <strong className={serverHealth === 'online' ? 'text-emerald-400 font-semibold' : 'text-rose-400'}>{serverHealth.toUpperCase()}</strong>
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 border border-white/5 text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>GROQ: <strong className="text-cyan-300">Llama-3.3-70B</strong></span>
            <span className="px-1.5 py-0.2 bg-cyan-950 text-cyan-400 text-[10px] rounded border border-cyan-500/20">
              {backendStats.totalKeys} Keys Active
            </span>
          </div>

          {/* Voice Indicator Badge */}
          {isSpeaking && (
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 animate-pulse">
              <div className="flex items-center gap-0.5 h-3">
                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
              </div>
              <span className="text-[11px]">Speaking Deliverable...</span>
            </div>
          )}
        </div>

        {/* Right Navigation & HUD Controls */}
        <div className="flex items-center gap-2">
          {/* New Multi-Turn Session Button */}
          <button
            onClick={handleNewChat}
            className="p-2 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 hover:text-white hover:bg-cyan-900/60 hover:border-cyan-400 transition-all cursor-pointer flex items-center gap-1.5 text-xs font-mono font-medium shadow-sm hover:shadow-[0_0_12px_rgba(6,182,212,0.3)]"
            title="Start New Multi-Turn Session"
          >
            <RotateCcw className="w-4 h-4 text-cyan-400" />
            <span className="hidden sm:inline font-mono">New Chat</span>
          </button>

          {/* Voice Settings Toggle */}
          <button
            onClick={() => setVoiceSettingsOpen(!voiceSettingsOpen)}
            className={`p-2 rounded-lg border transition-all cursor-pointer flex items-center gap-1.5 text-xs ${
              autoSpeak 
                ? 'bg-cyan-950/70 border-cyan-500/50 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.2)]' 
                : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
            title="Audio Voice Settings"
          >
            {autoSpeak ? <Volume2 className="w-4 h-4 text-cyan-400" /> : <VolumeX className="w-4 h-4" />}
            <span className="hidden sm:inline font-mono">Voice</span>
          </button>

          {/* Scheduler Button */}
          <button
            onClick={() => {
              fetchSchedules();
              setScheduleModalOpen(true);
            }}
            className="p-2 rounded-lg bg-slate-900/60 border border-white/5 text-slate-300 hover:text-white hover:bg-slate-800 transition-all cursor-pointer flex items-center gap-1.5 text-xs"
            title="Autonomous Task Scheduler"
          >
            <Clock className="w-4 h-4 text-amber-400" />
            <span className="hidden sm:inline font-mono">Schedules</span>
            {backendStats.activeJobs > 0 && (
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            )}
          </button>

          {/* Cognitive Memory & Persona Impression Button */}
          <button
            onClick={() => {
              fetchMemoryProfile();
              setMemoryModalOpen(true);
            }}
            className="p-2 rounded-lg bg-slate-900/60 border border-purple-500/30 text-purple-300 hover:text-white hover:border-purple-400 hover:shadow-[0_0_15px_rgba(168,85,247,0.3)] transition-all cursor-pointer flex items-center gap-1.5 text-xs font-medium"
            title="Cognitive Memory & Adaptive User Impression"
          >
            <Brain className="w-4 h-4 text-purple-400" />
            <span className="hidden sm:inline font-mono">Memory</span>
            {memoryProfile?.total_interactions > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-purple-950/90 border border-purple-500/40 text-[10px] text-purple-300 font-mono">
                {memoryProfile.total_interactions}
              </span>
            )}
          </button>

          {/* Key Vault Settings Button */}
          <button
            onClick={() => {
              fetchKeyVault();
              setKeyVaultOpen(true);
            }}
            className="p-2 rounded-lg bg-gradient-to-r from-cyan-950/80 to-indigo-950/80 border border-cyan-500/30 text-cyan-300 hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all cursor-pointer flex items-center gap-1.5 text-xs font-medium"
            title="Multi-LLM Key Vault & Failover Settings"
          >
            <Key className="w-4 h-4 text-cyan-400" />
            <span className="hidden sm:inline font-mono">Key Vault</span>
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* 2. VOICE CONTROLS POPUP DRAWER */}
      {/* ------------------------------------------------------------- */}
      {voiceSettingsOpen && (
        <div className="glass-panel-glow border-b border-cyan-500/30 px-6 py-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono z-20 animate-in slide-in-from-top duration-200">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-cyan-400" />
              <span className="text-slate-300 font-semibold">Voice Engine (TTS):</span>
            </div>

            {/* Voice selection */}
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="bg-slate-900 border border-cyan-500/30 rounded px-2.5 py-1 text-slate-200 focus:outline-none focus:border-cyan-400"
            >
              {voices.map(v => (
                <option key={v.name} value={v.name}>
                  {v.name} ({v.lang})
                </option>
              ))}
            </select>

            {/* Auto-Speak Toggle */}
            <label className="flex items-center gap-2 cursor-pointer text-slate-300 select-none">
              <input
                type="checkbox"
                checked={autoSpeak}
                onChange={(e) => setAutoSpeak(e.target.checked)}
                className="rounded bg-slate-900 border-cyan-500/40 text-cyan-500 focus:ring-0"
              />
              <span>Auto-Speak AI Deliverables</span>
            </label>
          </div>

          <div className="flex items-center gap-6">
            {/* Speed Slider */}
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Speed: {speechRate}x</span>
              <input
                type="range"
                min="0.7"
                max="1.5"
                step="0.1"
                value={speechRate}
                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                className="w-20 accent-cyan-400 cursor-pointer"
              />
            </div>

            {/* Stop current speech */}
            {isSpeaking && (
              <button
                onClick={handleStopSpeech}
                className="px-2.5 py-1 rounded bg-rose-950/80 border border-rose-500/40 text-rose-300 hover:bg-rose-900 transition-colors flex items-center gap-1 cursor-pointer"
              >
                <Square className="w-3 h-3" /> Stop Audio
              </button>
            )}

            <button
              onClick={() => setVoiceSettingsOpen(false)}
              className="text-slate-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 3. MAIN WORKSPACE CONTAINER */}
      {/* ------------------------------------------------------------- */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR: MAK DEPARTMENT HUB */}
        <aside className="w-80 border-r border-white/10 glass-panel flex flex-col justify-between shrink-0 overflow-y-auto">
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between px-1">
              <span className="text-[11px] font-mono uppercase tracking-widest text-slate-400 font-semibold flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                Specialist Swarm
              </span>
              <span className="text-[10px] font-mono text-cyan-400 px-1.5 py-0.5 rounded bg-cyan-950/60 border border-cyan-500/20">
                8 DEPARTMENTS
              </span>
            </div>

            {/* Department Roster Pills */}
            <div className="space-y-1.5">
              {MAK_DEPARTMENTS.map((dept) => {
                const Icon = dept.icon;
                const isActive = activeDepartment === dept.id;
                const isExecuting = isLoading && isActive;

                return (
                  <button
                    key={dept.id}
                    onClick={() => handleDepartmentPillClick(dept)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-all duration-200 flex items-start gap-3 cursor-pointer group ${
                      isActive
                        ? 'bg-gradient-to-r from-cyan-950/50 to-indigo-950/40 border-cyan-500/40 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                        : 'bg-slate-900/30 border-white/5 hover:bg-slate-900/60 hover:border-white/10'
                    }`}
                  >
                    <div className={`p-2 rounded-lg mt-0.5 shrink-0 transition-all ${
                      isActive
                        ? 'bg-cyan-500/20 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                        : 'bg-slate-800/80 text-slate-400 group-hover:text-slate-200'
                    }`}>
                      <Icon className="w-4 h-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-semibold truncate ${
                          isActive ? 'text-cyan-200' : 'text-slate-200 group-hover:text-white'
                        }`}>
                          {dept.name}
                        </span>
                        <div className="flex items-center gap-1 shrink-0 ml-1">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            isExecuting
                              ? 'bg-emerald-400 animate-ping'
                              : isActive
                              ? 'bg-cyan-400'
                              : 'bg-slate-600'
                          }`} />
                        </div>
                      </div>

                      <p className="text-[11px] text-slate-400 truncate mt-0.5">
                        {dept.role}
                      </p>

                      {isExecuting && (
                        <div className="flex items-center gap-1.5 mt-1.5 text-[10px] text-emerald-400 font-mono animate-pulse">
                          <Activity className="w-3 h-3" />
                          <span>{dept.activeSubtext}</span>
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bottom Sidebar Status Card */}
          <div className="p-4 border-t border-white/10 space-y-3 bg-slate-950/40">
            <div className="p-3 rounded-xl bg-slate-900/70 border border-cyan-500/20 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0" />
                <div className="flex flex-col">
                  <span className="text-xs font-medium text-slate-200">Failover Engine</span>
                  <span className="text-[10px] text-emerald-400 font-mono">Zero Downtime Active</span>
                </div>
              </div>
              <button
                onClick={() => {
                  fetchKeyVault();
                  setKeyVaultOpen(true);
                }}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 font-mono underline cursor-pointer"
              >
                Configure
              </button>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono px-1">
              <span>LangGraph v0.2</span>
              <span>CrewAI Swarm</span>
            </div>
          </div>
        </aside>

        {/* RIGHT MAIN AREA: CHAT & COMMAND DOCK */}
        <main className="flex-1 flex flex-col relative overflow-hidden bg-gradient-to-b from-transparent to-[#070a11]">
          {/* Drag and Drop Active Overlay */}
          {isDragging && (
            <div className="absolute inset-0 bg-cyan-950/80 border-2 border-dashed border-cyan-400 rounded-xl z-50 flex flex-col items-center justify-center gap-3 backdrop-blur-md pointer-events-none">
              <UploadCloud className="w-16 h-16 text-cyan-400 animate-bounce" />
              <h3 className="text-lg font-bold text-white font-orbitron">DROP FILES TO ATTACH</h3>
              <p className="text-xs text-cyan-200 font-mono">Accepts documents, code files, CSV data, and specs</p>
            </div>
          )}

          {/* Chat Messages Scroll Container */}
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 scroll-smooth"
          >
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user';
              const isCurrentlySpeaking = isSpeaking && speakingMsgId === msg.id;

              return (
                <div
                  key={msg.id || index}
                  className={`flex gap-3.5 max-w-4xl mx-auto ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in duration-300`}
                >
                  {/* Assistant Avatar */}
                  {!isUser && (
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-[0_0_12px_rgba(6,182,212,0.4)]">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  {/* Message Capsule */}
                  <div className={`flex flex-col max-w-[85%] sm:max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
                    {/* Header info */}
                    <div className="flex items-center gap-2 mb-1 px-1 text-[11px] font-mono text-slate-400">
                      <span className={isUser ? 'text-indigo-300 font-medium' : 'text-cyan-400 font-semibold'}>
                        {isUser ? 'OPERATOR' : (msg.department || 'MAK')}
                      </span>
                      <span>•</span>
                      <span>{msg.timestamp}</span>
                    </div>

                    {/* Bubble Content */}
                    <div className={`p-4 rounded-2xl transition-all ${
                      isUser
                        ? 'bg-gradient-to-r from-indigo-600 to-blue-600 text-white shadow-lg shadow-indigo-950/50 rounded-tr-none'
                        : 'glass-panel border border-white/10 text-slate-100 rounded-tl-none shadow-xl hover:border-cyan-500/30'
                    }`}>
                      {/* Attached Files inside user message */}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="mb-3 pb-2.5 border-b border-indigo-400/30 flex flex-wrap gap-2">
                          {msg.attachments.map(att => (
                            <div
                              key={att.id}
                              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/80 border border-indigo-400/40 text-xs font-mono text-indigo-200"
                            >
                              {getFileIcon(att.name)}
                              <span className="truncate max-w-[140px]">{att.name}</span>
                              <span className="text-[10px] text-indigo-300/70">
                                ({Math.round((att.size || 0) / 1024)} KB)
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Main Message Text / Markdown */}
                      {isUser ? (
                        <p className="whitespace-pre-wrap text-sm leading-relaxed select-text">{msg.content}</p>
                      ) : (
                        renderFormattedContent(msg.content)
                      )}

                      {/* Interactive Quick-Pick Option Chips (Option A / Option B / 1 / 2) */}
                      {!isUser && (() => {
                        const detectedOptions = extractOptionsFromMessage(msg.content);
                        if (detectedOptions.length === 0) return null;

                        return (
                          <div className="mt-3.5 pt-3 border-t border-cyan-500/20 flex flex-wrap items-center gap-2 select-none">
                            <span className="text-[11px] font-mono text-cyan-400 font-semibold flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-cyan-400" />
                              Quick Select:
                            </span>
                            {detectedOptions.map((opt) => (
                              <button
                                key={opt.id}
                                type="button"
                                onClick={() => handleOptionSelect(opt.fullPrompt)}
                                className="group flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-500/40 hover:border-cyan-400 text-xs font-mono text-cyan-200 hover:text-white transition-all cursor-pointer shadow-md hover:shadow-[0_0_12px_rgba(6,182,212,0.4)]"
                                title={`Select ${opt.label}: ${opt.text}`}
                              >
                                <span className="w-4 h-4 rounded-full bg-cyan-500/30 group-hover:bg-cyan-400 text-cyan-300 group-hover:text-slate-950 flex items-center justify-center font-bold text-[10px] transition-colors">
                                  {opt.id}
                                </span>
                                <span className="font-medium truncate max-w-[200px] sm:max-w-[260px]">{opt.text}</span>
                                <ChevronRight className="w-3 h-3 text-cyan-400 group-hover:translate-x-0.5 transition-transform shrink-0" />
                              </button>
                            ))}
                          </div>
                        );
                      })()}
                    </div>

                    {/* Action Bar (Audio Listen & Copy) for AI responses */}
                    {!isUser && (
                      <div className="flex items-center gap-2 mt-2 px-1 text-xs font-mono">
                        {/* Audio Speak Button */}
                        <button
                          type="button"
                          onClick={() => handleSpeak(msg.id, msg.content)}
                          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
                            isCurrentlySpeaking
                              ? 'bg-cyan-950 border-cyan-400 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.4)]'
                              : 'bg-slate-900/60 border-white/5 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30'
                          }`}
                          title="Listen to Deliverable"
                        >
                          {isCurrentlySpeaking ? (
                            <>
                              <div className="flex items-center gap-0.5 h-3">
                                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                                <div className="w-0.5 bg-cyan-400 equalizer-bar" />
                              </div>
                              <span>Playing...</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
                              <span>Listen</span>
                            </>
                          )}
                        </button>

                        {/* Copy Deliverable Button */}
                        <button
                          type="button"
                          onClick={() => handleCopy(msg.content, index)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900/60 border border-white/5 text-slate-400 hover:text-white hover:border-white/20 transition-colors cursor-pointer"
                          title="Copy Full Deliverable (Markdown / Text)"
                        >
                          {copiedIndex === index ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                              <span className="text-emerald-400 font-semibold">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Text</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* User Avatar */}
                  {isUser && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shrink-0 mt-1 shadow-md">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Executing Pulse State Card */}
            {isLoading && (
              <div className="flex gap-3.5 max-w-4xl mx-auto items-start animate-in fade-in duration-300">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.5)]">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="glass-panel-glow border border-cyan-500/40 p-4 rounded-2xl rounded-tl-none space-y-3 min-w-[320px]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500" />
                      </span>
                      <span className="font-orbitron font-bold text-xs text-cyan-300 tracking-wide">
                        MAK COGNITIVE GRAPH EXECUTING
                      </span>
                    </div>
                    <span className="text-xs font-mono text-cyan-400 font-semibold">
                      {executionDuration}s
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-slate-300 font-mono">
                    <Activity className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
                    <span>Orchestrating specialized department crews & synthesizing deliverable...</span>
                  </div>

                  <div className="w-full bg-slate-900/80 rounded-full h-1.5 overflow-hidden border border-cyan-500/20">
                    <div className="h-full bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400 animate-pulse w-full" />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* ------------------------------------------------------------- */}
          {/* 4. BOTTOM COMMAND DOCK & FILE ATTACHMENTS */}
          {/* ------------------------------------------------------------- */}
          <div className="p-4 sm:p-6 border-t border-white/10 glass-panel shrink-0 space-y-3">
            {/* Attached Files Previews */}
            {attachments.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pb-1">
                <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                  <Paperclip className="w-3 h-3 text-cyan-400" />
                  Context Attachments:
                </span>
                {attachments.map(att => (
                  <div
                    key={att.id}
                    className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-900/90 border border-cyan-500/30 text-xs font-mono text-cyan-200 shadow-sm"
                  >
                    {getFileIcon(att.name)}
                    <span className="truncate max-w-[150px] font-medium">{att.name}</span>
                    <span className="text-[10px] text-slate-400">
                      ({Math.round((att.size || 0) / 1024)} KB)
                    </span>
                    <button
                      onClick={() => removeAttachment(att.id)}
                      className="text-slate-400 hover:text-rose-400 transition-colors ml-1 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Input Form Box */}
            <form
              onSubmit={handleSubmit}
              className="glass-input rounded-2xl p-2 flex flex-col gap-2 transition-all"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Assign a directive to MAK (e.g. 'Search web for...', 'Conduct DCF valuation...', 'Draft cold outreach...')..."
                className="w-full bg-transparent px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none min-h-[44px] max-h-32"
                rows={1}
              />

              <div className="flex items-center justify-between pt-1 px-2 border-t border-white/5">
                <div className="flex items-center gap-2">
                  {/* File Upload Hidden Input & Trigger Button */}
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => handleFileSelect(e.target.files)}
                    multiple
                    className="hidden"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2 rounded-lg bg-slate-900/70 border border-white/5 text-slate-400 hover:text-cyan-300 hover:border-cyan-500/30 transition-all cursor-pointer flex items-center gap-1.5 text-xs font-mono"
                    title="Upload Documents or Code"
                  >
                    <Paperclip className="w-4 h-4 text-cyan-400" />
                    <span className="hidden sm:inline">Attach</span>
                  </button>

                  {/* Quick Schedule Prompt Button */}
                  <button
                    type="button"
                    onClick={() => {
                      if (input.trim()) {
                        setNewSchedule(prev => ({ ...prev, prompt: input.trim(), name: input.trim().slice(0, 30) }));
                      }
                      setScheduleModalOpen(true);
                      setSchedulerTab('create');
                    }}
                    className="p-2 rounded-lg bg-slate-900/70 border border-white/5 text-slate-400 hover:text-amber-300 hover:border-amber-500/30 transition-all cursor-pointer flex items-center gap-1.5 text-xs font-mono"
                    title="Schedule this prompt as an automated background job"
                  >
                    <CalendarPlus className="w-4 h-4 text-amber-400" />
                    <span className="hidden sm:inline">Schedule</span>
                  </button>
                </div>

                {/* Send Prompt Action Button */}
                <button
                  type="submit"
                  disabled={isLoading || (!input.trim() && attachments.length === 0)}
                  className={`px-4 py-2 rounded-xl font-medium text-xs flex items-center gap-2 transition-all cursor-pointer ${
                    isLoading || (!input.trim() && attachments.length === 0)
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                      : 'bg-gradient-to-r from-cyan-500 to-indigo-600 text-white shadow-[0_0_15px_rgba(6,182,212,0.4)] hover:shadow-[0_0_20px_rgba(6,182,212,0.6)]'
                  }`}
                >
                  <span>Dispatch</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </div>
        </main>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 5. MULTI-LLM API KEY VAULT & FAILOVER SETTINGS MODAL */}
      {/* ------------------------------------------------------------- */}
      {keyVaultOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel-glow w-full max-w-2xl rounded-2xl border border-cyan-500/40 p-6 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
                  <Key className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white font-orbitron tracking-wide">
                    MULTI-LLM KEY VAULT & FAILOVER POOL
                  </h2>
                  <p className="text-xs text-slate-400 font-mono">
                    Configure multiple API keys per provider to ensure seamless auto-rotation on 429 rate limits.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setKeyVaultOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Provider Tabs */}
            <div className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
              {['groq', 'openai', 'openrouter', 'anthropic', 'gemini'].map(prov => {
                const isSelected = selectedProvider === prov;
                const count = keyVaultData?.[prov]?.total_keys || 0;
                return (
                  <button
                    key={prov}
                    onClick={() => setSelectedProvider(prov)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider transition-all cursor-pointer flex items-center gap-2 ${
                      isSelected
                        ? 'bg-cyan-950 border border-cyan-400 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.3)]'
                        : 'bg-slate-900/60 border border-white/5 text-slate-400 hover:text-white'
                    }`}
                  >
                    <span>{prov}</span>
                    <span className={`px-1.5 py-0.2 text-[10px] rounded ${
                      count > 0 ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-500'
                    }`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Add New Key Form */}
            <div className="space-y-2">
              <label className="text-xs font-mono text-slate-300 block">
                Add New API Key to <strong className="text-cyan-400 uppercase">{selectedProvider}</strong> Rotation Pool:
              </label>
              <div className="flex gap-2">
                <input
                  type="password"
                  value={newKeyInput}
                  onChange={(e) => setNewKeyInput(e.target.value)}
                  placeholder={`Paste ${selectedProvider} API key (e.g. gsk_... or sk-...)`}
                  className="flex-1 bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-400"
                />
                <button
                  onClick={handleAddKey}
                  disabled={keySaving || !newKeyInput.trim()}
                  className="px-4 py-2 rounded-xl bg-cyan-600 text-white text-xs font-mono font-semibold hover:bg-cyan-500 disabled:bg-slate-800 disabled:text-slate-600 cursor-pointer flex items-center gap-1.5"
                >
                  {keySaving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                  Register Key
                </button>
              </div>
            </div>

            {/* Key Pool List for Selected Provider */}
            <div className="space-y-2">
              <span className="text-xs font-mono text-slate-400 block">
                Active Key Failover Rotation Slots:
              </span>
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {keyVaultData?.[selectedProvider]?.keys?.length > 0 ? (
                  keyVaultData[selectedProvider].keys.map((kObj, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl border flex items-center justify-between text-xs font-mono ${
                        kObj.is_active
                          ? 'bg-cyan-950/60 border-cyan-500/50 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                          : 'bg-slate-900/60 border-white/5'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`w-2 h-2 rounded-full ${kObj.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                        <span className="text-slate-200">{kObj.masked}</span>
                        {kObj.is_active && (
                          <span className="px-2 py-0.5 bg-emerald-950 border border-emerald-500/30 text-emerald-400 text-[10px] rounded font-semibold">
                            ACTIVE SLOT #{idx + 1}
                          </span>
                        )}
                        {!kObj.is_active && (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 text-[10px] rounded">
                            FAILOVER BACKUP #{idx + 1}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteKey(selectedProvider, idx)}
                        className="text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                        title="Remove Key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-xl bg-slate-900/40 border border-white/5 text-center text-xs font-mono text-slate-500">
                    No custom keys registered for {selectedProvider}. Falling back to default .env keys.
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-white/10 pt-4 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <ShieldCheck className="w-4 h-4" />
                Automatic Multi-Key Failover Enabled
              </span>
              <button
                onClick={() => setKeyVaultOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 6. AUTONOMOUS TASK SCHEDULER MODAL */}
      {/* ------------------------------------------------------------- */}
      {scheduleModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel-glow w-full max-w-3xl rounded-2xl border border-amber-500/40 p-6 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4 shrink-0">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.3)]">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white font-orbitron tracking-wide">
                    AUTONOMOUS TASK SCHEDULER & CRON
                  </h2>
                  <p className="text-xs text-slate-400 font-mono">
                    Schedule automated agentic tasks to run recurringly in background with zero human intervention.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setScheduleModalOpen(false)}
                className="text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Navigation Tabs */}
            <div className="flex gap-2 border-b border-white/10 pb-3 shrink-0">
              <button
                onClick={() => setSchedulerTab('active')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5 ${
                  schedulerTab === 'active'
                    ? 'bg-amber-950 border border-amber-400 text-amber-300'
                    : 'bg-slate-900/60 border border-white/5 text-slate-400 hover:text-white'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                Active Schedules ({schedulesList.length})
              </button>
              <button
                onClick={() => setSchedulerTab('create')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5 ${
                  schedulerTab === 'create'
                    ? 'bg-amber-950 border border-amber-400 text-amber-300'
                    : 'bg-slate-900/60 border border-white/5 text-slate-400 hover:text-white'
                }`}
              >
                <CalendarPlus className="w-3.5 h-3.5" />
                Create New Schedule
              </button>
              <button
                onClick={() => setSchedulerTab('history')}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all cursor-pointer flex items-center gap-1.5 ${
                  schedulerTab === 'history'
                    ? 'bg-amber-950 border border-amber-400 text-amber-300'
                    : 'bg-slate-900/60 border border-white/5 text-slate-400 hover:text-white'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Execution History ({scheduleHistory.length})
              </button>
            </div>

            {/* Tab Contents Container */}
            <div className="flex-1 overflow-y-auto pr-1">
              {/* TAB 1: Active Schedules Table */}
              {schedulerTab === 'active' && (
                <div className="space-y-3">
                  {schedulesList.length > 0 ? (
                    schedulesList.map(job => (
                      <div
                        key={job.id}
                        className="p-4 rounded-xl bg-slate-900/70 border border-amber-500/20 flex items-center justify-between text-xs font-mono"
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <strong className="text-white text-sm">{job.name}</strong>
                          </div>
                          <p className="text-slate-400 text-[11px]">Next Execution: <span className="text-amber-300">{job.next_run}</span></p>
                          <p className="text-slate-500 text-[10px] truncate max-w-md">Trigger: {job.trigger}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleRunScheduleNow(job.id)}
                            className="px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-900 cursor-pointer flex items-center gap-1"
                          >
                            <PlayCircle className="w-3.5 h-3.5" /> Run Now
                          </button>
                          <button
                            onClick={() => handleDeleteSchedule(job.id)}
                            className="p-2 rounded-lg bg-rose-950/60 border border-rose-500/30 text-rose-400 hover:bg-rose-900 cursor-pointer"
                            title="Delete Schedule"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-slate-500 text-xs font-mono border border-dashed border-white/10 rounded-2xl">
                      No active recurring background jobs configured. Switch to 'Create New Schedule' to set one up.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Create Schedule Form */}
              {schedulerTab === 'create' && (
                <form onSubmit={handleCreateSchedule} className="space-y-4 text-xs font-mono">
                  <div className="space-y-1.5">
                    <label className="text-slate-300">Schedule Name:</label>
                    <input
                      type="text"
                      required
                      value={newSchedule.name}
                      onChange={(e) => setNewSchedule({ ...newSchedule, name: e.target.value })}
                      placeholder="e.g. Daily AI Market Intelligence Briefing"
                      className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-amber-400"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-300">Agentic Prompt Directive:</label>
                    <textarea
                      required
                      rows={3}
                      value={newSchedule.prompt}
                      onChange={(e) => setNewSchedule({ ...newSchedule, prompt: e.target.value })}
                      placeholder="e.g. Search the live web for the top 5 breakthroughs in autonomous agents today and generate an executive summary..."
                      className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-amber-400 resize-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-slate-300">Schedule Type:</label>
                      <select
                        value={newSchedule.schedule_type}
                        onChange={(e) => setNewSchedule({ ...newSchedule, schedule_type: e.target.value })}
                        className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400"
                      >
                        <option value="interval">Interval (Every X Minutes)</option>
                        <option value="daily">Daily At Time</option>
                        <option value="cron">Advanced 5-Field Cron</option>
                      </select>
                    </div>

                    {newSchedule.schedule_type === 'interval' && (
                      <div className="space-y-1.5">
                        <label className="text-slate-300">Interval (Minutes):</label>
                        <input
                          type="number"
                          min="1"
                          value={newSchedule.interval_minutes}
                          onChange={(e) => setNewSchedule({ ...newSchedule, interval_minutes: parseInt(e.target.value) || 60 })}
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400"
                        />
                      </div>
                    )}

                    {newSchedule.schedule_type === 'daily' && (
                      <div className="space-y-1.5">
                        <label className="text-slate-300">Time (HH:MM 24h):</label>
                        <input
                          type="time"
                          value={newSchedule.daily_time}
                          onChange={(e) => setNewSchedule({ ...newSchedule, daily_time: e.target.value })}
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400"
                        />
                      </div>
                    )}

                    {newSchedule.schedule_type === 'cron' && (
                      <div className="space-y-1.5">
                        <label className="text-slate-300">Cron Expression:</label>
                        <input
                          type="text"
                          value={newSchedule.cron_expr}
                          onChange={(e) => setNewSchedule({ ...newSchedule, cron_expr: e.target.value })}
                          placeholder="0 9 * * 1-5"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-400"
                        />
                      </div>
                    )}
                  </div>

                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 text-slate-950 font-bold text-xs font-mono hover:from-amber-400 hover:to-orange-500 cursor-pointer shadow-lg shadow-amber-950/50"
                  >
                    Activate Autonomous Schedule
                  </button>
                </form>
              )}

              {/* TAB 3: Execution History */}
              {schedulerTab === 'history' && (
                <div className="space-y-3">
                  {scheduleHistory.length > 0 ? (
                    scheduleHistory.map((hist, hIdx) => (
                      <div
                        key={hIdx}
                        className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-2 text-xs font-mono"
                      >
                        <div className="flex items-center justify-between">
                          <strong className="text-white">{hist.job_name}</strong>
                          <span className="text-[10px] text-slate-400">{hist.timestamp} ({hist.duration_sec}s)</span>
                        </div>
                        <div className="text-slate-300 text-[11px] bg-slate-950/80 p-2.5 rounded border border-white/5">
                          {renderFormattedContent(hist.result_preview)}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-slate-500 text-xs font-mono border border-dashed border-white/10 rounded-2xl">
                      No automated background execution runs recorded yet.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 7. COGNITIVE MEMORY & USER IMPRESSION HUD MODAL */}
      {/* ------------------------------------------------------------- */}
      {memoryModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-panel-glow border border-purple-500/40 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-[0_0_50px_rgba(168,85,247,0.25)] animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-purple-500/20 flex items-center justify-between bg-purple-950/20">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-purple-950/80 border border-purple-500/40 text-purple-400">
                  <Brain className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white tracking-wide font-mono">Cognitive Memory & Persona Impression</h3>
                  <p className="text-[11px] text-purple-300/80 font-mono">Adaptive user memory & behavioral impression profile</p>
                </div>
              </div>
              <button
                onClick={() => setMemoryModalOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs font-mono custom-scrollbar">
              {memoryLoading ? (
                <div className="p-12 text-center text-purple-400 font-mono flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Synthesizing Cognitive Persona Profile...
                </div>
              ) : (
                <>
                  {/* Persona Impression Card */}
                  <div className="p-4 rounded-xl bg-gradient-to-br from-purple-950/50 via-slate-900/90 to-indigo-950/40 border border-purple-500/30 space-y-3 shadow-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-purple-400 font-semibold tracking-wider uppercase flex items-center gap-1">
                        <Sparkles className="w-3 h-3 text-purple-400" />
                        Synthesized User Impression
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-purple-950 border border-purple-500/40 text-[10px] text-purple-300">
                        {memoryProfile?.total_interactions || 1} Interactions Logged
                      </span>
                    </div>
                    <p className="text-slate-200 text-xs leading-relaxed font-sans font-medium">
                      "{memoryProfile?.summary_impression || 'Senior AI Systems Architect & Founder. Decisive, focused on high-performance decoupled systems. Values depth, conciseness, structured deliverables, and zero conversational fluff.'}"
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-white/5 text-[11px]">
                      <div>
                        <span className="text-slate-400">Technical Depth: </span>
                        <span className="text-cyan-300 font-semibold">{memoryProfile?.technical_level || 'Expert / Lead Systems Engineer'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Preferred Tone: </span>
                        <span className="text-purple-300 font-semibold">{memoryProfile?.preferred_tone || 'Direct, concise with citations'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Learned Preferences */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-300">
                      <span className="font-semibold text-purple-300 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                        Learned Communication & Formatting Preferences
                      </span>
                      <span className="text-[10px] text-slate-500">Auto-Adapts Every Turn</span>
                    </div>
                    <div className="space-y-1.5">
                      {memoryProfile?.key_preferences && memoryProfile.key_preferences.length > 0 ? (
                        memoryProfile.key_preferences.map((pref, pIdx) => (
                          <div
                            key={pIdx}
                            className="px-3 py-2 rounded-lg bg-slate-900/80 border border-white/5 flex items-center gap-2 text-slate-200 text-[11px]"
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0" />
                            <span>{pref}</span>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 text-center text-slate-500 text-xs">No explicit preferences recorded yet.</div>
                      )}
                    </div>
                  </div>

                  {/* Active Work Context & Projects */}
                  <div className="space-y-2">
                    <span className="font-semibold text-cyan-300 flex items-center gap-1.5 text-[11px]">
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      Active Projects & Domain Focus
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {memoryProfile?.active_projects && memoryProfile.active_projects.length > 0 ? (
                        memoryProfile.active_projects.map((proj, prIdx) => (
                          <span
                            key={prIdx}
                            className="px-2.5 py-1 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-[11px]"
                          >
                            {proj}
                          </span>
                        ))
                      ) : (
                        <span className="text-slate-500 text-xs">MAK Autonomous Enterprise Ecosystem</span>
                      )}
                    </div>
                  </div>

                  {/* Database Engine Telemetry */}
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 space-y-1 text-[11px] text-slate-400">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-slate-300">
                        <Database className="w-3.5 h-3.5 text-indigo-400" />
                        Persistent Memory Engine
                      </span>
                      <span className="text-emerald-400 font-semibold">SQLite WAL Enabled</span>
                    </div>
                    <p className="text-[10px] text-slate-500">
                      Multi-turn conversations and persona impression vectors are synced in real-time to <code className="text-slate-400">scheduled_tasks.db</code>.
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3.5 border-t border-purple-500/20 flex items-center justify-between bg-purple-950/20 text-xs font-mono">
              <button
                onClick={handleClearMemory}
                className="px-3 py-1.5 rounded-lg bg-rose-950/80 border border-rose-500/40 text-rose-300 hover:bg-rose-900 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Reset Memory History
              </button>

              <button
                onClick={fetchMemoryProfile}
                className="px-3.5 py-1.5 rounded-lg bg-purple-900/80 border border-purple-500/40 text-purple-200 hover:bg-purple-800 transition-colors flex items-center gap-1.5 cursor-pointer font-medium"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${memoryLoading ? 'animate-spin' : ''}`} />
                Refresh Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
