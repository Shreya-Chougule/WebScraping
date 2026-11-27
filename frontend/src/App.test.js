import React from 'react';
import { render, screen, fireEvent, waitFor, act, within } from '@testing-library/react';
import App from './App';

const mockUser = {
  id: 'a0000000-0000-0000-0000-000000000001',
  email: 'admin@scrapescout.com',
  role: 'admin',
  full_name: 'System Administrator',
};

const mockProject = {
  id: 'p0000000-0000-0000-0000-000000000001',
  title: 'Full Stack React Application',
  description: 'Build a dashboard with React and FastAPI',
  project_type: 'Web',
  required_technologies: ['React', 'FastAPI', 'Python'],
  client_name: 'Acme Corp',
  location: 'Remote',
  budget: '1500',
  currency: 'USD',
  posted_date: '2026-11-10T10:00:00Z',
  deadline: '2026-12-01T00:00:00Z',
  original_url: 'https://example.com/project/1',
  category: 'Web Development',
  confidence_score: 0.95,
  is_duplicate: false,
  created_at: '2026-11-10T10:00:00Z',
};

const mockAnalytics = {
  total_projects: 42,
  projects_today: 5,
  projects_by_type: { Web: 30, App: 8, Both: 4 },
  scraping_runs: { total: 10, successful: 9, failed: 1, running: 0 },
  projects_by_source: [{ source_name: 'Truelancer', project_count: 42 }],
};

const mockNotification = {
  id: 'n0000000-0000-0000-0000-000000000001',
  title: 'New High Priority Lead',
  message: 'Discovered high-budget full-stack project.',
  type: 'high_priority',
  is_read: false,
  created_at: new Date().toISOString(),
};

beforeEach(() => {
  localStorage.clear();
  jest.clearAllMocks();
});

afterEach(() => {
  jest.restoreAllMocks();
});

test('renders login screen by default when unauthenticated', () => {
  render(<App />);

  expect(screen.getByRole('heading', { name: /ScrapeScout/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Register/i })).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Email address/i)).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Password/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Access Workspace/i })).toBeInTheDocument();
});

test('allows switching between login and registration mode', () => {
  render(<App />);

  const registerTab = screen.getByRole('button', { name: /Register/i });
  fireEvent.click(registerTab);

  expect(screen.getByPlaceholderText(/Full Name/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();

  const signInTab = screen.getByRole('button', { name: /Sign In/i });
  fireEvent.click(signInTab);

  expect(screen.queryByPlaceholderText(/Full Name/i)).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Access Workspace/i })).toBeInTheDocument();
});

test('displays authentication error on invalid credentials', async () => {
  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    if (String(url).includes('/auth/login')) {
      return Promise.resolve({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid email or password.' }),
      });
    }
    return Promise.reject(new Error('Unknown url'));
  });

  render(<App />);

  fireEvent.change(screen.getByPlaceholderText(/Email address/i), {
    target: { value: 'user@example.com' },
  });
  fireEvent.change(screen.getByPlaceholderText(/Password/i), {
    target: { value: 'wrongpassword' },
  });

  fireEvent.click(screen.getByRole('button', { name: /Access Workspace/i }));

  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/Invalid email or password/i);
  });
});

