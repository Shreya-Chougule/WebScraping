
import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [projects, setProjects] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  const [title, setTitle] = useState('');
  const [originalUrl, setOriginalUrl] = useState('');
  const [description, setDescription] = useState('');

  const [selectedType, setSelectedType] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Format values for display
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

  // Fetch projects from FastAPI
  const fetchProjects = async () => {
    setLoading(true);

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/projects'
      );

      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const data = await response.json();
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchProjects();
    }
  }, [isLoggedIn]);

  // Login
  const handleLogin = (e) => {
    e.preventDefault();

    if (username.trim()) {
      setIsLoggedIn(true);
    }
  };

  // Add project
  const handleAddProject = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/projects',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            title,
            original_url: originalUrl,
            description
          })
        }
      );

      if (response.ok) {
        setTitle('');
        setOriginalUrl('');
        setDescription('');
        await fetchProjects();
      } else {
        const errorData = await response.json().catch(() => ({}));
        alert(errorData.detail || 'Failed to add project');
      }
    } catch (error) {
      console.error('Error adding project:', error);
      alert('Could not connect to the backend.');
    }
  };

  // Delete project
  const handleDeleteProject = async (id) => {
    if (!window.confirm('Delete this project record?')) {
      return;
    }

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/projects/${id}`,
        { method: 'DELETE' }
      );

      if (response.ok) {
        await fetchProjects();
      } else {
        alert('Failed to delete project');
      }
    } catch (error) {
      console.error('Error deleting project:', error);
      alert('Could not connect to the backend.');
    }
  };

  // Get unique project types
  const projectTypes = [
    ...new Set(
      projects
        .map((project) => project.project_type)
        .filter(
          (value) =>
            typeof value === 'string' && value.trim() !== ''
        )
    )
  ].sort();

  // Get unique categories
  const categories = [
    ...new Set(
      projects
        .map((project) => project.category)
        .filter(
          (value) =>
            typeof value === 'string' && value.trim() !== ''
        )
    )
  ].sort();

  // Search and filter projects
  const filteredProjects = projects.filter((project) => {
    const search = searchTerm.trim().toLowerCase();

    const projectTitle = String(
      project.title || ''
    ).toLowerCase();

    const projectDescription = String(
      project.description || ''
    ).toLowerCase();

    const matchesSearch =
      projectTitle.includes(search) ||
      projectDescription.includes(search);

    const matchesType =
      selectedType === 'All' ||
      String(project.project_type || '').toLowerCase() ===
        selectedType.toLowerCase();

    const matchesCategory =
      selectedCategory === 'All' ||
      String(project.category || '').toLowerCase() ===
        selectedCategory.toLowerCase();

    return matchesSearch && matchesType && matchesCategory;
  });

  // Classify project types for statistics
  const getTypeFlags = (project) => {
    const type = String(
      project.project_type || ''
    ).toLowerCase();

    const isBoth =
      type.includes('both') ||
      (
        type.includes('web') &&
        (type.includes('app') || type.includes('mobile'))
      );

    return {
      isBoth,
      isWeb: type.includes('web') && !isBoth,
      isApp:
        (type.includes('app') || type.includes('mobile')) &&
        !isBoth
    };
  };

  // Dashboard statistics
  const totalProjects = projects.length;

  const webProjects = projects.filter(
    (project) => getTypeFlags(project).isWeb
  ).length;

  const appProjects = projects.filter(
    (project) => getTypeFlags(project).isApp
  ).length;

  const bothProjects = projects.filter(
    (project) => getTypeFlags(project).isBoth
  ).length;

  const duplicateProjects = projects.filter(
    (project) => project.is_duplicate === true
  ).length;

  // Export the current search/filter results as CSV
  const handleExportCSV = () => {
    if (filteredProjects.length === 0) {
      alert('There are no projects to export.');
      return;
    }

    const columns = [
      { key: 'id', label: 'Project ID' },
      { key: 'source_id', label: 'Source ID' },
      { key: 'title', label: 'Title' },
      { key: 'description', label: 'Description' },
      { key: 'project_type', label: 'Project Type' },
      { key: 'required_technology', label: 'Required Technologies' },
      { key: 'client_name', label: 'Client Name' },
      { key: 'location', label: 'Location' },
      { key: 'budget', label: 'Budget' },
      { key: 'currency', label: 'Currency' },
      { key: 'posted_date', label: 'Posted Date' },
      { key: 'deadline', label: 'Deadline' },
      { key: 'original_url', label: 'Original URL' },
      { key: 'content_info', label: 'Content Info' },
      { key: 'category', label: 'Category' },
      { key: 'confidence_score', label: 'Confidence Score' },
      { key: 'is_duplicate', label: 'Is Duplicate' },
      { key: 'created_at', label: 'Created At' }
    ];

    // Escape commas, quotes and newlines correctly for CSV
    const csvValue = (value) => {
      let text = '';

      if (value !== null && value !== undefined) {
        text =
          typeof value === 'object'
            ? JSON.stringify(value)
            : String(value);
      }

      return `"${text.replace(/"/g, '""')}"`;
    };

    const headerRow = columns
      .map((column) => csvValue(column.label))
      .join(',');

    const dataRows = filteredProjects.map((project) =>
      columns
        .map((column) => csvValue(project[column.key]))
        .join(',')
    );

    // BOM helps Excel display UTF-8 text correctly
    const csvContent =
      '\uFEFF' + [headerRow, ...dataRows].join('\r\n');

    const blob = new Blob([csvContent], {
      type: 'text/csv;charset=utf-8;'
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = url;
    link.download =
      `project-discovery-${new Date().toISOString().slice(0, 10)}.csv`;

    document.body.appendChild(link);
    link.click();
    link.remove();

    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  // Login screen
  if (!isLoggedIn) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h2>Project Discovery</h2>
          <p>Sign in to manage scraped opportunities</p>

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <input
                type="text"
                placeholder="Enter Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="submit-btn">
              Access Workspace
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Dashboard
  return (
    <div className="dashboard-container">
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">PD</div>
          <h2>Project Discovery Engine</h2>
        </div>

        <div className="user-controls">
          <span className="user-badge">
            User: <strong>{username}</strong>
          </span>

          <button
            className="logout-btn"
            onClick={() => setIsLoggedIn(false)}
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Statistics Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '16px',
          margin: '20px 0'
        }}
      >
        {[
          { label: 'Total Projects', value: totalProjects },
          { label: 'Web Projects', value: webProjects },
          { label: 'App Projects', value: appProjects },
          { label: 'Web & App Projects', value: bothProjects },
          { label: 'Duplicate Projects', value: duplicateProjects }
        ].map((stat) => (
          <div
            key={stat.label}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '18px',
              background: 'white'
            }}
          >
            <p style={{ margin: '0 0 10px', color: '#6b7280' }}>
              {stat.label}
            </p>
            <h2 style={{ margin: 0, color: '#111827' }}>
              {stat.value}
            </h2>
          </div>
        ))}
      </div>

      <div className="content-grid">
        {/* Add Project Form */}
        <aside className="panel">
          <h3 className="panel-title">Add Opportunity</h3>

          <form onSubmit={handleAddProject}>
            <div className="form-group">
              <label>Project Title</label>
              <input
                type="text"
                placeholder="Enter project title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Source URL</label>
              <input
                type="url"
                placeholder="https://example.com/project"
                value={originalUrl}
                onChange={(e) => setOriginalUrl(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                placeholder="Brief project description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <button type="submit" className="submit-btn">
              + Add Record
            </button>
          </form>
        </aside>

        {/* Project Dashboard */}
        <main className="panel">
          <div className="panel-title">
            <span>Discovered Projects</span>
            <span className="count-badge">
              {filteredProjects.length} Projects
            </span>
          </div>

          {/* Search */}
          <div
            className="form-group"
            style={{ marginBottom: '16px' }}
          >
            <input
              type="text"
              placeholder="Search by title or description..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Filters */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              marginBottom: '16px'
            }}
          >
            <div className="form-group">
              <label htmlFor="projectTypeFilter">Project Type</label>
              <select
                id="projectTypeFilter"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
                  borderRadius: '8px'
                }}
              >
                <option value="All">All Project Types</option>
                {projectTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="categoryFilter">Category</label>
              <select
                id="categoryFilter"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                style={{
                  width: '100%',
                  padding: '10px',
                  marginTop: '6px',
                  borderRadius: '8px'
                }}
              >
                <option value="All">All Categories</option>
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* CSV Export */}
          <div style={{ marginBottom: '20px' }}>
            <button
              type="button"
              onClick={handleExportCSV}
              disabled={filteredProjects.length === 0}
              style={{
                padding: '10px 16px',
                border: 'none',
                borderRadius: '8px',
                background:
                  filteredProjects.length === 0 ? '#9ca3af' : '#2563eb',
                color: 'white',
                cursor:
                  filteredProjects.length === 0 ? 'not-allowed' : 'pointer',
                fontWeight: '600'
              }}
            >
              Export CSV ({filteredProjects.length})
            </button>
            <p style={{ fontSize: '0.85rem', color: '#6b7280' }}>
              Exports projects matching your current search and filters.
            </p>
          </div>

          {/* Project Cards */}
          {loading ? (
            <p className="empty-state">Loading projects...</p>
          ) : filteredProjects.length === 0 ? (
            <p className="empty-state">No matching projects found.</p>
          ) : (
            <div className="projects-grid">
              {filteredProjects.map((proj) => (
                <div key={proj.id} className="project-card">
                  <div>
                    <h4>{formatField(proj.title)}</h4>
                    <p>{formatField(proj.description)}</p>

                    <p>
                      <strong>Project Type:</strong>{' '}
                      {formatField(proj.project_type)}
                    </p>

                    <p>
                      <strong>Required Technologies:</strong>{' '}
                      {formatField(proj.required_technology)}
                    </p>

                    <p>
                      <strong>Client:</strong>{' '}
                      {formatField(proj.client_name)}
                    </p>

                    <p>
                      <strong>Location:</strong>{' '}
                      {formatField(proj.location)}
                    </p>

                    <p>
                      <strong>Budget:</strong>{' '}
                      {proj.budget == null || proj.budget === ''
                        ? 'Not specified'
                        : `${formatField(proj.budget)} ${
                            proj.currency || ''
                          }`.trim()}
                    </p>

                    <p>
                      <strong>Posted Date:</strong>{' '}
                      {formatField(proj.posted_date)}
                    </p>

                    <p>
                      <strong>Deadline:</strong>{' '}
                      {formatField(proj.deadline)}
                    </p>

                    <p>
                      <strong>Category:</strong>{' '}
                      {formatField(proj.category)}
                    </p>

                    <p>
                      <strong>Confidence Score:</strong>{' '}
                      {formatField(proj.confidence_score)}
                    </p>

                    <p>
                      <strong>Duplicate:</strong>{' '}
                      {proj.is_duplicate == null
                        ? 'Unknown'
                        : proj.is_duplicate
                          ? 'Yes'
                          : 'No'}
                    </p>

                    <p>
                      <strong>Additional Info:</strong>{' '}
                      {formatField(proj.content_info)}
                    </p>

                    <p>
                      <strong>Created At:</strong>{' '}
                      {formatField(proj.created_at)}
                    </p>
                  </div>

                  <div className="card-footer">
                    {proj.original_url && (
                      <a
                        href={proj.original_url}
                        target="_blank"
                        rel="noreferrer"
                        className="link-btn"
                      >
                        Source Link ↗
                      </a>
                    )}

                    <button
                      onClick={() => handleDeleteProject(proj.id)}
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#ef4444',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        fontWeight: '600'
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
