
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import './App.css';

const API_BASE_URL = (
  process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

const PAGE_SIZE = 100;

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');

  const [projects, setProjects] = useState([]);
  const [allProjects, setAllProjects] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const [loading, setLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [addingProject, setAddingProject] = useState(false);
  const [error, setError] = useState('');

  const [title, setTitle] = useState('');
  const [originalUrl, setOriginalUrl] = useState('');
  const [description, setDescription] = useState('');

  const [dailyDate, setDailyDate] = useState(() => {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).format(new Date());

    return parts;
  });
  const [dailyData, setDailyData] = useState(null);
  const [dailyLoading, setDailyLoading] = useState(false);
  const [dailyError, setDailyError] = useState('');

  const formatField = (value) => {
    if (value === null || value === undefined || value === '') {
      return 'Not specified';
    }

    if (Array.isArray(value)) {
      return value.length
        ? value.map((item) =>
            typeof item === 'object' && item !== null
              ? JSON.stringify(item)
              : String(item)
          ).join(', ')
        : 'Not specified';
    }

    if (typeof value === 'object') {
      return JSON.stringify(value);
    }

    return String(value);
  };

  const getErrorMessage = async (response) => {
    try {
      const data = await response.json();
      return data.detail || data.message || `Request failed (${response.status})`;
    } catch {
      return `Request failed (${response.status})`;
    }
  };

  const buildProjectQuery = useCallback((currentOffset = 0) => {
    const params = new URLSearchParams();

    const search = searchTerm.trim();
    if (search) params.set('search', search);
    if (selectedType !== 'All') params.set('project_type', selectedType);
    if (selectedCategory !== 'All') params.set('category', selectedCategory);

    params.set('limit', String(PAGE_SIZE));
    params.set('offset', String(currentOffset));

    return params.toString();
  }, [searchTerm, selectedType, selectedCategory]);

  const fetchAllProjects = useCallback(async () => {
    const response = await fetch(`${API_BASE_URL}/projects`);

    if (!response.ok) {
      throw new Error(await getErrorMessage(response));
    }

    const data = await response.json();
    setAllProjects(Array.isArray(data) ? data : []);
  }, []);

  const fetchProjects = useCallback(async (currentOffset = 0, append = false) => {
    setLoading(true);
    setError('');

    try {
      const query = buildProjectQuery(currentOffset);
      const response = await fetch(
        `${API_BASE_URL}/projects/search?${query}`
      );

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const data = await response.json();
      const rows = Array.isArray(data) ? data : [];

      setProjects((previous) => append ? [...previous, ...rows] : rows);
      setOffset(currentOffset);
      setHasMore(rows.length === PAGE_SIZE);
    } catch (requestError) {
      console.error('Error fetching projects:', requestError);
      setError(requestError.message || 'Unable to load projects.');
      if (!append) setProjects([]);
    } finally {
      setLoading(false);
    }
  }, [buildProjectQuery]);

  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/analytics/dashboard`);

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setAnalytics(await response.json());
    } catch (requestError) {
      console.error('Error fetching dashboard analytics:', requestError);
      setError(requestError.message || 'Unable to load dashboard analytics.');
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  const fetchDailyOpportunities = useCallback(async (dateValue = dailyDate) => {
    if (!dateValue) return;

    setDailyLoading(true);
    setDailyError('');

    try {
      const params = new URLSearchParams({ date: dateValue });
      const response = await fetch(
        `${API_BASE_URL}/analytics/daily-opportunities?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setDailyData(await response.json());
    } catch (requestError) {
      console.error('Error fetching daily opportunities:', requestError);
      setDailyError(
        requestError.message || 'Unable to load daily opportunities.'
      );
      setDailyData(null);
    } finally {
      setDailyLoading(false);
    }
  }, [dailyDate]);

  const refreshDashboard = useCallback(async () => {
    await Promise.allSettled([
      fetchProjects(0, false),
      fetchAllProjects(),
      fetchAnalytics(),
      fetchDailyOpportunities(dailyDate)
    ]);
  }, [
    fetchProjects,
    fetchAllProjects,
    fetchAnalytics,
    fetchDailyOpportunities,
    dailyDate
  ]);

  useEffect(() => {
    if (isLoggedIn) {
      refreshDashboard();
    }
  }, [isLoggedIn, refreshDashboard]);

  // Search and filters are sent to the backend.
  useEffect(() => {
    if (!isLoggedIn) return undefined;

    const timeoutId = window.setTimeout(() => {
      fetchProjects(0, false);
    }, 350);

    return () => window.clearTimeout(timeoutId);
  }, [
    isLoggedIn,
    searchTerm,
    selectedType,
    selectedCategory,
    fetchProjects
  ]);

  const handleLogin = (event) => {
    event.preventDefault();

    if (username.trim()) {
      setIsLoggedIn(true);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setProjects([]);
    setAllProjects([]);
    setAnalytics(null);
    setDailyData(null);
    setError('');
  };

  const handleAddProject = async (event) => {
    event.preventDefault();
    setAddingProject(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          original_url: originalUrl.trim(),
          description: description.trim()
        })
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      setTitle('');
      setOriginalUrl('');
      setDescription('');
      await refreshDashboard();
    } catch (requestError) {
      console.error('Error adding project:', requestError);
      alert(requestError.message || 'Could not add the project.');
    } finally {
      setAddingProject(false);
    }
  };

  const handleDeleteProject = async (id) => {
    if (!window.confirm('Delete this project record?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/projects/${id}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      await refreshDashboard();
    } catch (requestError) {
      console.error('Error deleting project:', requestError);
      alert(requestError.message || 'Could not delete the project.');
    }
  };

  const projectTypes = useMemo(() => (
    [...new Set(
      allProjects
        .map((project) => project.project_type)
        .filter((value) => typeof value === 'string' && value.trim())
    )].sort()
  ), [allProjects]);

  const categories = useMemo(() => (
    [...new Set(
      allProjects
        .map((project) => project.category)
        .filter((value) => typeof value === 'string' && value.trim())
    )].sort()
  ), [allProjects]);

  const duplicateProjects = allProjects.filter(
    (project) => project.is_duplicate === true
  ).length;

  const typeCounts = analytics?.projects_by_type || {};
  const runCounts = analytics?.scraping_runs || {};

  const stats = [
    { label: 'Total Projects', value: analytics?.total_projects ?? '—' },
    { label: 'Projects Today', value: analytics?.projects_today ?? '—' },
    { label: 'Web Projects', value: typeCounts.Web ?? 0 },
    { label: 'App Projects', value: typeCounts.App ?? 0 },
    { label: 'Web & App Projects', value: typeCounts.Both ?? 0 },
    { label: 'Duplicate Projects', value: duplicateProjects }
  ];

  const handleExportCSV = async () => {
    setExporting(true);

    try {
      const params = new URLSearchParams();
      const search = searchTerm.trim();

      if (search) params.set('search', search);
      if (selectedType !== 'All') params.set('project_type', selectedType);
      if (selectedCategory !== 'All') params.set('category', selectedCategory);

      const response = await fetch(
        `${API_BASE_URL}/projects/export?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(await getErrorMessage(response));
      }

      const blob = await response.blob();

      if (blob.size === 0) {
        alert('There are no projects matching the current filters.');
        return;
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `scrapescout-projects-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (requestError) {
      console.error('Error exporting projects:', requestError);
      alert(requestError.message || 'Unable to export projects.');
    } finally {
      setExporting(false);
    }
  };

  const handleDailyDateChange = (event) => {
    const newDate = event.target.value;
    setDailyDate(newDate);
    if (newDate) fetchDailyOpportunities(newDate);
  };

  const loadMoreProjects = () => {
    if (!loading && hasMore) {
      fetchProjects(offset + PAGE_SIZE, true);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h2>ScrapeScout</h2>
          <p>Sign in to manage discovered opportunities</p>

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <input
                type="text"
                placeholder="Enter Username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </div>

            <button type="submit" className="submit-btn">
              Access Workspace
            </button>
          </form>
          <p className="login-note">
            This is the existing frontend-only login screen.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">SS</div>
          <h2>ScrapeScout</h2>
        </div>

        <div className="user-controls">
          <span className="user-badge">
            User: <strong>{username}</strong>
          </span>
          <button className="logout-btn" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button onClick={() => setError('')} aria-label="Dismiss error">
            ×
          </button>
        </div>
      )}

      <section className="stats-grid" aria-label="Dashboard statistics">
        {stats.map((stat) => (
          <div className="stat-card" key={stat.label}>
            <p>{stat.label}</p>
            <h2>{analyticsLoading && stat.value === '—' ? '...' : stat.value}</h2>
          </div>
        ))}
      </section>

      <section className="run-summary">
        <div>
          <span className="run-label">Scraping Runs</span>
          <strong>{runCounts.total ?? '—'}</strong>
        </div>
        <div>
          <span className="run-label">Successful</span>
          <strong className="success-text">{runCounts.successful ?? 0}</strong>
        </div>
        <div>
          <span className="run-label">Failed</span>
          <strong className="failure-text">{runCounts.failed ?? 0}</strong>
        </div>
        <div>
          <span className="run-label">Running</span>
          <strong>{runCounts.running ?? 0}</strong>
        </div>
      </section>

      <section className="source-summary panel">
        <h3 className="panel-title">Projects by Source</h3>
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
            {analyticsLoading ? 'Loading source statistics...' : 'No source statistics available.'}
          </p>
        )}
      </section>

      <section className="daily-panel panel">
        <div className="daily-heading">
          <div>
            <h3 className="panel-title">
              {dailyData?.title || 'Daily Project Opportunities'}
            </h3>
            <p className="muted-text">
              Daily compilation uses the Asia/Kolkata calendar date.
            </p>
          </div>

          <div className="date-control">
            <label htmlFor="dailyDate">Select date</label>
            <input
              id="dailyDate"
              type="date"
              value={dailyDate}
              onChange={handleDailyDateChange}
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
              <span>{dailyData.is_historical ? 'Historical results' : "Today's results"}</span>
              <span>{dailyData.timezone}</span>
            </div>

            {dailyData.projects?.length ? (
              <div className="daily-project-list">
                {dailyData.projects.map((project) => (
                  <article className="daily-project" key={project.id}>
                    <div>
                      <h4>{formatField(project.title)}</h4>
                      <p>{formatField(project.description)}</p>
                      <span className="daily-project-type">
                        {formatField(project.project_type)}
                      </span>
                    </div>
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
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty-state">
                No non-duplicate opportunities were found for this date.
              </p>
            )}
          </>
        ) : (
          <p className="empty-state">Select a date to view its opportunities.</p>
        )}
      </section>

      <div className="content-grid">
        <aside className="panel">
          <h3 className="panel-title">Add Opportunity</h3>

          <form onSubmit={handleAddProject}>
            <div className="form-group">
              <label htmlFor="projectTitle">Project Title</label>
              <input
                id="projectTitle"
                type="text"
                placeholder="Enter project title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="projectUrl">Source URL</label>
              <input
                id="projectUrl"
                type="url"
                placeholder="https://example.com/project"
                value={originalUrl}
                onChange={(event) => setOriginalUrl(event.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="projectDescription">Description</label>
              <textarea
                id="projectDescription"
                placeholder="Brief project description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>

            <button type="submit" className="submit-btn" disabled={addingProject}>
              {addingProject ? 'Adding...' : '+ Add Record'}
            </button>
          </form>
        </aside>

        <main className="panel">
          <div className="panel-title">
            <span>Discovered Projects</span>
            <span className="count-badge">
              {projects.length}{hasMore ? '+' : ''} loaded
            </span>
          </div>

          <div className="form-group">
            <label htmlFor="projectSearch">Search projects</label>
            <input
              id="projectSearch"
              type="text"
              placeholder="Search by title or description..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>

          <div className="filters-grid">
            <div className="form-group">
              <label htmlFor="projectTypeFilter">Project Type</label>
              <select
                id="projectTypeFilter"
                value={selectedType}
                onChange={(event) => setSelectedType(event.target.value)}
              >
                <option value="All">All Project Types</option>
                {projectTypes.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="categoryFilter">Category</label>
              <select
                id="categoryFilter"
                value={selectedCategory}
                onChange={(event) => setSelectedCategory(event.target.value)}
              >
                <option value="All">All Categories</option>
                {categories.map((category) => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="export-row">
            <button
              type="button"
              className="export-btn"
              onClick={handleExportCSV}
              disabled={exporting}
            >
              {exporting ? 'Preparing CSV...' : 'Export CSV'}
            </button>
            <p>Exports all projects matching the current search and filters.</p>
          </div>

          {loading && projects.length === 0 ? (
            <p className="empty-state">Loading projects...</p>
          ) : projects.length === 0 ? (
            <p className="empty-state">No matching projects found.</p>
          ) : (
            <>
              <div className="projects-grid">
                {projects.map((project) => (
                  <article key={project.id} className="project-card">
                    <div>
                      <h4>{formatField(project.title)}</h4>
                      <p>{formatField(project.description)}</p>

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
                      <p><strong>Posted Date:</strong> {formatField(project.posted_date)}</p>
                      <p><strong>Deadline:</strong> {formatField(project.deadline)}</p>
                      <p><strong>Category:</strong> {formatField(project.category)}</p>
                      <p><strong>Confidence Score:</strong> {formatField(project.confidence_score)}</p>
                      <p>
                        <strong>Duplicate:</strong>{' '}
                        {project.is_duplicate == null
                          ? 'Unknown'
                          : project.is_duplicate ? 'Yes' : 'No'}
                      </p>
                      <p><strong>Additional Info:</strong> {formatField(project.content_info)}</p>
                      <p><strong>Created At:</strong> {formatField(project.created_at)}</p>
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

                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteProject(project.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
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
        </main>
      </div>
    </div>
  );
}

export default App;