test('authenticates successfully and renders dashboard with stats and projects', async () => {
  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/login')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          access_token: 'fake-jwt-token-123',
          token_type: 'bearer',
          user: mockUser,
        }),
      });
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAnalytics),
      });
    }
    if (urlStr.includes('/projects/search') || urlStr.endsWith('/projects')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([mockProject]),
      });
    }
    if (urlStr.includes('/sources')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([{ id: 's1', name: 'Truelancer' }]),
      });
    }
    if (urlStr.includes('/analytics/daily-opportunities')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          title: "Today's Project Opportunities",
          total_projects: 1,
          timezone: 'Asia/Kolkata',
          projects: [mockProject],
        }),
      });
    }
    if (urlStr.includes('/notifications')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          notifications: [mockNotification],
          unread_count: 1,
          total: 1,
        }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  fireEvent.change(screen.getByPlaceholderText(/Email address/i), {
    target: { value: 'admin@scrapescout.com' },
  });
  fireEvent.change(screen.getByPlaceholderText(/Password/i), {
    target: { value: 'Admin@123' },
  });

  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /Access Workspace/i }));
  });

  await waitFor(() => {
    expect(screen.getByText(/System Administrator/i)).toBeInTheDocument();
  });

  // Verify role badge
  expect(screen.getAllByText(/admin/i).length).toBeGreaterThanOrEqual(1);

  // Verify dashboard stats
  expect(screen.getByText(/Total Projects/i)).toBeInTheDocument();
  expect(screen.getByText(/Web Projects/i)).toBeInTheDocument();

  // Verify project card
  expect(screen.getAllByText('Full Stack React Application').length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText(/Build a dashboard with React and FastAPI/i).length).toBeGreaterThanOrEqual(1);
});

test('renders advanced search and filter controls and allows resetting', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/projects/search') || urlStr.endsWith('/projects')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([mockProject]) });
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAnalytics) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  await waitFor(() => {
    expect(screen.getAllByRole('button', { name: /Projects/i }).length).toBeGreaterThanOrEqual(1);
  });
  fireEvent.click(screen.getAllByRole('button', { name: /Projects/i })[0]);

  await waitFor(() => {
    expect(screen.getByPlaceholderText(/Search keyword/i)).toBeInTheDocument();
  });

  const searchInput = screen.getByPlaceholderText(/Search keyword/i);
  fireEvent.change(searchInput, { target: { value: 'FastAPI' } });
  expect(searchInput.value).toBe('FastAPI');

  // Verify filter controls exist
  expect(screen.getByLabelText(/Project Type/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Category/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Technology/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Location/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Posted From/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Posted To/i)).toBeInTheDocument();

  // Click clear filters button
  const clearBtn = screen.getByRole('button', { name: /Clear Filters/i });
  fireEvent.click(clearBtn);

  expect(searchInput.value).toBe('');
});

test('renders export controls for CSV and Excel', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/projects/export')) {
      return Promise.resolve({
        ok: true,
        blob: () => Promise.resolve(new Blob(['id,title\n1,Test'], { type: 'text/csv' })),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  // Mock URL object methods for download
  global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
  global.URL.revokeObjectURL = jest.fn();

  render(<App />);

  const exportsNavBtn = await screen.findByRole('button', { name: /Exports/i });
  fireEvent.click(exportsNavBtn);

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /Export CSV/i })).toBeInTheDocument();
  });

  const exportExcelBtn = screen.getByRole('button', { name: /Export Excel/i });
  expect(exportExcelBtn).toBeInTheDocument();

  const exportCsvBtn = screen.getByRole('button', { name: /Export CSV/i });
  fireEvent.click(exportCsvBtn);

  await waitFor(() => {
    expect(global.URL.createObjectURL).toHaveBeenCalled();
  });
});

test('renders notifications panel and marks notification as read', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  jest.spyOn(global, 'fetch').mockImplementation((url, opts) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.endsWith('/notifications')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          notifications: [mockNotification],
          unread_count: 1,
          total: 1,
        }),
      });
    }
    if (urlStr.includes('/notifications/') && urlStr.endsWith('/read')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'success', id: mockNotification.id }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /View notifications/i })).toBeInTheDocument();
  });

  // Bell icon badge shows 1 unread notification
  expect(screen.getByText('1')).toBeInTheDocument();

  // Click bell to toggle panel
  fireEvent.click(screen.getByRole('button', { name: /View notifications/i }));

  expect(screen.getByText('New High Priority Lead')).toBeInTheDocument();
  expect(screen.getByText(/Discovered high-budget full-stack project/i)).toBeInTheDocument();

  // Mark read
  const markReadBtn = screen.getByRole('button', { name: /Mark read/i });
  fireEvent.click(markReadBtn);

  await waitFor(() => {
    expect(screen.queryByRole('button', { name: /Mark read/i })).not.toBeInTheDocument();
  });
});

