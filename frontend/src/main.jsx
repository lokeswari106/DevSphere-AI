import React, {
  useState,
  useEffect,
  useCallback,
  useRef,
  createContext,
  useContext,
  lazy,
  Suspense,
} from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  NavLink,
  Link,
  useNavigate,
  useParams,
  Navigate,
} from "react-router-dom";
import {
  Box,
  Plus,
  LayoutDashboard,
  Folder,
  ScanLine,
  Settings,
  ArrowRight,
  LogOut,
  ChevronRight,
  Menu,
  Moon,
  Sun,
  Check,
  RefreshCw,
  Download,
  FileCode2,
  Activity,
  Search,
  ArrowUpRight,
} from "lucide-react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./styles.css";
import { api, setCsrf, errorText, label, download } from "./api";
import { Artifact, Status, Empty, Markdown } from "./components/Artifacts";
import ReviewInput from "./components/ReviewInput";
import ReviewFinding from "./components/ReviewFinding";
const CodeEditor = lazy(() => import("./components/CodeEditor"));
const Session = createContext();
const examples = [
  {
    title: "E-commerce application",
    text: "Create an e-commerce platform with authentication, product management, cart, orders and a clearly labelled test-mode payment integration. Build a small runnable demonstration with secure password handling and ownership checks.",
  },
  {
    title: "URL shortener",
    text: "Build a URL shortening API with URL validation, unique short codes, redirect lookup, click counting and tests. Use a simple modular design with persistent storage.",
  },
  {
    title: "Review existing code",
    text: "Analyze my uploaded Node.js application and identify bugs, performance issues and security risks. Include file references, fixes and honest verification limits.",
  },
];
function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [theme, setTheme] = useState(
      localStorage.getItem("devsphere-theme") || "light",
    );
  useEffect(() => {
    api
      .get("/auth/me")
      .then(({ data }) => {
        setUser(data.user);
        setCsrf(data.csrf_token);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("devsphere-theme", theme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#191b1f" : "#faf9f6");
  }, [theme]);
  if (loading) return <div className="boot">Opening your workspace…</div>;
  return (
    <Session.Provider value={{ user, setUser, theme, setTheme }}>
      <BrowserRouter>{!user ? <Auth /> : <Shell />}</BrowserRouter>
    </Session.Provider>
  );
}
function Auth() {
  const { setUser } = useContext(Session);
  const [register, setRegister] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const d = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const { data } = await api.post(
        "/auth/" + (register ? "register" : "login"),
        d,
      );
      setCsrf(data.csrf_token);
      setUser(data.user);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-screen">
      <div className="auth-story">
        <Link to="/" className="brand">
          <span className="brand-mark">
            <Box size={23} />
          </span>
          DevSphere <b>AI</b>
        </Link>
        <div>
          <span className="eyebrow">YOUR ENGINEERING WORKSPACE</span>
          <h1>
            From an idea
            <br />
            to something
            <br />
            <em>you can build.</em>
          </h1>
          <p>
            Plan, design, write and review software with a team of specialized
            AI agents. You stay in control at every step.
          </p>
        </div>
        <div className="auth-foot">
          <span>8 specialized agents</span>
          <span>One shared project</span>
          <span>Your approval</span>
        </div>
      </div>
      <div className="auth-main">
        <form className="auth-form" onSubmit={submit}>
          <span className="small-mark">
            <Box />
          </span>
          <h2>{register ? "Create your workspace" : "Welcome back"}</h2>
          <p className="muted">
            {register
              ? "Start building with DevSphere AI. No invitation needed."
              : "Sign in to continue your engineering projects."}
          </p>
          {register && (
            <label>
              Your name
              <input name="name" autoComplete="name" required minLength={2} />
            </label>
          )}
          <label>
            Email address
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              minLength={register ? 12 : 1}
              required
            />
          </label>
          {register && <small>Use at least 12 characters.</small>}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary wide" disabled={busy}>
            {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
            <ArrowRight size={17} />
          </button>
          <p className="auth-switch">
            {register ? "Already have an account?" : "New here?"}{" "}
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setRegister(!register);
                setError("");
              }}
            >
              {register ? "Sign in" : "Create an account"}
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}
function Shell() {
  const { user, setUser, theme, setTheme } = useContext(Session);
  const [open, setOpen] = useState(false);
  async function logout() {
    await api.post("/auth/logout");
    setCsrf("");
    setUser(null);
  }
  return (
    <div className="app-shell">
      <button
        aria-label="Toggle navigation"
        aria-expanded={open}
        aria-controls="workspace-navigation"
        className="mobile-menu"
        onClick={() => setOpen(!open)}
      >
        <Menu />
      </button>
      {open && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setOpen(false)} />}
      <aside id="workspace-navigation" className={open ? "sidebar open" : "sidebar"}>
        <Link className="brand" to="/" onClick={() => setOpen(false)}>
          <span className="brand-mark">
            <Box size={21} />
          </span>
          DevSphere <b>AI</b>
        </Link>
        <Link to="/new" className="new-project" onClick={() => setOpen(false)}>
          <Plus size={18} />
          New project
        </Link>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Main navigation" onClick={() => setOpen(false)}>
          <NavLink to="/" end>
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>
          <NavLink to="/projects">
            <Folder size={18} />
            My projects
          </NavLink>
          <NavLink to="/review">
            <ScanLine size={18} />
            Code review
          </NavLink>
          <NavLink to="/settings">
            <Settings size={18} />
            Settings
          </NavLink>
        </nav>
        <div className="sidebar-note">
          <span className="sidebar-note-label">A little structure.<br />More room to build.</span>
          <p>
            Eight agents share the work.<br />You decide what moves forward.
          </p>
        </div>
        <div className="sidebar-bottom">
          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}{" "}
            {theme === "light" ? "Dark" : "Light"} mode
          </button>
          <div className="profile">
            <span className="avatar">{user.name[0].toUpperCase()}</span>
            <div>
              <strong>{user.name}</strong>
              <small>Personal workspace</small>
            </div>
            <button aria-label="Sign out" onClick={logout}>
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Dashboard all />} />
          <Route path="/new" element={<NewProject />} />
          <Route path="/review" element={<ReviewInput />} />
          <Route path="/projects/:id" element={<Workspace />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}
