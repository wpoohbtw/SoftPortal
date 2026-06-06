/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  DoorOpen,
  LockKeyhole,
  Plus,
  ShieldCheck,
  Trash2,
  UserRound,
  X,
} from 'lucide-react'
import './App.css'

gsap.registerPlugin(useGSAP)

type Route = '/' | '/admin'

type User = {
  id: number
  username: string
  display_name: string
  is_admin: boolean
  is_active: boolean
}

type Project = {
  key: string
  name: string
  path: string
  description: string
  is_active: boolean
}

type SessionPayload = {
  user: User
  projects: Project[]
}

const fallbackProjects: Project[] = [
  {
    key: 'pnl',
    name: 'ProfitsNLosses',
    path: '/pnl/',
    description: 'Future protected route for finance tools',
    is_active: true,
  },
  {
    key: 'vault',
    name: 'Vault Console',
    path: '/vault/',
    description: 'Admin-only workspace placeholder',
    is_active: true,
  },
  {
    key: 'metrics',
    name: 'Metrics Lab',
    path: '/metrics/',
    description: 'Experiments and reports placeholder',
    is_active: true,
  },
]

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let message = 'Request failed'
    try {
      const body = (await response.json()) as { detail?: string }
      message = body.detail ?? message
    } catch {
      message = response.statusText || message
    }
    throw new Error(message)
  }

  const text = await response.text()
  return (text ? JSON.parse(text) : {}) as T
}

function getRoute(): Route {
  return window.location.pathname === '/admin' ? '/admin' : '/'
}

function App() {
  const [route, setRoute] = useState<Route>(getRoute)
  const [session, setSession] = useState<SessionPayload | null>(null)
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const shellRef = useRef<HTMLDivElement | null>(null)

  const navigate = (nextRoute: Route) => {
    window.history.pushState({}, '', nextRoute)
    setRoute(nextRoute)
  }

  useEffect(() => {
    const onPopState = () => setRoute(getRoute())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    let alive = true
    apiRequest<SessionPayload>('/api/auth/session')
      .then((payload) => {
        if (alive) setSession(payload)
      })
      .catch(() => {
        if (alive) setSession(null)
      })
      .finally(() => {
        if (alive) setIsCheckingSession(false)
      })

    return () => {
      alive = false
    }
  }, [])

  useGSAP(
    () => {
      gsap.fromTo(
        '.motion-rise',
        { y: 18, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.55, stagger: 0.04, ease: 'power3.out' },
      )
    },
    { scope: shellRef, dependencies: [route, session?.user.username ?? 'login'] },
  )

  const handleLogin = async (username: string, password: string) => {
    const payload = await apiRequest<SessionPayload>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setSession(payload)
    navigate('/')
  }

  const handleLogout = async () => {
    await apiRequest<{ ok: boolean }>('/api/auth/logout', { method: 'POST' })
    setLogoutOpen(false)
    setSession(null)
    navigate('/')
  }

  let content = <LoadingView />
  if (!isCheckingSession && !session) {
    content = <LoginView onLogin={handleLogin} />
  } else if (!isCheckingSession && session) {
    if (route === '/admin' && session.user.is_admin) {
      content = <AdminView currentUser={session.user} onBack={() => navigate('/')} />
    } else {
      content = (
        <PortalView
          projects={session.projects.length ? session.projects : fallbackProjects}
          user={session.user}
          onAdmin={session.user.is_admin ? () => navigate('/admin') : undefined}
          onLogoutRequest={() => setLogoutOpen(true)}
        />
      )
    }
  }

  return (
    <div className="app-shell" ref={shellRef}>
      <div className="texture-grid" aria-hidden="true" />
      <main className="portal-stage">{content}</main>

      {logoutOpen && (
        <LogoutModal
          username={session?.user.display_name ?? session?.user.username ?? 'User'}
          onCancel={() => setLogoutOpen(false)}
          onConfirm={handleLogout}
        />
      )}
    </div>
  )
}

function LoadingView() {
  return <section className="loading-view motion-rise" aria-live="polite" />
}

function LoginView({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await onLogin(username.trim(), password)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Login failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="login-layout" aria-label="Login">
      <div className="login-art motion-rise" aria-hidden="true">
        <img src="/login-art.jpg" alt="" />
      </div>

      <form className="login-card motion-rise" onSubmit={submit}>
        <label>
          <span>Login</span>
          <div className="input-shell">
            <UserRound size={18} />
            <input
              autoComplete="username"
              autoFocus
              onChange={(event) => setUsername(event.target.value)}
              placeholder="admin"
              type="text"
              value={username}
            />
          </div>
        </label>

        <label>
          <span>Password</span>
          <div className="input-shell">
            <LockKeyhole size={18} />
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              type="password"
              value={password}
            />
          </div>
        </label>

        {error && <p className="form-error">{error}</p>}

        <button className="primary-button" disabled={isSubmitting} type="submit">
          <span>{isSubmitting ? 'Checking' : 'Log in'}</span>
          <ArrowRight size={18} />
        </button>
      </form>
    </section>
  )
}

