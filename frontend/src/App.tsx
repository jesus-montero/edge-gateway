import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { DashboardPage } from './pages/DashboardPage';
import { DevicesPage } from './pages/DevicesPage';
import { EventsPage } from './pages/EventsPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { RulesPage } from './pages/RulesPage';
import auth from './services/auth';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUser } from '@fortawesome/free-solid-svg-icons';
import { useEffect, useState, useRef } from 'react';

const navigationItems = [
  { label: 'Panel', to: '/' },
  { label: 'Integraciones', to: '/integrations' },
  { label: 'Dispositivos', to: '/devices' },
  { label: 'Reglas', to: '/rules' },
];

/**
 * Componente de ruta protegida que redirige a inicio si el usuario no está autenticado.
 */
function ProtectedRoute({ children, isAuthenticated }: { children: React.ReactNode; isAuthenticated: boolean }) {
  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function LayoutShell() {
  const navigate = useNavigate();
  const [authDrawerOpen, setAuthDrawerOpen] = useState(false);
  const [authDrawerMode, setAuthDrawerMode] = useState<'login' | 'credentials'>('login');
  const [sessionUsername, setSessionUsername] = useState(auth.getSessionUsername());
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSaving, setAuthSaving] = useState(false);

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setSessionUsername(auth.getSessionUsername());
  }, []);

  function openAuthDrawer(mode: 'login' | 'credentials') {
    setAuthDrawerMode(mode);
    setAuthDrawerOpen(true);
  }

  function closeAuthDrawer() {
    setAuthDrawerOpen(false);
  }

  // Estado local de los formularios dentro del panel lateral.
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const loginUsernameRef = useRef<HTMLInputElement | null>(null);
  const [newUsername, setNewUsername] = useState(auth.getSessionUsername() ?? '');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saveNote, setSaveNote] = useState('');

  async function handleLoginSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!loginUsername.trim() || !loginPassword) return;

    setAuthSaving(true);
    setAuthError(null);
    try {
      const session = await auth.login(loginUsername.trim(), loginPassword);
      setSessionUsername(session.username);
      setNewUsername(session.username);
      setLoginUsername('');
      setLoginPassword('');
      setSaveNote('Autenticado');
      window.setTimeout(() => setSaveNote(''), 1400);
      closeAuthDrawer();
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'No se pudo autenticar');
    } finally {
      setAuthSaving(false);
    }
  }

  useEffect(() => {
    if (authDrawerOpen && authDrawerMode === 'login') {
      // Pequeño retraso para esperar a la transición del panel.
      window.setTimeout(() => loginUsernameRef.current?.focus(), 60);
    }
  }, [authDrawerOpen, authDrawerMode]);

  async function handleCredSave() {
    if (!sessionUsername) {
      setAuthError('Primero debes autenticarte');
      return;
    }

    if (!newUsername.trim() || !newPassword) {
      setAuthError('Completa todos los campos');
      return;
    }

    if (newPassword !== confirmPassword) {
      setAuthError('Las contraseñas nuevas no coinciden');
      return;
    }

    setAuthSaving(true);
    setAuthError(null);
    try {
      const session = await auth.updateCredentials(newUsername.trim(), newPassword);
      setSessionUsername(session.username);
      setNewUsername(session.username);
      setNewPassword('');
      setConfirmPassword('');
      setSaveNote('Guardado');
      window.setTimeout(() => {
        setSaveNote('');
        closeAuthDrawer();
      }, 2000);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : 'No se pudo guardar');
    } finally {
      setAuthSaving(false);
    }
  }

  function handleLogout() {
    auth.logout();
    setSessionUsername(null);
    setLoginUsername('');
    setLoginPassword('');
    setNewUsername('');
    setNewPassword('');
    setConfirmPassword('');
    setAuthError(null);
    closeAuthDrawer();
    setUserMenuOpen(false);
  }

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const el = userMenuRef.current;
      if (!el) return;
      if (e.target instanceof Node && !el.contains(e.target)) {
        setUserMenuOpen(false);
      }
    }

    document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand">Edge Gateway</div>
        </div>
        {sessionUsername && (
          <nav className="nav">
            {navigationItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                end={item.to === '/'}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </aside>

      <div className="content-area">
        <header className="topbar">
          <div>
            <h1>Panel</h1>
          </div>
          <div>
            {sessionUsername ? (
              <div style={{ position: 'relative' }} ref={userMenuRef}>
                <button
                  type="button"
                  className="nav-link"
                  onClick={() => setUserMenuOpen((s) => !s)}
                  title={sessionUsername}
                >
                  <FontAwesomeIcon icon={faUser} />
                  <span style={{ marginLeft: 8 }}>{sessionUsername}</span>
                </button>

                {userMenuOpen ? (
                  <div className="user-menu">
                    <button type="button" className="nav-link" onClick={() => { handleLogout(); }}>
                      Cerrar sesión
                    </button>
                    <button
                      type="button"
                      className="nav-link"
                      onClick={() => {
                        setUserMenuOpen(false);
                        openAuthDrawer('credentials');
                      }}
                    >
                      Modificar credenciales
                    </button>
                  </div>
                ) : null}
              </div>
            ) : (
              <button type="button" className="nav-link" onClick={() => openAuthDrawer('login')}>
                <FontAwesomeIcon icon={faUser} />
                <span style={{ marginLeft: 8 }}>Autenticarse</span>
              </button>
            )}
          </div>
        </header>

        <main className="page-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/devices" element={<ProtectedRoute isAuthenticated={!!sessionUsername}><DevicesPage /></ProtectedRoute>} />
            <Route path="/rules" element={<ProtectedRoute isAuthenticated={!!sessionUsername}><RulesPage /></ProtectedRoute>} />
            <Route path="/integrations" element={<ProtectedRoute isAuthenticated={!!sessionUsername}><IntegrationsPage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

          <aside className={`device-drawer${authDrawerOpen ? ' open' : ''}`} role="dialog" aria-modal="true" aria-hidden={!authDrawerOpen}>
            <div className="device-drawer-header">
              <div>
                <p className="device-drawer-eyebrow">{authDrawerMode === 'login' ? 'Autenticación' : 'Credenciales'}</p>
                <h3>{authDrawerMode === 'login' ? 'Iniciar sesión' : 'Gestión de credenciales'}</h3>
              </div>
              <button type="button" className="btn btn-secondary" onClick={closeAuthDrawer}>
                Cerrar
              </button>
            </div>

            <div className="device-drawer-body">
              {authError ? <div className="alert error">{authError}</div> : null}
              {authDrawerMode === 'login' ? (
                <form onSubmit={handleLoginSubmit} style={{ display: 'grid', gap: 12 }}>
                  <label className="device-field">
                    <span>Usuario</span>
                    <input ref={loginUsernameRef} value={loginUsername} onChange={(e) => setLoginUsername(e.target.value)} type="text" />
                  </label>

                  <label className="device-field">
                    <span>Contraseña</span>
                    <input value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} type="password" />
                  </label>

                  <div className="device-drawer-actions">
                    <button type="button" className="btn btn-secondary" onClick={closeAuthDrawer}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn btn-primary" disabled={authSaving}>
                      {authSaving ? 'Comprobando...' : 'Entrar'}
                    </button>
                  </div>
                </form>
              ) : (
                <div style={{ display: 'grid', gap: 12 }}>
                  <div className="device-id-readonly">
                    <span>Usuario actual</span>
                    <strong>{sessionUsername ?? 'Sin sesión'}</strong>
                  </div>

                  <label className="device-field">
                    <span>Nuevo usuario</span>
                    <input value={newUsername} onChange={(e) => setNewUsername(e.target.value)} type="text" />
                  </label>

                  <label className="device-field">
                    <span>Nueva contraseña</span>
                    <input value={newPassword} onChange={(e) => setNewPassword(e.target.value)} type="password" />
                  </label>

                  <label className="device-field">
                    <span>Confirmar nueva contraseña</span>
                    <input value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} type="password" />
                  </label>

                  <div className="device-drawer-actions">
                    <button type="button" className="btn btn-secondary" onClick={closeAuthDrawer}>
                      Cancelar
                    </button>
                    <button type="button" className="btn btn-primary" onClick={handleCredSave} disabled={authSaving}>
                      {authSaving ? 'Guardando...' : 'Guardar'}
                    </button>
                  </div>
                  {saveNote ? <div className="topbar-chip">{saveNote}</div> : null}
                </div>
              )}
            </div>
          </aside>

          <div className={`device-drawer-overlay${authDrawerOpen ? ' open' : ''}`} onClick={closeAuthDrawer} />
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return <LayoutShell />;
}