test('handles sign out and returns to login screen', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/auth/logout')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ message: 'Logged out' }) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /Sign Out/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole('button', { name: /Sign Out/i }));

  await waitFor(() => {
    expect(screen.getByRole('button', { name: /Access Workspace/i })).toBeInTheDocument();
  });

  expect(localStorage.getItem('scrapescout_token')).toBeNull();
});

test('enforces role-based delete action between admin and viewer', async () => {
  const viewerUser = {
    id: 'v0000000-0000-0000-0000-000000000001',
    email: 'viewer@scrapescout.com',
    role: 'viewer',
    full_name: 'Project Viewer',
  };

  localStorage.setItem('scrapescout_token', 'mock-viewer-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(viewerUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(viewerUser) });
    }
    if (urlStr.includes('/projects/search') || urlStr.endsWith('/projects')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([mockProject]) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  await waitFor(() => {
    expect(screen.getByText('Project Viewer')).toBeInTheDocument();
  });

  // Viewer role must not have project delete button
  await waitFor(() => {
    expect(screen.getByText(/Viewer Access/i)).toBeInTheDocument();
  });
  expect(screen.queryByRole('button', { name: /Delete/i })).not.toBeInTheDocument();
});

test('navigates across all sidebar sections and shows planned sources', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/sources')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 's1', name: 'Truelancer', base_url: 'https://www.truelancer.com', is_active: true },
        ]),
      });
    }
    if (urlStr.includes('/scraping-runs')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          {
            id: 'r1',
            source_id: 's1',
            status: 'SUCCESS',
            records_found: 4,
            started_at: '2026-11-26T10:00:00Z',
            completed_at: '2026-11-26T10:01:00Z',
            error_log: null,
          },
        ]),
      });
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAnalytics) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  // Sources page
  await waitFor(() => {
    expect(screen.getAllByRole('button', { name: /Sources/i }).length).toBeGreaterThanOrEqual(1);
  });
  fireEvent.click(screen.getAllByRole('button', { name: /Sources/i })[0]);
  expect(await screen.findByText(/Connected & Active Sources/i)).toBeInTheDocument();
  expect(screen.getByText(/Planned Freelance Sources/i)).toBeInTheDocument();
  expect(screen.getByText('PeoplePerHour')).toBeInTheDocument();
  expect(screen.getAllByText(/Planned · Not Connected/i).length).toBe(4);

  // Scraping Activity page
  fireEvent.click(screen.getByRole('button', { name: /Scraping Activity/i }));
  expect(await screen.findByText(/Scraping Run History/i)).toBeInTheDocument();
  expect(await screen.findByText('SUCCESS')).toBeInTheDocument();

  // Settings page
  fireEvent.click(screen.getByRole('button', { name: /Settings/i }));
  expect(await screen.findByText(/Appearance & Theme/i)).toBeInTheDocument();
  expect(screen.getAllByText(/System Administrator/i).length).toBeGreaterThanOrEqual(2);
});

test('toggles light and dark theme and persists preference in localStorage', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));
  localStorage.setItem('scrapescout_theme', 'light');

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  const { container } = render(<App />);

  await waitFor(() => {
    expect(container.querySelector('[data-theme="light"]')).toBeInTheDocument();
  });

  const themeToggle = screen.getByRole('button', { name: /Toggle color theme/i });
  fireEvent.click(themeToggle);

  await waitFor(() => {
    expect(container.querySelector('[data-theme="dark"]')).toBeInTheDocument();
  });
  expect(localStorage.getItem('scrapescout_theme')).toBe('dark');
});