function PortalView({
  projects,
  user,
  onAdmin,
  onLogoutRequest,
}: {
  projects: Project[]
  user: User
  onAdmin?: () => void
  onLogoutRequest: () => void
}) {
  const openProject = (project: Project) => {
    window.location.href = project.path
  }

  return (
    <section className="portal-layout" aria-label="Projects">
      <div className="top-actions motion-rise">
        <button className="identity" onClick={onLogoutRequest} type="button">
          <span className="identity-name">{user.display_name || user.username}</span>
          <span className="identity-action">Log out</span>
        </button>
        <div className="icon-actions">
          {onAdmin && (
            <button className="icon-button" onClick={onAdmin} title="Admin" type="button">
              <ShieldCheck size={18} />
            </button>
          )}
        </div>
      </div>

      <div className="portal-center">
        <div className="project-grid">
          {projects.slice(0, 3).map((project) => (
            <button className="project-button motion-rise" key={project.key} onClick={() => openProject(project)} type="button">
              <strong>{project.name}</strong>
              <span className="project-arrow">
                <ArrowRight size={18} />
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

function AdminView({ currentUser, onBack }: { currentUser: User; onBack: () => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [createOpen, setCreateOpen] = useState(false)
  const [error, setError] = useState('')
  const [newUser, setNewUser] = useState({ username: '', password: '' })

  const loadUsers = async () => {
    const payload = await apiRequest<User[]>('/api/admin/users')
    setUsers(payload)
  }

  useEffect(() => {
    loadUsers().catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : 'Admin request failed')
    })
  }, [])

  const createUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    try {
      await apiRequest<User>('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify(newUser),
      })
      setNewUser({ username: '', password: '' })
      setCreateOpen(false)
      await loadUsers()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Create user failed')
    }
  }

  const deleteUser = async (userId: number) => {
    setError('')
    try {
      await apiRequest<{ ok: boolean }>(`/api/admin/users/${userId}`, { method: 'DELETE' })
      await loadUsers()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Delete user failed')
    }
  }

  return (
    <section className="admin-layout motion-rise">
      <div className="admin-header">
        <button className="icon-button" onClick={onBack} title="Back" type="button">
          <ArrowLeft size={18} />
        </button>
        <span>{currentUser.display_name}</span>
        <button className="icon-button" onClick={() => setCreateOpen(true)} title="Add user" type="button">
          <Plus size={18} />
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      <div className="admin-panel users-panel">
        <div className="user-list">
          {users.map((user) => (
            <div className="user-row" key={user.id}>
              <span>{user.username}</span>
              <button
                className="icon-button danger-icon"
                disabled={user.id === currentUser.id || user.is_admin}
                onClick={() => deleteUser(user.id)}
                title="Delete"
                type="button"
              >
                <Trash2 size={17} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {createOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="modal-card" aria-modal="true" onSubmit={createUser} role="dialog">
            <label>
              <span>Username</span>
              <div className="input-shell">
                <UserRound size={18} />
                <input
                  autoFocus
                  onChange={(event) => setNewUser({ ...newUser, username: event.target.value })}
                  value={newUser.username}
                />
              </div>
            </label>
            <label>
              <span>Password</span>
              <div className="input-shell">
                <LockKeyhole size={18} />
                <input
                  onChange={(event) => setNewUser({ ...newUser, password: event.target.value })}
                  type="password"
                  value={newUser.password}
                />
              </div>
            </label>
            <div className="modal-actions">
              <button className="ghost-button" onClick={() => setCreateOpen(false)} type="button">
                <X size={17} />
                <span>Cancel</span>
              </button>
              <button className="primary-button" type="submit">
                <Check size={17} />
                <span>Create</span>
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  )
}

function LogoutModal({
  username,
  onCancel,
  onConfirm,
}: {
  username: string
  onCancel: () => void
  onConfirm: () => Promise<void>
}) {
  const [isLeaving, setIsLeaving] = useState(false)

  const confirm = async () => {
    setIsLeaving(true)
    await onConfirm()
    setIsLeaving(false)
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-card" aria-modal="true" role="dialog">
        <div className="modal-icon">
          <DoorOpen size={22} />
        </div>
        <h2>Log out from {username}?</h2>
        <div className="modal-actions">
          <button className="ghost-button" onClick={onCancel} type="button">
            <X size={17} />
            <span>Cancel</span>
          </button>
          <button className="danger-button" disabled={isLeaving} onClick={confirm} type="button">
            <Check size={17} />
            <span>{isLeaving ? 'Leaving' : 'Log out'}</span>
          </button>
        </div>
      </section>
    </div>
  )
}

export default App