function Dashboard({ all = false }) {
  const { user } = useContext(Session);
  const [items, setItems] = useState([]),
    [error, setError] = useState(""),
    [search, setSearch] = useState("");
  useEffect(() => {
    api
      .get("/projects")
      .then((r) => setItems(r.data))
      .catch((e) => setError(errorText(e)));
  }, []);
  const filtered = items.filter((x) =>
    x.project_name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="page dashboard">
      <div className="page-top">
        <span className="breadcrumb">
          Workspace / {all ? "My projects" : "Overview"}
        </span>
        <span className="quiet-pill">Personal workspace</span>
      </div>
      <header className="hero">
        <div className="hero-intro">
          <span className="eyebrow">YOUR ENGINEERING WORKSPACE</span>
          <h1>{all ? "Your projects" : `Hello, ${user.name.split(" ")[0]}.`}</h1>
          <p>{all ? "Your work, from the first requirement to the final review." : "A clear space to plan, build and review your next project."}</p>
        </div>
        <Link to="/new" className="primary">
          Create a project
          <ArrowRight size={18} />
        </Link>
      </header>
      {!all && (
        <section className="starter-section">
          <h2>
            Start with an example <span>A starting point for your next build</span>
          </h2>
          <div className="starter-grid">
            {examples.map((x, i) => (
              <Link
                to={i === 2 ? "/review" : "/new"}
                state={{ requirement: x.text, name: x.title }}
                className="starter"
                key={x.title}
              >
                <div className="starter-meta"><span>{["APPLICATION", "API & DATA", "CODE QUALITY"][i]}</span><span className="starter-number">0{i + 1}</span></div>
                <h3>
                  {x.title}
                  <ArrowUpRight size={17} />
                </h3>
                <p>
                  {i === 0
                    ? "Design a complete shopping experience."
                    : i === 1
                      ? "Explore a small, focused API project."
                      : "Find issues in code you already have."}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}
      <section className="projects-section">
        <div className="section-line">
          <h2>
            {all ? "All projects" : "Recent projects"}{" "}
            <span className="count">{items.length}</span>
          </h2>
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Search projects"
              placeholder="Find a project"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        {!filtered.length ? (
          <Empty title="Your next idea starts here">
            Create a project or import code to start your first engineering
            workflow.
          </Empty>
        ) : (
          <div className="project-list">
            {filtered.map((p) => (
              <Link key={p.id} className="project-row" to={"/projects/" + p.id}>
                <span className="project-icon">
                  <Folder size={21} />
                </span>
                <div className="project-main">
                  <h3>{p.project_name}</h3>
                  <span>
                    {p.framework} · Version {p.revision}
                  </span>
                </div>
                <Status value={p.project_status} />
                <time>
                  {new Date(p.updated_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </time>
                <ChevronRight size={18} />
              </Link>
            ))}
          </div>
        )}
      </section>
      <footer className="page-footer">
        <span>DevSphere AI / Engineering workspace</span>
        <span>Plan · Design · Build · Review · Deliver</span>
      </footer>
    </div>
  );
}
import { useLocation } from "react-router-dom";
function NewProject({ review = false }) {
  const navigate = useNavigate(),
    location = useLocation();
  const [language, setLanguage] = useState(review ? "JavaScript" : "Python"),
    [framework, setFramework] = useState(review ? "Node.js" : "FastAPI"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const frameworks = {
    Python: ["FastAPI", "React + FastAPI"],
    JavaScript: ["Node.js", "React + Node.js"],
    Java: ["Java standard library"],
  };
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    const d = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const { data } = await api.post("/projects", d);
      navigate("/projects/" + data.id, { state: { import: review } });
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  }
  return (
    <div className="page narrow">
      <span className="breadcrumb">
        Workspace / {review ? "Code review" : "New project"}
      </span>
      <header className="page-heading">
        <span className="eyebrow">
          {review ? "UNDERSTAND YOUR CODE" : "START WITH YOUR IDEA"}
        </span>
        <h1>
          {review
            ? "A fresh perspective on your code."
            : "What would you like to build?"}
        </h1>
        <p>
          {review
            ? "Create a review workspace, then import your source files."
            : "Describe the outcome. Your AI team will help work out the details."}
        </p>
      </header>
      <form className="project-form" onSubmit={submit}>
        <label>
          Project name
          <input
            name="project_name"
            placeholder="e.g. Linkly URL shortener"
            defaultValue={location.state?.name || ""}
            minLength={3}
            maxLength={120}
            required
          />
        </label>
        <label>
          {review ? "Review goals" : "What should the application do?"}
          <textarea
            name="description"
            rows={7}
            minLength={20}
            maxLength={12000}
            placeholder="Describe the users, main features and any constraints…"
            defaultValue={
              location.state?.requirement || (review ? examples[2].text : "")
            }
            required
          />
        </label>
        <small>
          Include the important details. You can refine the plan before any code
          is generated.
        </small>
        <div className="form-row">
          <label>
            Language
            <select
              name="programming_language"
              value={language}
              onChange={(e) => {
                setLanguage(e.target.value);
                setFramework(frameworks[e.target.value][0]);
              }}
            >
              {Object.keys(frameworks).map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            Framework
            <select
              name="framework"
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
            >
              {frameworks[language].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Application type
          <select name="application_type">
            <option value="web_application">Web application</option>
            <option value="api">Backend API</option>
            <option value="library">Library or utility</option>
          </select>
        </label>
        <p className="form-note">
          <Check size={17} />
          Nothing is overwritten. You approve designs and file changes.
        </p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <div className="form-actions">
          <Link to="/" className="secondary">
            Cancel
          </Link>
          <button className="primary" disabled={busy}>
            {busy ? "Creating…" : "Create workspace"}
            <ArrowRight size={17} />
          </button>
        </div>
      </form>
    </div>
  );
}
const tabs = [
  "Overview",
  "Requirements",
  "Architecture",
  "Database and APIs",
  "Code",
  "Code Review",
  "Testing",
  "Documentation",
];
function Workspace() {
  const { id } = useParams(),
    navigate = useNavigate(),
    location = useLocation();
  const [p, setP] = useState(null),
    [tab, setTab] = useState(location.state?.tab || (location.state?.import ? "Code" : "Overview")),
    [wf, setWf] = useState({ tasks: [] }),
    [docs, setDocs] = useState([]),
    [files, setFiles] = useState([]),
    [reviews, setReviews] = useState([]),
    [tests, setTests] = useState([]),
    [approvals, setApprovals] = useState([]),
    [versions, setVersions] = useState([]),
    [events, setEvents] = useState([]),
    [caps, setCaps] = useState({}),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [workflow, setWorkflow] = useState("full"),
    [instructions, setInstructions] = useState(""),
    [comment, setComment] = useState(""),
    [selected, setSelected] = useState(""),
    [editor, setEditor] = useState(""),
    [showDiff, setShowDiff] = useState(false),
    [diffBefore, setDiffBefore] = useState(undefined),
    [severity, setSeverity] = useState("all");
  const requestVersion = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++requestVersion.current;
    try {
      const r = await Promise.all([
        api.get("/projects/" + id),
        api.get(`/projects/${id}/workflow`),
        api.get(`/projects/${id}/documents`),
        api.get(`/projects/${id}/files`),
        api.get(`/projects/${id}/reviews`),
        api.get(`/projects/${id}/tests`),
        api.get(`/projects/${id}/approvals`),
        api.get(`/projects/${id}/versions`),
        api.get(`/projects/${id}/events`),
        api.get("/settings"),
      ]);
      if (version !== requestVersion.current) return;
      setP(r[0].data);
      setWf(r[1].data);
      setDocs(r[2].data);
      setFiles(r[3].data);
      setReviews(r[4].data);
      setTests(r[5].data);
      setApprovals(r[6].data);
      setVersions(r[7].data);
      setEvents(r[8].data);
      setCaps(r[9].data);
    } catch (e) {
      if (version === requestVersion.current) setError(errorText(e));
    }
  }, [id]);
  useEffect(() => {
    setP(null);
    setError("");
    setWf({ tasks: [] });
    setTests([]);
    setSelected("");
    refresh();
    const onFocus = () => refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      ++requestVersion.current;
      window.removeEventListener("focus", onFocus);
    };
  }, [refresh]);
  const backgroundWork = ["queued", "running", "testing"].includes(wf.run?.status)
    || tests.some((test) => ["queued", "running"].includes(test.test_status));
  const waitingForReview = wf.run?.status === "awaiting_approval";
  useEffect(() => {
    if (!backgroundWork && !waitingForReview) return;
    const timer = setInterval(refresh, backgroundWork ? 3000 : 10000);
    return () => clearInterval(timer);
  }, [refresh, backgroundWork, waitingForReview]);
  const file = files.find((f) => f.id === selected);
  useEffect(() => {
    if (!selected && files.length) setSelected(files[0].id);
  }, [files]);
  useEffect(() => {
    if (file) {
      setEditor(file.file_content);
      setDiffBefore(undefined);
    }
  }, [selected, file?.version]);
  async function act(fn) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function execute(type = workflow) {
    await act(() =>
      api.post(`/projects/${id}/execute`, {
        workflow_type: type,
        instructions,
      }),
    );
  }
  async function decision(a, d) {
    await act(() =>
      api.post(`/projects/${id}/approvals/${a.id}/decision`, {
        decision: d,
        artifact_hash: a.artifact_hash,
        expected_revision: p.revision,
        comment,
      }),
    );
    setComment("");
  }
  async function upload(e) {
    const uploaded = [...e.target.files];
    if (uploaded.length > 60) {
      setError("Select at most 60 source files.");
      return;
    }
    await act(async () => {
      const contents = await Promise.all(
        uploaded.map(async (f) => ({
          path: f.webkitRelativePath || f.name,
          content: await f.text(),
        })),
      );
      await api.post(`/projects/${id}/files/import`, {
        files: contents,
        expected_revision: p.revision,
      });
    });
    e.target.value = "";
  }
  const pending = approvals.filter((a) => a.status === "pending");
  const active = ["queued", "running", "awaiting_approval", "testing"].includes(
    wf.run?.status,
  );
  const reviewing = active && (wf.run?.workflow_type === "quick_review" || wf.tasks.some(t => ["review", "security"].includes(t.task_name) && ["queued", "running"].includes(t.task_status)));
  const doc = (kind) => docs.find((x) => x.document_type === kind);
  const currentApproval = pending[0];
  if (!p)
    return (
      <div className="page">
        {error ? <p className="error">{error}</p> : <p>Opening project…</p>}
      </div>
    );
  return (
    <div className="workspace">
      <div className="workspace-heading">
        <Link to="/projects" className="breadcrumb">
          My projects <ChevronRight size={13} /> {p.project_name}
        </Link>
        <div className="section-line">
          <div>
            <h1>{p.project_name}</h1>
            <p>
              {p.framework} <span>·</span> Revision {p.revision} <span>·</span>{" "}
              <Status value={p.project_status} />
            </p>
          </div>
          <div className="button-row"><button className="secondary" onClick={refresh} title="Refresh project status">
            <RefreshCw size={15} /> Refresh
          </button><button
            className="secondary"
            onClick={() =>
              act(() =>
                download(`/projects/${id}/export`, "devsphere-project.zip"),
              )
            }
          >
            <Download size={16} />
            Export project
          </button></div>
        </div>
      </div>
      <div className="workspace-tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t}
            role="tab"
            aria-label={t}
            aria-selected={tab === t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t}
            {t === "Code" && files.length > 0 && <span>{files.length}</span>}
          </button>
        ))}
      </div>
      <div className="workspace-content">
        {error && (
          <div className="error" role="alert">
            {error}
            <button className="text-button" onClick={() => setError("")}>
              Dismiss
            </button>
          </div>
        )}
        {currentApproval && (
          <section className="approval">
            <div className="section-line">
              <div>
                <span className="eyebrow">YOUR REVIEW IS NEEDED</span>
                <h2>
                  {label(currentApproval.checkpoint)}{" "}
                  {currentApproval.checkpoint === "test_failure"
                    ? "needs attention"
                    : "is ready to review"}
                </h2>
              </div>
              <Status value="awaiting_approval" />
            </div>
            <p>
              {currentApproval.payload.summary ||
                "Review this exact proposal before continuing. Existing versions are preserved."}
            </p>
            {currentApproval.checkpoint === "test_execution" && (
              <p>
                The separate runner will execute the current source and tests
                with network access disabled, a 512 MB memory limit and a time
                limit. Model and database secrets are excluded.
              </p>
            )}
            <details>
              <summary>
                Inspect proposal{" "}
                {currentApproval.payload.files &&
                  `(${currentApproval.payload.files.length} files)`}
              </summary>
              {currentApproval.payload.files ? (
                currentApproval.payload.files.map((f) => (
                  <details className="proposal-file" key={f.path}>
                    <summary>{f.path}</summary>
                    <Suspense fallback={<p>Loading comparison…</p>}>
                      <CodeEditor
                        path={f.path}
                        before={
                          files.find((x) => x.file_path === f.path)
                            ?.file_content || ""
                        }
                        value={f.content}
                      />
                    </Suspense>
                  </details>
                ))
              ) : (
                <Artifact value={currentApproval.payload} />
              )}
            </details>
            {["plan", "requirements", "architecture", "database"].includes(
              currentApproval.checkpoint,
            ) && (
              <ProposalEditor
                key={currentApproval.artifact_hash}
                proposal={currentApproval}
                revision={p.revision}
                projectId={id}
                act={act}
              />
            )}
            <label className="approval-comment">
              Feedback or requested changes
              <textarea
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Describe any changes you would like…"
              />
            </label>
            <div className="approval-actions">
              <button
                className="primary"
                disabled={busy}
                onClick={() => decision(currentApproval, "approve")}
              >
                <Check size={17} />
                {currentApproval.checkpoint === "test_execution"
                  ? "Approve test execution"
                  : currentApproval.checkpoint === "test_failure"
                    ? "Continue with disclosed failures"
                    : "Approve and continue"}
              </button>
              {currentApproval.run_id && (
                <button
                  className="secondary"
                  disabled={busy || !comment.trim()}
                  onClick={() => decision(currentApproval, "regenerate")}
                >
                  <RefreshCw size={16} />
                  {currentApproval.checkpoint === "test_failure"
                    ? "Request repair"
                    : "Request changes"}
                </button>
              )}
              <button
                className="text-button danger"
                disabled={busy}
                onClick={() => decision(currentApproval, "reject")}
              >
                Reject
              </button>
            </div>
            <small>
              Approval applies only to this proposal and revision{" "}
              {currentApproval.base_revision}.
            </small>
          </section>
        )}
        {tab === "Overview" && (
          <>
            <div className="overview-grid">
              <section>
                <span className="eyebrow">PROJECT BRIEF</span>
                <h2>A shared direction for your AI team</h2>
                <p className="brief">{p.description}</p>
                <details>
                  <summary>Edit project brief</summary>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const d = Object.fromEntries(
                        new FormData(e.currentTarget),
                      );
                      act(() =>
                        api.put("/projects/" + id, {
                          ...d,
                          expected_revision: p.revision,
                        }),
                      );
                    }}
                  >
                    <label>
                      Name
                      <input
                        name="project_name"
                        defaultValue={p.project_name}
                        required
                      />
                    </label>
                    <label>
                      Requirement
                      <textarea
                        name="description"
                        rows={5}
                        defaultValue={p.description}
                        required
                      />
                    </label>
                    <button className="secondary" disabled={active || busy}>
                      Save brief
                    </button>
                  </form>
                </details>
                <div className="workflow-controls">
                  <label>
                    Engineering workflow
                    <select
                      value={workflow}
                      onChange={(e) => setWorkflow(e.target.value)}
                    >
                      <option value="full">Full project generation</option>
                      <option value="review">Review existing code</option>
                      <option value="requirements">Refine requirements</option>
                      <option value="architecture">
                        Regenerate architecture
                      </option>
                      <option value="database">
                        Regenerate database and APIs
                      </option>
                      <option value="code">Generate or modify code</option>
                      <option value="repair">
                        Repair after tests or review
                      </option>
                      <option value="documentation">Documentation only</option>
                    </select>
                  </label>
                  <label>
                    Additional instructions
                    <textarea
                      rows={3}
                      value={instructions}
                      onChange={(e) => setInstructions(e.target.value)}
                      placeholder="Optional: describe changes, constraints or priorities"
                    />
                  </label>
                  <div className="button-row">
                    <button
                      className="primary"
                      disabled={active || pending.length > 0 || busy}
                      onClick={() => execute()}
                    >
                      Start workflow
                      <ArrowRight size={17} />
                    </button>
                    {wf.run?.status === "failed" && (
                      <button
                        className="secondary"
                        onClick={() =>
                          act(() => api.post(`/projects/${id}/retry`))
                        }
                      >
                        Retry failed step
                      </button>
                    )}
                    {active && (
                      <button
                        className="secondary"
                        onClick={() => {
                          if (
                            confirm(
                              "Cancel this workflow? Approved files will be preserved.",
                            )
                          )
                            act(() => api.post(`/projects/${id}/cancel`));
                        }}
                      >
                        Cancel workflow
                      </button>
                    )}
                  </div>
                  <small>
                    {label(caps.provider)} · {caps.model} · Human approval at
                    checkpoints
                  </small>
                </div>
              </section>
              <section className="timeline-panel">
                <div className="section-line">
                  <h2>
                    <Activity size={18} />
                    Agent activity
                  </h2>
                  <span className={`live-indicator ${backgroundWork ? "is-live" : ""}`}>
                    {backgroundWork ? "Live updates" : waitingForReview ? "Review needed" : wf.run?.status === "completed" ? "Completed" : "Idle"}
                  </span>
                </div>
                {wf.run?.error && <p className="error">{wf.run.error}</p>}
                {!wf.tasks.length ? (
                  <Empty title="Your team is ready">
                    Start a workflow to see each agent's work here.
                  </Empty>
                ) : (
                  <div className="timeline">
                    {wf.tasks.map((t) => (
                      <details
                        key={t.id}
                        className={"timeline-item " + t.task_status}
                      >
                        <summary>
                          <span className="timeline-dot" />
                          <div>
                            <strong>{label(t.agent_name)}</strong>
                            <small>
                              {label(t.task_name)} ·{" "}
                              {t.completed_at
                                ? `${((new Date(t.completed_at) - new Date(t.started_at)) / 1000).toFixed(1)} s`
                                : label(t.task_status)}
                            </small>
                          </div>
                          <Status value={t.task_status} />
                        </summary>
                        {t.error_message && (
                          <p className="error">{t.error_message}</p>
                        )}
                        <Artifact
                          value={
                            t.output_data?.artifact || {
                              summary: ["running", "queued"].includes(t.task_status)
                                ? "Agent is working with the shared project context."
                                : `This task is ${label(t.task_status).toLowerCase()}. No completed output was saved.`,
                            }
                          }
                        />
                      </details>
                    ))}
                  </div>
                )}
              </section>
            </div>
            {doc("plan") && (
              <details className="history">
                <summary>Engineering plan and task dependencies</summary>
                <Artifact value={doc("plan").document_content} />
              </details>
            )}
            <details className="history">
              <summary>Version history ({versions.length})</summary>
              {versions.map((v) => (
                <div className="history-row" key={v.id}>
                  <strong>v{v.version_number}</strong>
                  <span>{v.change_summary}</span>
                  <small>{new Date(v.created_at).toLocaleString()}</small>
                </div>
              ))}
            </details>
            <details className="history">
              <summary>Activity log</summary>
              {events.map((e) => (
                <div className="history-row" key={e.id}>
                  <small>{new Date(e.created_at).toLocaleTimeString()}</small>
                  <span>{label(e.event_type)}</span>
                </div>
              ))}
            </details>
            <button
              className="text-button danger"
              onClick={() => {
                const name = prompt(
                  "To delete this project, type its exact name: " +
                    p.project_name,
                );
                if (name === p.project_name)
                  act(async () => {
                    await api.delete("/projects/" + id, {
                      params: { confirm_name: name },
                    });
                    navigate("/projects");
                  });
              }}
            >
              Delete project
            </button>
          </>
        )}
        {["Requirements", "Architecture", "Database and APIs"].includes(
          tab,
        ) && (
          <>
            <div className="section-line">
              <h2>{tab}</h2>
              <span className="muted">Approved artifacts</span>
            </div>
            {doc(
              {
                Requirements: "requirements",
                Architecture: "architecture",
                "Database and APIs": "database",
              }[tab],
            ) ? (
              <Artifact
                value={
                  doc(
                    {
                      Requirements: "requirements",
                      Architecture: "architecture",
                      "Database and APIs": "database",
                    }[tab],
                  ).document_content
                }
              />
            ) : (
              <Empty title="This part is still ahead">
                Start a workflow and approve the preceding step. Its output will
                appear here.
              </Empty>
            )}
            {tab === "Requirements" && !active && (
              <details>
                <summary>Write your own requirement specification</summary>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const content = new FormData(e.currentTarget).get(
                      "content",
                    );
                    act(() =>
                      api.post(`/projects/${id}/requirements`, {
                        content,
                        expected_revision: p.revision,
                      }),
                    );
                  }}
                >
                  <label>
                    Specification
                    <textarea name="content" minLength={20} rows={6} required />
                  </label>
                  <button className="secondary">Propose specification</button>
                </form>
              </details>
            )}
          </>
        )}
        {tab === "Code" && (
          <>
            <div className="section-line">
              <div>
                <h2>Project files</h2>
                <p className="muted">
                  Browse approved source. Edits become proposals before they are
                  saved.
                </p>
              </div>
              <label className="secondary upload">
                <Plus size={16} />
                Import source
                <input
                  type="file"
                  multiple
                  onChange={upload}
                  disabled={active || busy || pending.length > 0}
                  accept=".py,.js,.jsx,.mjs,.cjs,.json,.md,.sql,.java,.css,.html,.txt,.toml,.yaml,.yml,.xml"
                />
              </label>
            </div>
            {!files.length ? (
              <Empty title="A clean slate">
                Generate code or import source files to review. Files stay in
                this project; originals are unchanged.
              </Empty>
            ) : (
              <div className="code-workspace">
                <div className="file-tree">
                  {files.map((f) => (
                    <button
                      className={selected === f.id ? "selected" : ""}
                      key={f.id}
                      onClick={() => setSelected(f.id)}
                    >
                      <FileCode2 size={15} />
                      <span>{f.file_path}</span>
                      <small>v{f.version}</small>
                    </button>
                  ))}
                </div>
                <div className="editor-panel">
                  <div className="editor-header">
                    <span>{file?.file_path}</span>
                    <div>
                      {file?.version > 1 && (
                        <button
                          className="text-button"
                          onClick={() =>
                            act(async () => {
                              const { data } = await api.get(
                                `/projects/${id}/files/${file.id}/diff?against=${file.version - 1}`,
                              );
                              setDiffBefore(data.before);
                              setShowDiff(true);
                            })
                          }
                        >
                          Previous version
                        </button>
                      )}
                      <button
                        className="text-button"
                        onClick={() => {
                          setDiffBefore(file?.file_content);
                          setShowDiff(!showDiff);
                        }}
                      >
                        {showDiff ? "Editor" : "Compare"}
                      </button>
                    </div>
                  </div>
                  <Suspense fallback={<p>Loading editor…</p>}>
                    <CodeEditor
                      path={file?.file_path}
                      value={editor}
                      onChange={setEditor}
                      before={showDiff ? diffBefore : undefined}
                    />
                  </Suspense>
                  <div className="editor-footer">
                    <small>
                      {editor !== file?.file_content
                        ? "Unsaved changes · approval required"
                        : "All changes saved"}{" "}
                    </small>
                    <button
                      className="primary"
                      disabled={
                        active ||
                        pending.length > 0 ||
                        busy ||
                        editor === file?.file_content
                      }
                      onClick={() =>
                        act(() =>
                          api.put(`/projects/${id}/files/${file.id}`, {
                            content: editor,
                            expected_revision: p.revision,
                          }),
                        )
                      }
                    >
                      Propose changes
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        {tab === "Code Review" && (
          <>
            <div className="section-line">
              <div>
                <h2>Quality and security</h2>
                <p className="muted">
                  AI findings are hypotheses. Static observations are labelled
                  separately.
                </p>
              </div>
              <div className="button-row"><Link className="secondary" to="/review">Paste or upload code</Link><button
                className="secondary"
                disabled={active || !files.length || busy || pending.length > 0}
                onClick={() => execute("quick_review")}
              >
                Review current code
              </button></div>
            </div>
            {reviewing && <p className="notice" role="status">Review in progress. Quality and security agents are inspecting the source; findings will appear here when both finish.</p>}
            {wf.run?.workflow_type === "quick_review" && wf.run?.status === "failed" && <p className="error" role="alert">The review did not finish: {wf.run.error || "Check agent activity in Overview."} <button className="text-button" onClick={()=>act(()=>api.post(`/projects/${id}/retry`))}>Retry review</button></p>}
            <div className="filter-bar">
              {["all", "critical", "high", "medium", "low", "info"].map((s) => (
                <button
                  className={severity === s ? "selected" : ""}
                  onClick={() => setSeverity(s)}
                  key={s}
                >
                  {label(s)}
                </button>
              ))}
            </div>
            {reviews
              .filter((r) => severity === "all" || r.severity === severity)
              .map((r) => (
                <ReviewFinding key={r.id} finding={r} source={files.find(f=>f.id===r.file_id)} />
              ))}
            {!reviews.length && (
              <Empty title={reviewing ? "Your review is running" : wf.run?.workflow_type==='quick_review' && wf.run?.status==='completed' ? "Review complete: no findings returned" : "No findings recorded yet"}>
                {reviewing ? "You can leave this page and return later. Progress is saved in your project." : "Paste code, upload files or review the current project files. An empty review is not a security guarantee."}
              </Empty>
            )}
          </>
        )}
        {tab === "Testing" && (
          <>
            <div className="section-line">
              <div>
                <h2>Tests with real results</h2>
                <p className="muted">
                  {caps.runner_online && caps.runner_capabilities?.image_ready
                    ? "Isolated runner is ready."
                    : "Runner is offline or the sandbox image is not ready."}
                </p>
              </div>
              <div className="button-row">
                <button
                  className="secondary"
                  disabled={
                    active || !files.length || busy || pending.length > 0
                  }
                  onClick={() => execute("tests")}
                >
                  Generate tests
                </button>
                <button
                  className="primary"
                  disabled={
                    active ||
                    !files.length ||
                    busy ||
                    pending.length > 0 ||
                    !caps.runner_online
                  }
                  onClick={() =>
                    act(() =>
                      api.post(`/projects/${id}/run-tests`, {
                        recipe: {
                          Python: "python",
                          JavaScript: "node",
                          Java: "java",
                        }[p.programming_language],
                      }),
                    )
                  }
                >
                  Request test execution
                </button>
              </div>
            </div>
            {!tests.length ? (
              <Empty title="No tests have run">
                Generate test cases, review the proposed files and approve
                sandbox execution.
              </Empty>
            ) : (
              tests.map((t) => (
                <article className="test-result" key={t.id}>
                  <div className="section-line">
                    <h3>{label(t.recipe)} test execution</h3>
                    <Status value={t.test_status} />
                    {t.source_current === false && (
                      <small>Earlier source version</small>
                    )}
                  </div>
                  <div className="test-counts">
                    <span>
                      <strong>{t.total_tests ?? "—"}</strong>Total
                    </span>
                    <span>
                      <strong>{t.passed_tests ?? "—"}</strong>Passed
                    </span>
                    <span>
                      <strong>{t.failed_tests ?? "—"}</strong>Failed
                    </span>
                    <span>
                      <strong>
                        {t.details?.execution?.duration?.toFixed(1) ?? "—"}
                      </strong>
                      Seconds
                    </span>
                  </div>
                  <small>
                    Snapshot {t.source_hash.slice(0, 12)} ·{" "}
                    {new Date(t.created_at).toLocaleString()}
                  </small>
                  {t.test_status === "failed" && /ERROR collecting|error during collection/i.test(t.execution_output || "") && <p className="notice">Test collection failed before individual tests could run. Check the syntax or missing dependency in the execution log.</p>}
                  <details
                    open={["failed", "timed_out", "runner_error"].includes(
                      t.test_status,
                    )}
                  >
                    <summary>Execution log</summary>
                    <pre>
                      {t.execution_output ||
                        "Waiting for the runner. No results yet."}
                    </pre>
                  </details>
                </article>
              ))
            )}
          </>
        )}
        {tab === "Documentation" && (
          <>
            <div className="section-line">
              <div>
                <h2>Project documentation</h2>
                <p className="muted">
                  Versioned reports built from this project's actual artifacts.
                </p>
              </div>
              <button
                className="secondary"
                disabled={active || busy || pending.length > 0}
                onClick={() => execute("documentation")}
              >
                Generate documentation
              </button>
            </div>
            {!docs.length ? (
              <Empty title="The story of your project">
                Approved designs and final documentation will appear here.
              </Empty>
            ) : (
              docs.flatMap(d => d.document_type === 'documentation' ? ['final_report','readme','architecture','testing','deployment'].map(section=>({...d,section,document_content:d.document_content[section+'_markdown']})) : [d]).map((d) => (
                <details className="document-row" key={d.id+(d.section||'')}>
                  <summary>
                    <span>{label(d.section || d.document_type)}</span>
                    <small>v{d.version}</small>
                  </summary>
                  <div className="button-row">
                    <button
                      className="secondary"
                      onClick={() =>
                        act(() =>
                          download(
                            `/projects/${id}/documents/${d.id}/download?format=md&section=${d.section || 'final_report'}`,
                            (d.section || d.document_type) + ".md",
                          ),
                        )
                      }
                    >
                      Markdown
                      <Download size={15} />
                    </button>
                    <button
                      className="secondary"
                      onClick={() =>
                        act(() =>
                          download(
                            `/projects/${id}/documents/${d.id}/download?format=pdf&section=${d.section || 'final_report'}`,
                            (d.section || d.document_type) + ".pdf",
                          ),
                        )
                      }
                    >
                      PDF
                      <Download size={15} />
                    </button>
                  </div>
                  <Artifact value={d.document_content} />
                </details>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
function SettingsPage() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get("/settings").then((r) => setData(r.data));
  }, []);
  return (
    <div className="page narrow">
      <span className="breadcrumb">Workspace / Settings</span>
      <header className="page-heading">
        <h1>Your workspace settings</h1>
        <p>
          Model and runner connections are managed on the application server.
        </p>
      </header>
      {data && (
        <dl className="settings-list">
          <dt>AI provider</dt>
          <dd>{label(data.provider)}</dd>
          <dt>Current model</dt>
          <dd>{data.model}</dd>
          <dt>Test runner</dt>
          <dd>{data.runner_online ? "Online" : "Offline"}</dd>
          <dt>Sandbox image</dt>
          <dd>
            {data.runner_capabilities?.image_ready ? "Ready" : "Not available"}
          </dd>
          <dt>File limit</dt>
          <dd>{data.max_files} files per project</dd>
          <dt>Application version</dt>
          <dd>{data.version}</dd>
        </dl>
      )}
      <p className="notice">
        To switch models, update the server's environment configuration and
        restart it. API keys are never stored in this browser.
      </p>
      <p className="muted">
        Generated code needs human review. Test results appear only after an
        approved execution. This workspace preserves previous file and document
        versions.
      </p>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);

function ProposalEditor({ proposal, revision, projectId, act }) {
  const [value, setValue] = useState(JSON.stringify(proposal.payload, null, 2));
  return (
    <details>
      <summary>Edit this proposal</summary>
      <p>
        Correct the structured artifact before approval. The original agent
        output remains in the history.
      </p>
      <textarea
        aria-label="Proposal JSON"
        rows={14}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        style={{ fontFamily: "monospace" }}
      />
      <button
        className="secondary"
        onClick={() =>
          act(() =>
            api.put(`/projects/${projectId}/approvals/${proposal.id}`, {
              expected_revision: revision,
              artifact_hash: proposal.artifact_hash,
              payload: JSON.parse(value),
            }),
          )
        }
      >
        Save proposal edits
      </button>
    </details>
  );
}