test('triggers manual Truelancer fetch and displays loading and result summary', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  let resolveManualFetch;
  const manualFetchPromise = new Promise((resolve) => {
    resolveManualFetch = resolve;
  });

  jest.spyOn(global, 'fetch').mockImplementation((url, opts) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/scrape/truelancer/manual') && opts?.method === 'POST') {
      return manualFetchPromise;
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAnalytics) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  const fetchBtn = await screen.findByRole('button', { name: /Fetch from Truelancer/i });
  fireEvent.click(fetchBtn);

  expect(screen.getByRole('button', { name: /Fetching from Truelancer/i })).toBeDisabled();

  await act(async () => {
    resolveManualFetch({
      ok: true,
      json: () => Promise.resolve({
        run_id: 'run-123',
        source_id: 's1',
        source_name: 'Truelancer',
        provider: 'scraperapi',
        start_url: 'https://www.truelancer.com/freelance-jobs',
        status: 'SUCCESS',
        records_found: 8,
        inserted: 5,
        duplicate_skipped: 2,
        irrelevant_skipped: 1,
        missing_url_skipped: 0,
        invalid_skipped: 0,
        failed: 0,
        submission: {},
      }),
    });
  });

  await waitFor(() => {
    expect(screen.getByLabelText(/Manual fetch summary/i)).toBeInTheDocument();
  });

  expect(screen.getByText(/Truelancer fetch finished \(SUCCESS\): 8 found, 5 inserted/i)).toBeInTheDocument();
  expect(screen.getByText('Records Found')).toBeInTheDocument();
  expect(screen.getByText('Projects Inserted')).toBeInTheDocument();
  expect(
  within(screen.getByLabelText(/Manual fetch summary/i))
    .getByText('Duplicates Skipped')
).toBeInTheDocument();
});

test('allows authenticated non-admin viewer to trigger manual Truelancer fetch', async () => {
  const viewerUser = {
    id: 'v0000000-0000-0000-0000-000000000001',
    email: 'viewer@scrapescout.com',
    role: 'viewer',
    full_name: 'Project Viewer',
  };
  localStorage.setItem('scrapescout_token', 'mock-viewer-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(viewerUser));

  jest.spyOn(global, 'fetch').mockImplementation((url) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(viewerUser) });
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAnalytics) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  const fetchBtn = await screen.findByRole('button', { name: /Fetch from Truelancer/i });
  expect(fetchBtn).toBeEnabled();
});

test('renders Scheduler page, creates a schedule, and displays upcoming executions on Dashboard', async () => {
  localStorage.setItem('scrapescout_token', 'mock-token');
  localStorage.setItem('scrapescout_user', JSON.stringify(mockUser));

  const savedSchedule = {
    id: 'sched-1',
    source_id: 's1',
    name: 'Daily Morning Sync',
    frequency: 'daily',
    time_of_day: '09:00',
    timezone: 'Asia/Kolkata',
    max_pages: 3,
    min_request_interval: 1.0,
    is_enabled: true,
    next_run_at: '2026-11-27T03:30:00Z',
    last_run_at: null,
    last_run_status: null,
  };

  jest.spyOn(global, 'fetch').mockImplementation((url, opts) => {
    const urlStr = String(url);
    if (urlStr.includes('/auth/me')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockUser) });
    }
    if (urlStr.includes('/sources')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          { id: 's1', name: 'Truelancer', base_url: 'https://www.truelancer.com', is_active: true },
        ]),
      });
    }
    if (urlStr.includes('/schedules/status')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ scheduler_enabled: false, running: false, default_timezone: 'Asia/Kolkata' }),
      });
    }
    if (urlStr.endsWith('/schedules') && opts?.method === 'POST') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(savedSchedule) });
    }
    if (urlStr.endsWith('/schedules')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([savedSchedule]) });
    }
    if (urlStr.includes('/analytics/dashboard')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          ...mockAnalytics,
          inserted_today: 4,
          duplicates_skipped: 1,
          active_sources_count: 1,
          scheduler_enabled: false,
          upcoming_schedules: [savedSchedule],
        }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
  });

  render(<App />);

  // Dashboard shows upcoming scheduled execution
  expect(await screen.findByText(/Upcoming Scheduled Executions/i)).toBeInTheDocument();
  expect(await screen.findByText('Daily Morning Sync')).toBeInTheDocument();

  // Navigate to Scheduler page
  fireEvent.click(screen.getByRole('button', { name: /Scheduler/i }));
  expect(await screen.findByText(/Background Scheduler Status/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Frequency \*/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Save Schedule/i })).toBeInTheDocument();
});
