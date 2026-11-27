import React, { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';

const API_BASE_URL = (
  process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const PAGE_SIZE = 50;
const THEME_STORAGE_KEY = 'scrapescout_theme';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'projects', label: 'Projects', icon: '💼' },
  { id: 'sources', label: 'Sources', icon: '🔌' },
  { id: 'scheduler', label: 'Scheduler', icon: '⏰' },
  { id: 'activity', label: 'Scraping Activity', icon: '📋' },
  { id: 'exports', label: 'Exports', icon: '📥' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

const WEEKDAY_LABELS = [
  { value: 0, label: 'Mon' },
  { value: 1, label: 'Tue' },
  { value: 2, label: 'Wed' },
  { value: 3, label: 'Thu' },
  { value: 4, label: 'Fri' },
  { value: 5, label: 'Sat' },
  { value: 6, label: 'Sun' },
];

const PLANNED_SOURCES = [
  {
    name: 'Guru',
    url: 'https://www.guru.com',
    description: 'Freelance marketplace integration planned for future parser support.',
  },
  {
    name: 'PeoplePerHour',
    url: 'https://www.peopleperhour.com',
    description: 'Hourly and fixed-price freelance project feed planned.',
  },
  {
    name: 'Freelancer.com',
    url: 'https://www.freelancer.com',
    description: 'Global freelance contest and project API integration planned.',
  },
  {
    name: 'Malt',
    url: 'https://www.malt.com',
    description: 'European freelance opportunity discovery planned.',
  },
];

const PAGE_META = {
  dashboard: {
    title: 'Dashboard Overview',
    subtitle: 'Monitor freelance lead discovery, source health, and manual Truelancer runs.',
  },
  projects: {
    title: 'Discovered Projects',
    subtitle: 'Search, filter, inspect, and manage collected freelance opportunities.',
  },
  sources: {
    title: 'Data Sources',
    subtitle: 'Manage active scraping integrations and view planned platforms.',
  },
  scheduler: {
    title: 'Recurring Scheduler',
    subtitle: 'Configure daily, weekly, monthly, and custom automated scraping schedules.',
  },
  activity: {
    title: 'Scraping Activity',
    subtitle: 'Inspect execution history, record counts, and run diagnostics.',
  },
  exports: {
    title: 'Exports',
    subtitle: 'Download filtered freelance project opportunities in CSV or Excel format.',
  },
  settings: {
    title: 'Settings',
    subtitle: 'Manage your workspace appearance, account profile, and regional defaults.',
  },
};

function App() {
  // Theme State (persisted in localStorage)
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return saved === 'light' || saved === 'dark' ? saved : 'dark';
  });

  // Navigation State
  const [activePage, setActivePage] = useState('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Authentication State
  const [token, setToken] = useState(() => localStorage.getItem('scrapescout_token') || '');
  const [currentUser, setCurrentUser] = useState(() => {
    const cached = localStorage.getItem('scrapescout_user');
    try {
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authFullName, setAuthFullName] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  // Notifications State
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifsCount, setUnreadNotifsCount] = useState(0);
  const [notifsLoading, setNotifsLoading] = useState(false);

  // Projects, Sources, Runs & Analytics State
  const [projects, setProjects] = useState([]);
  const [allProjects, setAllProjects] = useState([]);
  const [sources, setSources] = useState([]);
  const [scrapingRuns, setScrapingRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);

  // Recurring Scheduler State
  const [schedules, setSchedules] = useState([]);
  const [schedulesLoading, setSchedulesLoading] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState({ scheduler_enabled: false, running: false });
  const [scheduleError, setScheduleError] = useState('');
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [schedSourceId, setSchedSourceId] = useState('');
  const [schedName, setSchedName] = useState('Truelancer Recurring Sync');
  const [schedFrequency, setSchedFrequency] = useState('daily');
  const [schedTimeOfDay, setSchedTimeOfDay] = useState('09:00');
  const [schedWeekdays, setSchedWeekdays] = useState([0, 2, 4]);
  const [schedDayOfMonth, setSchedDayOfMonth] = useState(1);
  const [schedCustomType, setSchedCustomType] = useState('cron'); // 'cron' | 'interval'
  const [schedCronExpr, setSchedCronExpr] = useState('0 */6 * * *');
  const [schedIntervalMinutes, setSchedIntervalMinutes] = useState(60);
  const [schedTimezone, setSchedTimezone] = useState('Asia/Kolkata');
  const [schedMaxPages, setSchedMaxPages] = useState(3);
  const [schedMinInterval, setSchedMinInterval] = useState(1.0);
  const [schedEnabled, setSchedEnabled] = useState(true);

  // Manual Truelancer Fetch State
  const [fetchingTruelancer, setFetchingTruelancer] = useState(false);
  const [lastFetchResult, setLastFetchResult] = useState(null);
  const [fetchError, setFetchError] = useState('');

  // Search & Filters State
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedTechnology, setSelectedTechnology] = useState('All');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedSourceId, setSelectedSourceId] = useState('All');
  const [postedFrom, setPostedFrom] = useState('');
  const [postedTo, setPostedTo] = useState('');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  // UI Feedback States
  const [loading, setLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [exportingFormat, setExportingFormat] = useState(null); // 'csv' | 'excel' | null
  const [addingProject, setAddingProject] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // New Project Form Inputs
  const [newTitle, setNewTitle] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newDescription, setNewDescription] = useState('');

  // Daily Opportunities State
  const [dailyDate, setDailyDate] = useState(() => {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(new Date());
  });
  const [dailyData, setDailyData] = useState(null);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyError, setDailyError] = useState('');

  const isLoggedIn = Boolean(token && currentUser);
  const isAdmin = currentUser?.role === 'admin';

  // Persist theme preference and apply data-theme attribute
  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Helper for auth headers
  const getAuthHeaders = useCallback((extraHeaders = {}) => {
    const headers = { ...extraHeaders };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }, [token]);

  const getErrorMessage = async (response) => {
    try {
      const data = await response.json();
      return data.detail || data.message || `Request failed (${response.status})`;
    } catch {
      return `Request failed (${response.status})`;
    }
  };

  const formatField = (value) => {
    if (value === null || value === undefined || value === '') {
      return 'Not specified';
    }
    if (Array.isArray(value)) {
      return value.length
        ? value.map((item) =>
            typeof item === 'object' && item !== null ? JSON.stringify(item) : String(item)
          ).join(', ')
        : 'Not specified';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  };

  const formatTimestamp = (value) => {
    if (!value) return '—';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return String(value);
    return dt.toLocaleString();
  };

  // Build query parameters for search and export
  const buildProjectQueryParams = useCallback((currentOffset = 0, isExport = false) => {
    const params = new URLSearchParams();

    const search = searchTerm.trim();
    if (search) params.set('search', search);
    if (selectedType !== 'All') params.set('project_type', selectedType);
    if (selectedCategory !== 'All') params.set('category', selectedCategory);
    if (selectedTechnology !== 'All') params.set('technology', selectedTechnology);
    if (selectedLocation.trim()) params.set('location', selectedLocation.trim());
    if (selectedSourceId !== 'All') params.set('source_id', selectedSourceId);
    if (postedFrom) params.set('posted_from', `${postedFrom}T00:00:00`);
    if (postedTo) params.set('posted_to', `${postedTo}T23:59:59`);

    if (!isExport) {
      params.set('limit', String(PAGE_SIZE));
      params.set('offset', String(currentOffset));
    }

    return params;
  }, [
    searchTerm,
    selectedType,
    selectedCategory,
    selectedTechnology,
    selectedLocation,
    selectedSourceId,
    postedFrom,
    postedTo,
  ]);

  // Fetch projects from backend
  const fetchProjects = useCallback(async (currentOffset = 0, append = false) => {
    setLoading(true);
    setError('');

    try {
      const query = buildProjectQueryParams(currentOffset, false).toString();
      const response = await fetch(`${API_BASE_URL}/projects/search?${query}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const data = await response.json();
      const rows = Array.isArray(data) ? data : [];

      setProjects((previous) => (append ? [...previous, ...rows] : rows));
      setOffset(currentOffset);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (err) {
      console.error('Error fetching projects:', err);
      setError(err.message || 'Unable to load projects.');
      if (!append) setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [buildProjectQueryParams, getAuthHeaders]);

  // Fetch all projects for metadata options
  const fetchAllProjects = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setAllProjects(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Error fetching all projects:', err);
    }
  }, [getAuthHeaders]);

  // Fetch active sources list
  const fetchSources = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/sources?is_active=true`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        const activeOnly = (Array.isArray(data) ? data : []).filter(
          (src) => src && src.is_active !== false
        );
        setSources(activeOnly);
      }
    } catch (err) {
      console.error('Error fetching sources:', err);
    }
  }, [getAuthHeaders]);

  // Fetch scraping run history
  const fetchScrapingRuns = useCallback(async () => {
    setRunsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/scraping-runs?limit=50`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setScrapingRuns(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Error fetching scraping runs:', err);
    } finally {
      setRunsLoading(false);
    }
  }, [getAuthHeaders]);

  // Fetch recurring schedules and scheduler status
  const fetchSchedules = useCallback(async () => {
    setSchedulesLoading(true);
    setScheduleError('');
    try {
      const [listRes, statusRes] = await Promise.all([
        fetch(`${API_BASE_URL}/schedules`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE_URL}/schedules/status`, { headers: getAuthHeaders() }),
      ]);
      if (listRes.ok) {
        const data = await listRes.json();
        setSchedules(Array.isArray(data) ? data : []);
      } else if (listRes.status === 503) {
        setScheduleError(await getErrorMessage(listRes));
      }
      if (statusRes.ok) {
        setSchedulerStatus(await statusRes.json());
      }
    } catch (err) {
      console.error('Error fetching schedules:', err);
    } finally {
      setSchedulesLoading(false);
    }
  }, [getAuthHeaders]);

  // Fetch dashboard analytics
  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/analytics/dashboard`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        setAnalytics(await response.json());
      }
    } catch (err) {
      console.error('Error fetching dashboard analytics:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [getAuthHeaders]);

  // Fetch daily opportunities
  const fetchDailyOpportunities = useCallback(async (dateValue = dailyDate) => {
    if (!dateValue) return;
    setDailyLoading(true);
    setDailyError('');

    try {
      const params = new URLSearchParams({ date: dateValue });
      const response = await fetch(
        `${API_BASE_URL}/analytics/daily-opportunities?${params.toString()}`,
        { headers: getAuthHeaders() }
      );

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setDailyData(await response.json());
    } catch (err) {
      console.error('Error fetching daily opportunities:', err);
      setDailyError(err.message || 'Unable to load daily opportunities.');
      setDailyData(null);
    } finally {
      setDailyLoading(false);
    }
  }, [dailyDate, getAuthHeaders]);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    if (!token) return;
    setNotifsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/notifications`, {
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        const data = await response.json();
        setNotifications(data.notifications || []);
        setUnreadNotifsCount(data.unread_count || 0);
      }
    } catch (err) {
      console.error('Error fetching notifications:', err);
    } finally {
      setNotifsLoading(false);
    }
  }, [token, getAuthHeaders]);

  // Refresh entire workspace
  const refreshDashboard = useCallback(async () => {
    await Promise.allSettled([
      fetchProjects(0, false),
      fetchAllProjects(),
      fetchSources(),
      fetchScrapingRuns(),
      fetchSchedules(),
      fetchAnalytics(),
      fetchDailyOpportunities(dailyDate),
      fetchNotifications(),
    ]);
  }, [
    fetchProjects,
    fetchAllProjects,
    fetchSources,
    fetchScrapingRuns,
    fetchSchedules,
    fetchAnalytics,
    fetchDailyOpportunities,
    fetchNotifications,
    dailyDate,
  ]);

  // Initial authentication verification if token exists
  useEffect(() => {
    if (token) {
      fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (res.ok) return res.json();
          throw new Error('Session expired');
        })
        .then((userData) => {
          setCurrentUser(userData);
          localStorage.setItem('scrapescout_user', JSON.stringify(userData));
        })
        .catch(() => {
          setToken('');
          setCurrentUser(null);
          localStorage.removeItem('scrapescout_token');
          localStorage.removeItem('scrapescout_user');
        });
    }
  }, [token]);

  // Trigger dashboard refresh on login
  useEffect(() => {
    if (isLoggedIn) {
      refreshDashboard();
    }
  }, [isLoggedIn, refreshDashboard]);

  // Default schedule source selection to first active source
  useEffect(() => {
    if (!schedSourceId && sources.length > 0) {
      const truelancer = sources.find(
        (s) => (s.name || '').trim().toLowerCase() === 'truelancer'
      );
      setSchedSourceId((truelancer || sources[0]).id);
    }
  }, [sources, schedSourceId]);

  // Debounced search & filter re-fetch
  useEffect(() => {
    if (!isLoggedIn) return undefined;
    const timeoutId = window.setTimeout(() => {
      fetchProjects(0, false);
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [
    isLoggedIn,
    searchTerm,
    selectedType,
    selectedCategory,
    selectedTechnology,
    selectedLocation,
    selectedSourceId,
    postedFrom,
    postedTo,
    fetchProjects,
  ]);

  // Handle Authentication (Login / Register)
  const handleAuthSubmit = async (event) => {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError('');

    const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
    const body = authMode === 'login'
      ? { email: authEmail.trim(), password: authPassword }
      : { email: authEmail.trim(), password: authPassword, full_name: authFullName.trim() || undefined };

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const data = await response.json();
      setToken(data.access_token);
      setCurrentUser(data.user);
      localStorage.setItem('scrapescout_token', data.access_token);
      localStorage.setItem('scrapescout_user', JSON.stringify(data.user));

      setAuthPassword('');
      setSuccessMessage(`Welcome back, ${data.user.full_name || data.user.email}!`);
    } catch (err) {
      console.error('Auth error:', err);
      setAuthError(err.message || 'Authentication failed.');
    } finally {
      setAuthLoading(false);
    }
  };

  // Handle Logout
  const handleLogout = async () => {
    try {
      if (token) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: getAuthHeaders(),
        });
      }
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setToken('');
      setCurrentUser(null);
      localStorage.removeItem('scrapescout_token');
      localStorage.removeItem('scrapescout_user');
      setProjects([]);
      setAllProjects([]);
      setSources([]);
      setScrapingRuns([]);
      setAnalytics(null);
      setDailyData(null);
      setNotifications([]);
      setLastFetchResult(null);
      setFetchError('');
      setError('');
      setSuccessMessage('');
    }
  };

  // Handle Manual Truelancer Fetch
  const handleManualTruelancerFetch = async () => {
    if (fetchingTruelancer) return;

    setFetchingTruelancer(true);
    setFetchError('');
    setError('');
    setSuccessMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}/scrape/truelancer/manual`, {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const result = await response.json();
      setLastFetchResult(result);
      setSuccessMessage(
        `Truelancer fetch finished (${result.status}): ${result.records_found} found, ${result.inserted} inserted.`
      );
      await refreshDashboard();
    } catch (err) {
      console.error('Manual Truelancer fetch error:', err);
      setFetchError(err.message || 'Manual Truelancer fetch failed.');
    } finally {
      setFetchingTruelancer(false);
    }
  };

  // Handle Notifications (Mark as Read)
  const handleMarkNotifAsRead = async (notifId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications/${notifId}/read`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        setNotifications((prev) =>
          prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
        );
        setUnreadNotifsCount((count) => Math.max(0, count - 1));
      }
    } catch (err) {
      console.error('Error marking notification as read:', err);
    }
  };

  // Handle Notifications (Mark All as Read)
  const handleMarkAllNotifsRead = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/notifications/read-all`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (response.ok) {
        setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
        setUnreadNotifsCount(0);
      }
    } catch (err) {
      console.error('Error marking all notifications as read:', err);
    }
  };

  // Handle Exports (CSV and Excel)
  const handleExport = async (format = 'csv') => {
    setExportingFormat(format);
    setError('');

    try {
      const params = buildProjectQueryParams(0, true);
      params.set('format', format);

      const response = await fetch(`${API_BASE_URL}/projects/export?${params.toString()}`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const blob = await response.blob();
      if (blob.size === 0) {
        alert('There are no projects matching the active filters to export.');
        return;
      }

      const dateStr = new Date().toISOString().slice(0, 10);
      const filename = `scrapescout-projects-${dateStr}.${format === 'excel' ? 'xlsx' : 'csv'}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setSuccessMessage(`Successfully exported ${filename}`);
    } catch (err) {
      console.error('Export error:', err);
      setError(err.message || 'Unable to export projects.');
    } finally {
      setExportingFormat(null);
    }
  };

  // Handle Add Project
  const handleAddProject = async (event) => {
    event.preventDefault();
    setAddingProject(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        method: 'POST',
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          title: newTitle.trim(),
          original_url: newUrl.trim(),
          description: newDescription.trim(),
        }),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setNewTitle('');
      setNewUrl('');
      setNewDescription('');
      setSuccessMessage('Opportunity successfully added!');
      await refreshDashboard();
    } catch (err) {
      console.error('Error adding project:', err);
      setError(err.message || 'Could not add the project record.');
    } finally {
      setAddingProject(false);
    }
  };

  // Handle Delete Project (Admin only)
  const handleDeleteProject = async (id) => {
    if (!isAdmin) {
      alert('Administrator privileges are required to delete projects.');
      return;
    }
    if (!window.confirm('Delete this project opportunity permanently?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/projects/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setSuccessMessage('Project opportunity deleted.');
      await refreshDashboard();
    } catch (err) {
      console.error('Error deleting project:', err);
      setError(err.message || 'Could not delete the project.');
    }
  };

  // Reset all search and filter fields
  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedType('All');
    setSelectedCategory('All');
    setSelectedTechnology('All');
    setSelectedLocation('');
    setSelectedSourceId('All');
    setPostedFrom('');
    setPostedTo('');
  };

  // Load more pagination
  const loadMoreProjects = () => {
    if (!loading && hasMore) {
      fetchProjects(offset + PAGE_SIZE, true);
    }
  };

  // Schedule Management Handlers
  const resetScheduleForm = () => {
    setEditingScheduleId(null);
    setSchedName('Truelancer Recurring Sync');
    setSchedFrequency('daily');
    setSchedTimeOfDay('09:00');
    setSchedWeekdays([0, 2, 4]);
    setSchedDayOfMonth(1);
    setSchedCustomType('cron');
    setSchedCronExpr('0 */6 * * *');
    setSchedIntervalMinutes(60);
    setSchedTimezone('Asia/Kolkata');
    setSchedMaxPages(3);
    setSchedMinInterval(1.0);
    setSchedEnabled(true);
    setScheduleError('');
  };

  const handleEditSchedule = (sched) => {
    setEditingScheduleId(sched.id);
    setSchedSourceId(sched.source_id);
    setSchedName(sched.name);
    setSchedFrequency(sched.frequency || 'daily');
    setSchedTimeOfDay(sched.time_of_day || '09:00');
    setSchedWeekdays(Array.isArray(sched.weekdays) && sched.weekdays.length ? sched.weekdays : [0]);
    setSchedDayOfMonth(sched.day_of_month || 1);
    if (sched.cron_expression) {
      setSchedCustomType('cron');
      setSchedCronExpr(sched.cron_expression);
    } else if (sched.interval_minutes) {
      setSchedCustomType('interval');
      setSchedIntervalMinutes(sched.interval_minutes);
    }
    setSchedTimezone(sched.timezone || 'Asia/Kolkata');
    setSchedMaxPages(sched.max_pages || 3);
    setSchedMinInterval(sched.min_request_interval ?? 1.0);
    setSchedEnabled(Boolean(sched.is_enabled));
    setScheduleError('');
  };

  const handleToggleWeekday = (dayVal) => {
    setSchedWeekdays((prev) =>
      prev.includes(dayVal)
        ? prev.filter((d) => d !== dayVal)
        : [...prev, dayVal].sort((a, b) => a - b)
    );
  };

  const handleSaveSchedule = async (event) => {
    event.preventDefault();
    setSavingSchedule(true);
    setScheduleError('');

    const payload = {
      source_id: schedSourceId,
      name: schedName.trim(),
      frequency: schedFrequency,
      time_of_day: schedTimeOfDay,
      weekdays: schedFrequency === 'weekly' ? schedWeekdays : null,
      day_of_month: schedFrequency === 'monthly' ? Number(schedDayOfMonth) : null,
      cron_expression:
        schedFrequency === 'custom' && schedCustomType === 'cron'
          ? schedCronExpr.trim()
          : null,
      interval_minutes:
        schedFrequency === 'custom' && schedCustomType === 'interval'
          ? Number(schedIntervalMinutes)
          : null,
      timezone: schedTimezone.trim() || 'Asia/Kolkata',
      max_pages: Number(schedMaxPages),
      min_request_interval: Number(schedMinInterval),
      is_enabled: schedEnabled,
    };

    try {
      const url = editingScheduleId
        ? `${API_BASE_URL}/schedules/${editingScheduleId}`
        : `${API_BASE_URL}/schedules`;
      const method = editingScheduleId ? 'PATCH' : 'POST';

      const response = await fetch(url, {
        method,
        headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setSuccessMessage(editingScheduleId ? 'Schedule updated.' : 'Schedule created.');
      resetScheduleForm();
      await Promise.allSettled([fetchSchedules(), fetchAnalytics()]);
    } catch (err) {
      setScheduleError(err.message || 'Unable to save schedule.');
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleToggleSchedule = async (sched) => {
    const action = sched.is_enabled ? 'pause' : 'resume';
    try {
      const response = await fetch(`${API_BASE_URL}/schedules/${sched.id}/${action}`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }
      setSuccessMessage(`Schedule ${sched.is_enabled ? 'paused' : 'resumed'}.`);
      await Promise.allSettled([fetchSchedules(), fetchAnalytics()]);
    } catch (err) {
      setScheduleError(err.message || 'Unable to update schedule status.');
    }
  };

  const handleDeleteSchedule = async (schedId) => {
    if (!window.confirm('Delete this recurring schedule?')) return;
    try {
      const response = await fetch(`${API_BASE_URL}/schedules/${schedId}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }
      setSuccessMessage('Schedule deleted.');
      await Promise.allSettled([fetchSchedules(), fetchAnalytics()]);
    } catch (err) {
      setScheduleError(err.message || 'Unable to delete schedule.');
    }
  };

  // Derived filter metadata
  const projectTypes = useMemo(() => {
    const types = new Set(
      allProjects
        .map((p) => p.project_type)
        .filter((val) => typeof val === 'string' && val.trim())
    );
    return Array.from(types).sort();
  }, [allProjects]);

  const categories = useMemo(() => {
    const cats = new Set(
      allProjects
        .map((p) => p.category)
        .filter((val) => typeof val === 'string' && val.trim())
    );
    return Array.from(cats).sort();
  }, [allProjects]);

  const technologies = useMemo(() => {
    const techs = new Set();
    allProjects.forEach((p) => {
      const req = p.required_technologies || p.required_technology;
      if (Array.isArray(req)) {
        req.forEach((t) => t && techs.add(String(t).trim()));
      } else if (typeof req === 'string' && req.trim()) {
        req.split(',').forEach((t) => techs.add(t.trim()));
      }
    });
    return Array.from(techs).sort();
  }, [allProjects]);

  const sourceNameById = useMemo(() => {
    const lookup = {};
    sources.forEach((src) => {
      if (src.id) lookup[src.id] = src.name;
    });
    return lookup;
  }, [sources]);

  const truelancerSource = useMemo(() => {
    return sources.find(
      (s) => (s.name || '').trim().toLowerCase() === 'truelancer'
    ) || null;
  }, [sources]);

  const typeCounts = analytics?.projects_by_type || {};
  const runCounts = analytics?.scraping_runs || {};
  const duplicateProjectsCount = allProjects.filter((p) => p.is_duplicate === true).length;
  const upcomingSchedules = analytics?.upcoming_schedules || [];

  const stats = [
    { label: 'Total Projects', value: analytics?.total_projects ?? '—' },
    { label: 'Discovered Today', value: analytics?.projects_today ?? '—' },
    { label: 'Inserted Today', value: analytics?.inserted_today ?? analytics?.projects_today ?? '—' },
    { label: 'Duplicates Skipped', value: analytics?.duplicates_skipped ?? duplicateProjectsCount },
    { label: 'Active Sources', value: analytics?.active_sources_count ?? sources.length },
    { label: 'Web Projects', value: typeCounts.Web ?? 0 },
    { label: 'App Projects', value: typeCounts.App ?? 0 },
    { label: 'Web & App Projects', value: typeCounts.Both ?? 0 },
  ];

  const renderProjectCard = (project) => (
    <article key={project.id} className="project-card">
      <div>
        <h4>{formatField(project.title)}</h4>
        <p className="project-desc">{formatField(project.description)}</p>

        <div className="project-meta-list">
          <p><strong>Project Type:</strong> {formatField(project.project_type)}</p>
          <p><strong>Required Technologies:</strong> {formatField(project.required_technologies ?? project.required_technology)}</p>
          <p><strong>Client:</strong> {formatField(project.client_name)}</p>
          <p><strong>Location:</strong> {formatField(project.location)}</p>
          <p>
            <strong>Budget:</strong>{' '}
            {project.budget == null || project.budget === ''
              ? 'Not specified'
              : `${formatField(project.budget)} ${project.currency || ''}`.trim()}
          </p>
          <p><strong>Category:</strong> {formatField(project.category)}</p>
          <p><strong>Confidence Score:</strong> {formatField(project.confidence_score)}</p>
          <p><strong>Posted Date:</strong> {formatField(project.posted_date)}</p>
          <p>
            <strong>Duplicate:</strong>{' '}
            {project.is_duplicate ? 'Yes' : 'No'}
          </p>
        </div>
      </div>

      <div className="card-footer">
        {project.original_url && (
          <a
            href={project.original_url}
            target="_blank"
            rel="noreferrer"
            className="link-btn"
          >
            View Source ↗
          </a>
        )}

        {isAdmin ? (
          <button
            type="button"
            className="delete-btn"
            onClick={() => handleDeleteProject(project.id)}
          >
            Delete
          </button>
        ) : (
          <span className="muted-text" style={{ fontSize: '0.75rem' }}>
            Viewer Access
          </span>
        )}
      </div>
    </article>
  );

  const renderManualFetchPanel = () => (
    <section className="fetch-hero-panel" aria-label="Manual Truelancer Fetch">
      <div className="fetch-hero-top">
        <div className="fetch-hero-copy">
          <h3>Truelancer Live Fetch</h3>
          <p>
            Run the configured Truelancer scraping pipeline on demand using ScraperAPI,
            keyword classification, deduplication, and Supabase persistence.
          </p>
        </div>

        <div className="fetch-actions">
          <button
            type="button"
            className="primary-btn"
            onClick={handleManualTruelancerFetch}
            disabled={fetchingTruelancer}
            title="Fetch projects from Truelancer"
          >
            {fetchingTruelancer ? 'Fetching from Truelancer...' : 'Fetch from Truelancer'}
          </button>
        </div>
      </div>

      {fetchError && (
        <div className="error-banner" role="alert">
          <span>{fetchError}</span>
          <button type="button" onClick={() => setFetchError('')} aria-label="Dismiss fetch error">×</button>
        </div>
      )}

      {lastFetchResult && (
        <div className="fetch-summary-grid" aria-label="Manual fetch summary">
          <div className="fetch-metric">
            <span>Run Status</span>
            <strong>{lastFetchResult.status}</strong>
          </div>
          <div className="fetch-metric">
            <span>Records Found</span>
            <strong>{lastFetchResult.records_found}</strong>
          </div>
          <div className="fetch-metric">
            <span>Projects Inserted</span>
            <strong>{lastFetchResult.inserted}</strong>
          </div>
          <div className="fetch-metric">
            <span>Duplicates Skipped</span>
            <strong>{lastFetchResult.duplicate_skipped}</strong>
          </div>
          <div className="fetch-metric">
            <span>Irrelevant Skipped</span>
            <strong>{lastFetchResult.irrelevant_skipped}</strong>
          </div>
          <div className="fetch-metric">
            <span>Invalid / Missing URL</span>
            <strong>
              {(lastFetchResult.missing_url_skipped || 0) + (lastFetchResult.invalid_skipped || 0)}
            </strong>
          </div>
          <div className="fetch-metric">
            <span>Failed Submissions</span>
            <strong>{lastFetchResult.failed}</strong>
          </div>
        </div>
      )}
    </section>
  );

  // If not logged in, render the Authentication Screen
  if (!isLoggedIn) {
    return (
      <div className="login-container" data-theme={theme}>
        <div className="login-theme-corner">
          <button
            type="button"
            className="theme-toggle-btn"
            onClick={toggleTheme}
            aria-label="Toggle color theme"
          >
            {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>

        <div className="login-card">
          <div className="login-brand">
            <div className="brand-icon">SS</div>
            <h2>ScrapeScout</h2>
          </div>
          <p className="login-subtitle">
            Sign in to discover and manage freelance project opportunities
          </p>

          <div className="auth-tabs" role="tablist">
            <button
              type="button"
              className={`auth-tab ${authMode === 'login' ? 'active' : ''}`}
              onClick={() => { setAuthMode('login'); setAuthError(''); }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-tab ${authMode === 'register' ? 'active' : ''}`}
              onClick={() => { setAuthMode('register'); setAuthError(''); }}
            >
              Register
            </button>
          </div>

          {authError && <div className="error-text" role="alert">{authError}</div>}

          <form onSubmit={handleAuthSubmit}>
            {authMode === 'register' && (
              <div className="form-group">
                <input
                  type="text"
                  placeholder="Full Name"
                  value={authFullName}
                  onChange={(e) => setAuthFullName(e.target.value)}
                />
              </div>
            )}

            <div className="form-group">
              <input
                type="email"
                placeholder="Email address"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <input
                type="password"
                placeholder="Password (minimum 6 characters)"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <button type="submit" className="submit-btn" disabled={authLoading}>
              {authLoading ? 'Authenticating...' : authMode === 'login' ? 'Access Workspace' : 'Create Account'}
            </button>
          </form>

          <p className="login-note">
            Default credentials: <code>admin@scrapescout.com</code> (Admin) or <code>viewer@scrapescout.com</code> (Viewer).
          </p>
        </div>
      </div>
    );
  }

  const activeMeta = PAGE_META[activePage] || PAGE_META.dashboard;

  return (
    <div className="app-shell" data-theme={theme}>
      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileNavOpen ? 'open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-brand">
          <div className="brand-icon">SS</div>
          <div>
            <h2>ScrapeScout</h2>
            <span>Lead Discovery</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => {
                setActivePage(item.id);
                setMobileNavOpen(false);
              }}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-source-pill">
            <span>
              <span className={`status-dot ${truelancerSource ? 'online' : 'offline'}`} />
              Truelancer
            </span>
            <strong>{truelancerSource ? 'Connected' : 'Pending'}</strong>
          </div>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="main-workspace">
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu-btn"
              onClick={() => setMobileNavOpen((open) => !open)}
              aria-label="Toggle navigation menu"
            >
              ☰
            </button>
            <div className="page-title-block">
              <h1>{activeMeta.title}</h1>
              <p>{activeMeta.subtitle}</p>
            </div>
          </div>

          <div className="user-controls">
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={toggleTheme}
              aria-label="Toggle color theme"
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>

            {/* Notifications Bell */}
            <div className="notif-container">
              <button
                type="button"
                className="notif-btn"
                onClick={() => setShowNotifications(!showNotifications)}
                aria-label="View notifications"
              >
                🔔
                {unreadNotifsCount > 0 && (
                  <span className="notif-badge">{unreadNotifsCount}</span>
                )}
              </button>

              {showNotifications && (
                <div className="notif-dropdown">
                  <div className="notif-header">
                    <h4>Notifications ({notifications.length})</h4>
                    {unreadNotifsCount > 0 && (
                      <button
                        type="button"
                        className="mark-all-btn"
                        onClick={handleMarkAllNotifsRead}
                      >
                        Mark all as read
                      </button>
                    )}
                  </div>

                  {notifsLoading ? (
                    <p className="empty-state">Loading notifications...</p>
                  ) : notifications.length === 0 ? (
                    <p className="empty-state">No notifications yet.</p>
                  ) : (
                    <div className="notif-list">
                      {notifications.map((notif) => (
                        <div
                          key={notif.id}
                          className={`notif-card ${!notif.is_read ? 'unread' : ''}`}
                        >
                          <div className="notif-card-header">
                            <span className="notif-title">{notif.title}</span>
                            {!notif.is_read && (
                              <button
                                type="button"
                                className="notif-mark-btn"
                                onClick={() => handleMarkNotifAsRead(notif.id)}
                              >
                                Mark read
                              </button>
                            )}
                          </div>
                          <p className="notif-message">{notif.message}</p>
                          <div className="notif-meta">
                            <span>{notif.type || 'info'}</span>
                            <span>
                              {notif.created_at
                                ? new Date(notif.created_at).toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                  })
                                : ''}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="user-badge">
              <span>{currentUser.full_name || currentUser.email}</span>
              <span className={`role-badge ${currentUser.role || 'viewer'}`}>
                {currentUser.role || 'viewer'}
              </span>
            </div>

            <button type="button" className="logout-btn" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-content">
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button>
            </div>
          )}

          {successMessage && (
            <div className="success-banner" role="status">
              <span>{successMessage}</span>
              <button type="button" onClick={() => setSuccessMessage('')} aria-label="Dismiss message">×</button>
            </div>
          )}

          {/* ==================== PAGE: DASHBOARD ==================== */}
          {activePage === 'dashboard' && (
            <>
              {renderManualFetchPanel()}

              <section className="stats-grid" aria-label="Dashboard statistics">
                {stats.map((stat) => (
                  <div className="stat-card" key={stat.label}>
                    <p>{stat.label}</p>
                    <h2>{analyticsLoading && stat.value === '—' ? '...' : stat.value}</h2>
                  </div>
                ))}
              </section>

              <div className="dashboard-two-col">
                {/* Opportunities by Active Source */}
                <section className="panel">
                  <div className="panel-header">
                    <h3 className="panel-title">Opportunities by Active Source</h3>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => setActivePage('sources')}
                    >
                      View Sources
                    </button>
                  </div>

                  {analytics?.projects_by_source?.length ? (
                    <div className="source-list">
                      {analytics.projects_by_source.map((source) => (
                        <div className="source-item" key={source.source_name}>
                          <span>{source.source_name}</span>
                          <strong>{source.project_count}</strong>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="muted-text">
                      {analyticsLoading ? 'Loading source statistics...' : 'No active source statistics available.'}
                    </p>
                  )}
                </section>

                {/* Recent Scraping Activity */}
                <section className="panel">
                  <div className="panel-header">
                    <h3 className="panel-title">Recent Scraping Activity</h3>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={() => setActivePage('activity')}
                    >
                      View All Runs
                    </button>
                  </div>

                  <div className="source-list">
                    <div className="source-item">
                      <span>Total Runs</span>
                      <strong>{runCounts.total ?? 0}</strong>
                    </div>
                    <div className="source-item">
                      <span>Successful</span>
                      <span className="badge badge-success">{runCounts.successful ?? 0}</span>
                    </div>
                    <div className="source-item">
                      <span>Failed</span>
                      <span className="badge badge-danger">{runCounts.failed ?? 0}</span>
                    </div>
                    <div className="source-item">
                      <span>Running</span>
                      <span className="badge badge-info">{runCounts.running ?? 0}</span>
                    </div>
                  </div>
                </section>
              </div>

              {/* Upcoming Scheduled Executions */}
              <section className="panel" aria-label="Upcoming Scheduled Executions">
                <div className="panel-header">
                  <h3 className="panel-title">
                    Upcoming Scheduled Executions
                    <span className={`badge ${analytics?.scheduler_enabled ? 'badge-success' : 'badge-neutral'}`}>
                      {analytics?.scheduler_enabled ? 'Auto-Runner Active' : 'Auto-Runner Disabled'}
                    </span>
                  </h3>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setActivePage('scheduler')}
                  >
                    Manage Schedules
                  </button>
                </div>

                {upcomingSchedules.length === 0 ? (
                  <p className="empty-state">
                    No active recurring schedules configured. Create one in the Scheduler tab.
                  </p>
                ) : (
                  <div className="source-list">
                    {upcomingSchedules.map((item) => (
                      <div className="source-item" key={item.id}>
                        <div>
                          <strong>{item.name}</strong>
                          <p className="muted-text" style={{ fontSize: '0.8rem' }}>
                            {sourceNameById[item.source_id] || 'Truelancer'} · {item.frequency} ({item.timezone})
                          </p>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <span className="badge badge-info">
                            Next: {formatTimestamp(item.next_run_at)}
                          </span>
                          {item.last_run_status && (
                            <p className="muted-text" style={{ fontSize: '0.75rem', marginTop: 4 }}>
                              Last: {item.last_run_status}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Daily Project Opportunities (Asia/Kolkata) */}
              <section className="panel">
                <div className="daily-heading">
                  <div>
                    <h3 className="panel-title">{dailyData?.title || 'Daily Project Opportunities'}</h3>
                    <p className="muted-text">
                      Consolidated non-duplicate opportunities compiled per Asia/Kolkata day.
                    </p>
                  </div>

                  <div className="date-control">
                    <label htmlFor="dailyDate">Select Date</label>
                    <input
                      id="dailyDate"
                      type="date"
                      value={dailyDate}
                      onChange={(e) => {
                        setDailyDate(e.target.value);
                        if (e.target.value) fetchDailyOpportunities(e.target.value);
                      }}
                    />
                  </div>
                </div>

                {dailyLoading ? (
                  <p className="empty-state">Loading daily opportunities...</p>
                ) : dailyError ? (
                  <p className="error-text">{dailyError}</p>
                ) : dailyData ? (
                  <>
                    <div className="daily-meta">
                      <strong>{dailyData.total_projects} opportunities</strong>
                      <span>{dailyData.is_historical ? 'Historical Results' : "Today's Discovered Leads"}</span>
                      <span>{dailyData.timezone}</span>
                    </div>

                    {dailyData.projects?.length ? (
                      <div className="daily-project-list">
                        {dailyData.projects.slice(0, 6).map((project) => (
                          <article className="daily-project" key={project.id}>
                            <div>
                              <h4>{formatField(project.title)}</h4>
                              <p>{formatField(project.description)}</p>
                              <span className="daily-project-type">{formatField(project.project_type)}</span>
                            </div>
                            {project.original_url && (
                              <a href={project.original_url} target="_blank" rel="noreferrer" className="link-btn">
                                View Source ↗
                              </a>
                            )}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="empty-state">No non-duplicate opportunities were recorded for this date.</p>
                    )}
                  </>
                ) : (
                  <p className="empty-state">Select a calendar date to view its compiled opportunities.</p>
                )}
              </section>

              {/* Recent Opportunities Preview */}
              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    Recent Opportunities Preview
                    <span className="count-badge">{projects.length}</span>
                  </h3>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => setActivePage('projects')}
                  >
                    Browse All Projects
                  </button>
                </div>

                {loading && projects.length === 0 ? (
                  <p className="empty-state">Loading discovered project opportunities...</p>
                ) : projects.length === 0 ? (
                  <p className="empty-state">No project opportunities available yet.</p>
                ) : (
                  <div className="projects-grid">
                    {projects.slice(0, 6).map(renderProjectCard)}
                  </div>
                )}
              </section>
            </>
          )}

          {/* ==================== PAGE: PROJECTS ==================== */}
          {activePage === 'projects' && (
            <div className="projects-layout">
              <aside className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">Add Opportunity</h3>
                </div>

                <form onSubmit={handleAddProject}>
                  <div className="form-group">
                    <label htmlFor="newTitle">Project Title *</label>
                    <input
                      id="newTitle"
                      type="text"
                      placeholder="e.g. Full-stack React & FastAPI Developer"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="newUrl">Original URL *</label>
                    <input
                      id="newUrl"
                      type="url"
                      placeholder="https://example.com/project/opportunity-123"
                      value={newUrl}
                      onChange={(e) => setNewUrl(e.target.value)}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="newDescription">Description</label>
                    <textarea
                      id="newDescription"
                      placeholder="Project overview, requirements, deliverables..."
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                    />
                  </div>

                  <button type="submit" className="submit-btn" disabled={addingProject}>
                    {addingProject ? 'Adding Record...' : '+ Add Opportunity'}
                  </button>
                </form>
              </aside>

              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    <span>Project Listings</span>
                    <span className="count-badge">
                      {projects.length}{hasMore ? '+' : ''} displayed
                    </span>
                  </h3>
                </div>

                <div className="form-group">
                  <label htmlFor="projectSearch">Search Title & Description</label>
                  <input
                    id="projectSearch"
                    type="text"
                    placeholder="Search keyword (e.g. React, Python, Mobile, API)..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <div className="filter-bar">
                  <div className="filters-grid-advanced">
                    <div className="form-group">
                      <label htmlFor="filterType">Project Type</label>
                      <select
                        id="filterType"
                        value={selectedType}
                        onChange={(e) => setSelectedType(e.target.value)}
                      >
                        <option value="All">All Types</option>
                        {projectTypes.length > 0 ? (
                          projectTypes.map((t) => (
                            <option key={t} value={t}>{t}</option>
                          ))
                        ) : (
                          <>
                            <option value="Web">Web</option>
                            <option value="App">App</option>
                            <option value="Both">Web & App (Both)</option>
                          </>
                        )}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="filterCategory">Category</label>
                      <select
                        id="filterCategory"
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                      >
                        <option value="All">All Categories</option>
                        {categories.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="filterTech">Technology</label>
                      <select
                        id="filterTech"
                        value={selectedTechnology}
                        onChange={(e) => setSelectedTechnology(e.target.value)}
                      >
                        <option value="All">All Technologies</option>
                        {technologies.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="filterSource">Source</label>
                      <select
                        id="filterSource"
                        value={selectedSourceId}
                        onChange={(e) => setSelectedSourceId(e.target.value)}
                      >
                        <option value="All">All Sources</option>
                        {sources.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="filterLocation">Location</label>
                      <input
                        id="filterLocation"
                        type="text"
                        placeholder="e.g. Remote, India, US"
                        value={selectedLocation}
                        onChange={(e) => setSelectedLocation(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="postedFrom">Posted From</label>
                      <input
                        id="postedFrom"
                        type="date"
                        value={postedFrom}
                        onChange={(e) => setPostedFrom(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="postedTo">Posted To</label>
                      <input
                        id="postedTo"
                        type="date"
                        value={postedTo}
                        onChange={(e) => setPostedTo(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="filters-actions">
                    <button
                      type="button"
                      className="reset-btn"
                      onClick={handleResetFilters}
                    >
                      Clear Filters
                    </button>

                    <div className="results-info">
                      Matching Results: <strong>{projects.length}</strong>
                    </div>

                    <div className="export-group">
                      <button
                        type="button"
                        className="export-btn-csv"
                        onClick={() => handleExport('csv')}
                        disabled={Boolean(exportingFormat)}
                      >
                        {exportingFormat === 'csv' ? 'Exporting...' : 'Export CSV'}
                      </button>
                      <button
                        type="button"
                        className="export-btn-excel"
                        onClick={() => handleExport('excel')}
                        disabled={Boolean(exportingFormat)}
                      >
                        {exportingFormat === 'excel' ? 'Exporting...' : 'Export Excel'}
                      </button>
                    </div>
                  </div>
                </div>

                {loading && projects.length === 0 ? (
                  <p className="empty-state">Loading discovered project opportunities...</p>
                ) : projects.length === 0 ? (
                  <p className="empty-state">No project opportunities match the active search and filter criteria.</p>
                ) : (
                  <>
                    <div className="projects-grid">
                      {projects.map(renderProjectCard)}
                    </div>

                    {hasMore && (
                      <div className="load-more-row">
                        <button
                          type="button"
                          className="load-more-btn"
                          onClick={loadMoreProjects}
                          disabled={loading}
                        >
                          {loading ? 'Loading...' : 'Load More Projects'}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </section>
            </div>
          )}

          {/* ==================== PAGE: SOURCES ==================== */}
          {activePage === 'sources' && (
            <>
              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">Connected & Active Sources</h3>
                  <button
                    type="button"
                    className="primary-btn"
                    onClick={handleManualTruelancerFetch}
                    disabled={fetchingTruelancer}
                  >
                    {fetchingTruelancer ? 'Fetching from Truelancer...' : 'Fetch from Truelancer'}
                  </button>
                </div>

                {sources.length === 0 ? (
                  <p className="empty-state">No active sources are currently configured.</p>
                ) : (
                  <div className="sources-cards-grid">
                    {sources.map((src) => (
                      <div className="source-card" key={src.id}>
                        <div className="panel-header" style={{ marginBottom: 0 }}>
                          <strong>{src.name}</strong>
                          <span className="badge badge-success">Connected · Active</span>
                        </div>
                        <p className="muted-text">{src.base_url}</p>
                        <div className="project-meta-list">
                          <p><strong>Scraping Type:</strong> {src.scraping_type || 'HTML / JSON'}</p>
                          <p><strong>Interval:</strong> {src.frequency_minutes ? `${src.frequency_minutes} mins` : 'On-demand'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">Planned Freelance Sources</h3>
                  <span className="badge badge-neutral">Roadmap</span>
                </div>
                <p className="muted-text" style={{ marginBottom: 16 }}>
                  These freelance platforms are planned for future integration and are not yet connected.
                </p>

                <div className="sources-cards-grid">
                  {PLANNED_SOURCES.map((src) => (
                    <div className="source-card" key={src.name}>
                      <div className="panel-header" style={{ marginBottom: 0 }}>
                        <strong>{src.name}</strong>
                        <span className="badge badge-warning">Planned · Not Connected</span>
                      </div>
                      <p className="muted-text">{src.description}</p>
                      <p className="muted-text" style={{ fontSize: '0.78rem' }}>{src.url}</p>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}

          {/* ==================== PAGE: SCHEDULER ==================== */}
          {activePage === 'scheduler' && (
            <>
              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    Background Scheduler Status
                    <span className={`badge ${schedulerStatus.scheduler_enabled ? 'badge-success' : 'badge-warning'}`}>
                      {schedulerStatus.scheduler_enabled ? 'Enabled (SCHEDULER_ENABLED=true)' : 'Disabled (SCHEDULER_ENABLED=false)'}
                    </span>
                  </h3>
                  <span className="muted-text">
                    Default Timezone: {schedulerStatus.default_timezone || 'Asia/Kolkata'}
                  </span>
                </div>
                <p className="muted-text">
                  Schedules saved here are stored persistently in Supabase and calculate real next-execution times.
                  {!schedulerStatus.scheduler_enabled && ' Background execution remains paused until SCHEDULER_ENABLED=true is configured on the backend.'}
                </p>
              </section>

              {scheduleError && (
                <div className="error-banner" role="alert">
                  <span>{scheduleError}</span>
                  <button type="button" onClick={() => setScheduleError('')} aria-label="Dismiss schedule error">×</button>
                </div>
              )}

              <div className="scheduler-layout">
                <aside className="panel">
                  <div className="panel-header">
                    <h3 className="panel-title">
                      {editingScheduleId ? 'Edit Schedule' : 'Create Schedule'}
                    </h3>
                    {editingScheduleId && (
                      <button type="button" className="reset-btn" onClick={resetScheduleForm}>
                        Cancel
                      </button>
                    )}
                  </div>

                  <form onSubmit={handleSaveSchedule}>
                    <div className="form-group">
                      <label htmlFor="schedName">Schedule Name *</label>
                      <input
                        id="schedName"
                        type="text"
                        value={schedName}
                        onChange={(e) => setSchedName(e.target.value)}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="schedSource">Active Source *</label>
                      <select
                        id="schedSource"
                        value={schedSourceId}
                        onChange={(e) => setSchedSourceId(e.target.value)}
                        required
                      >
                        {sources.length === 0 ? (
                          <option value="">No active sources available</option>
                        ) : (
                          sources.map((src) => (
                            <option key={src.id} value={src.id}>
                              {src.name}
                            </option>
                          ))
                        )}
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="schedFrequency">Frequency *</label>
                      <select
                        id="schedFrequency"
                        value={schedFrequency}
                        onChange={(e) => setSchedFrequency(e.target.value)}
                      >
                        <option value="daily">Daily</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                        <option value="custom">Custom</option>
                      </select>
                    </div>

                    {schedFrequency !== 'custom' && (
                      <div className="form-group">
                        <label htmlFor="schedTime">Execution Time (24h) *</label>
                        <input
                          id="schedTime"
                          type="time"
                          value={schedTimeOfDay}
                          onChange={(e) => setSchedTimeOfDay(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {schedFrequency === 'weekly' && (
                      <div className="form-group">
                        <label>Weekdays *</label>
                        <div className="weekday-picker">
                          {WEEKDAY_LABELS.map((day) => (
                            <button
                              key={day.value}
                              type="button"
                              className={`weekday-chip ${schedWeekdays.includes(day.value) ? 'selected' : ''}`}
                              onClick={() => handleToggleWeekday(day.value)}
                            >
                              {day.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {schedFrequency === 'monthly' && (
                      <div className="form-group">
                        <label htmlFor="schedDayOfMonth">Day of Month (1–31) *</label>
                        <input
                          id="schedDayOfMonth"
                          type="number"
                          min="1"
                          max="31"
                          value={schedDayOfMonth}
                          onChange={(e) => setSchedDayOfMonth(e.target.value)}
                          required
                        />
                      </div>
                    )}

                    {schedFrequency === 'custom' && (
                      <>
                        <div className="form-group">
                          <label htmlFor="schedCustomType">Custom Mode</label>
                          <select
                            id="schedCustomType"
                            value={schedCustomType}
                            onChange={(e) => setSchedCustomType(e.target.value)}
                          >
                            <option value="cron">Cron Expression (5-field)</option>
                            <option value="interval">Interval (Minutes)</option>
                          </select>
                        </div>

                        {schedCustomType === 'cron' ? (
                          <div className="form-group">
                            <label htmlFor="schedCron">Cron Expression *</label>
                            <input
                              id="schedCron"
                              type="text"
                              placeholder="0 */6 * * *"
                              value={schedCronExpr}
                              onChange={(e) => setSchedCronExpr(e.target.value)}
                              required
                            />
                          </div>
                        ) : (
                          <div className="form-group">
                            <label htmlFor="schedIntervalMins">Every N Minutes *</label>
                            <input
                              id="schedIntervalMins"
                              type="number"
                              min="1"
                              value={schedIntervalMinutes}
                              onChange={(e) => setSchedIntervalMinutes(e.target.value)}
                              required
                            />
                          </div>
                        )}
                      </>
                    )}

                    <div className="form-group">
                      <label htmlFor="schedTimezone">Timezone</label>
                      <input
                        id="schedTimezone"
                        type="text"
                        value={schedTimezone}
                        onChange={(e) => setSchedTimezone(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="schedMaxPages">Max Pages</label>
                      <input
                        id="schedMaxPages"
                        type="number"
                        min="1"
                        max="20"
                        value={schedMaxPages}
                        onChange={(e) => setSchedMaxPages(e.target.value)}
                      />
                    </div>

                    <div className="form-group">
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <input
                          type="checkbox"
                          checked={schedEnabled}
                          onChange={(e) => setSchedEnabled(e.target.checked)}
                        />
                        Schedule Enabled
                      </label>
                    </div>

                    <button
                      type="submit"
                      className="submit-btn"
                      disabled={savingSchedule || !schedSourceId}
                    >
                      {savingSchedule
                        ? 'Saving...'
                        : editingScheduleId
                        ? 'Update Schedule'
                        : 'Save Schedule'}
                    </button>
                  </form>
                </aside>

                <section className="panel">
                  <div className="panel-header">
                    <h3 className="panel-title">
                      Saved Schedules
                      <span className="count-badge">{schedules.length}</span>
                    </h3>
                    <button
                      type="button"
                      className="secondary-btn"
                      onClick={fetchSchedules}
                      disabled={schedulesLoading}
                    >
                      {schedulesLoading ? 'Refreshing...' : 'Refresh'}
                    </button>
                  </div>

                  {schedulesLoading && schedules.length === 0 ? (
                    <p className="empty-state">Loading schedules...</p>
                  ) : schedules.length === 0 ? (
                    <p className="empty-state">No recurring schedules saved yet.</p>
                  ) : (
                    <div className="schedule-cards">
                      {schedules.map((sched) => (
                        <article className="schedule-card" key={sched.id}>
                          <div className="panel-header" style={{ marginBottom: 0 }}>
                            <div>
                              <strong>{sched.name}</strong>
                              <p className="muted-text" style={{ fontSize: '0.82rem' }}>
                                {sourceNameById[sched.source_id] || 'Truelancer'} · {sched.frequency.toUpperCase()} ({sched.timezone})
                              </p>
                            </div>
                            <span className={`badge ${sched.is_enabled ? 'badge-success' : 'badge-neutral'}`}>
                              {sched.is_enabled ? 'Active' : 'Paused'}
                            </span>
                          </div>

                          <div className="project-meta-list">
                            <p><strong>Next Execution:</strong> {sched.is_enabled ? formatTimestamp(sched.next_run_at) : 'Paused'}</p>
                            <p><strong>Last Execution:</strong> {formatTimestamp(sched.last_run_at)}</p>
                            <p><strong>Last Status:</strong> {sched.last_run_status || 'Never run'}</p>
                            {sched.last_error && (
                              <p style={{ color: 'var(--danger-text)' }}>
                                <strong>Last Error:</strong> {sched.last_error}
                              </p>
                            )}
                          </div>

                          <div className="schedule-card-actions">
                            <button
                              type="button"
                              className="secondary-btn"
                              onClick={() => handleToggleSchedule(sched)}
                            >
                              {sched.is_enabled ? 'Pause' : 'Resume'}
                            </button>
                            <button
                              type="button"
                              className="secondary-btn"
                              onClick={() => handleEditSchedule(sched)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="delete-btn"
                              onClick={() => handleDeleteSchedule(sched.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
              </div>
            </>
          )}

          {/* ==================== PAGE: SCRAPING ACTIVITY ==================== */}
          {activePage === 'activity' && (
            <>
              {renderManualFetchPanel()}

              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">
                    Scraping Run History
                    <span className="count-badge">{scrapingRuns.length}</span>
                  </h3>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={fetchScrapingRuns}
                    disabled={runsLoading}
                  >
                    {runsLoading ? 'Refreshing...' : 'Refresh Runs'}
                  </button>
                </div>

                {runsLoading && scrapingRuns.length === 0 ? (
                  <p className="empty-state">Loading scraping run history...</p>
                ) : scrapingRuns.length === 0 ? (
                  <p className="empty-state">No scraping runs have been recorded yet.</p>
                ) : (
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Status</th>
                          <th>Records Found</th>
                          <th>Started At</th>
                          <th>Completed At</th>
                          <th>Error Details</th>
                        </tr>
                      </thead>
                      <tbody>
                        {scrapingRuns.map((run) => {
                          const statusVal = (run.status || 'UNKNOWN').toUpperCase();
                          const badgeClass =
                            statusVal === 'SUCCESS'
                              ? 'badge-success'
                              : statusVal === 'FAILED'
                              ? 'badge-danger'
                              : 'badge-info';

                          return (
                            <tr key={run.id}>
                              <td>{sourceNameById[run.source_id] || 'Truelancer'}</td>
                              <td>
                                <span className={`badge ${badgeClass}`}>{statusVal}</span>
                              </td>
                              <td>{run.records_found ?? 0}</td>
                              <td>{formatTimestamp(run.started_at)}</td>
                              <td>{formatTimestamp(run.completed_at)}</td>
                              <td className="error-log-cell" title={run.error_log || ''}>
                                {run.error_log || '—'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </>
          )}

          {/* ==================== PAGE: EXPORTS ==================== */}
          {activePage === 'exports' && (
            <section className="panel">
              <div className="panel-header">
                <h3 className="panel-title">Export Freelance Opportunities</h3>
                <span className="count-badge">{projects.length} matching records</span>
              </div>
              <p className="muted-text" style={{ marginBottom: 20 }}>
                Exports respect your active search and filter criteria from the Projects view.
              </p>

              <div className="exports-grid">
                <div className="export-card">
                  <div>
                    <h4 style={{ marginBottom: 8 }}>CSV Export (.csv)</h4>
                    <p className="muted-text">
                      Download formula-safe UTF-8 CSV data for spreadsheets, Python scripts, or CRM imports.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="export-btn-csv"
                    onClick={() => handleExport('csv')}
                    disabled={Boolean(exportingFormat)}
                  >
                    {exportingFormat === 'csv' ? 'Exporting...' : 'Export CSV'}
                  </button>
                </div>

                <div className="export-card">
                  <div>
                    <h4 style={{ marginBottom: 8 }}>Excel Workbook (.xlsx)</h4>
                    <p className="muted-text">
                      Generate a styled Microsoft Excel workbook with formatted headers and auto-sized columns.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="export-btn-excel"
                    onClick={() => handleExport('excel')}
                    disabled={Boolean(exportingFormat)}
                  >
                    {exportingFormat === 'excel' ? 'Exporting...' : 'Export Excel'}
                  </button>
                </div>
              </div>
            </section>
          )}

          {/* ==================== PAGE: SETTINGS ==================== */}
          {activePage === 'settings' && (
            <div className="settings-grid">
              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">User Profile</h3>
                </div>
                <div className="project-meta-list">
                  <p><strong>Full Name:</strong> {currentUser.full_name || 'Not specified'}</p>
                  <p><strong>Email:</strong> {currentUser.email}</p>
                  <p><strong>Role:</strong> {currentUser.role || 'viewer'}</p>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">Appearance & Theme</h3>
                </div>
                <p className="muted-text">
                  Choose between Dark Mode and Light Mode. Your preference is saved automatically in your browser.
                </p>
                <div className="theme-options">
                  <button
                    type="button"
                    className={`theme-choice-btn ${theme === 'dark' ? 'active' : ''}`}
                    onClick={() => setTheme('dark')}
                  >
                    🌙 Dark Mode
                  </button>
                  <button
                    type="button"
                    className={`theme-choice-btn ${theme === 'light' ? 'active' : ''}`}
                    onClick={() => setTheme('light')}
                  >
                    ☀️ Light Mode
                  </button>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <h3 className="panel-title">Workspace Preferences</h3>
                </div>
                <div className="project-meta-list">
                  <p><strong>Daily Compilation Timezone:</strong> Asia/Kolkata</p>
                  <p><strong>Active Scraping Source:</strong> Truelancer (Manual On-Demand)</p>
                  <p><strong>Classification Engine:</strong> Python Keyword Classifier</p>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
