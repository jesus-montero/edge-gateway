import { useCallback, useEffect, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus, faTrashCan, faPen } from '@fortawesome/free-solid-svg-icons';
import { PageCard } from '../components/PageCard';
import {
  getSaasProviders,
  getSaasProvider,
  createSaasProvider,
  updateSaasProvider,
  deleteSaasProvider,
} from '../services/api';

type EditorMode = 'create' | 'edit';

export function IntegrationsPage() {
  const [providers, setProviders] = useState<Record<string, Record<string, unknown>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>('edit');
  const [providerName, setProviderName] = useState('');
  const [editorJson, setEditorJson] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadProviders = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getSaasProviders();
      // res.providers is a mapping providerName -> config
      setProviders(res.providers ?? {});
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar las integraciones');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProviders();
  }, [loadProviders]);

  function openCreate() {
    setEditorMode('create');
    setProviderName('');
    setEditorJson('{}');
    setSaveError(null);
    setSaveMessage(null);
    setEditorOpen(true);
  }

  async function openEdit(name: string) {
    try {
      setSaveError(null);
      setEditorMode('edit');
      setProviderName(name);
      // try to fetch the latest config from backend
      const res = await getSaasProvider(name);
      setEditorJson(JSON.stringify(res.provider ?? {}, null, 2));
      setEditorOpen(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo cargar la integración');
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveMessage(null);

    let parsed: Record<string, unknown> = {};
    try {
      parsed = editorJson.trim() === '' ? {} : JSON.parse(editorJson);
    } catch (err) {
      setSaveError('JSON inválido: ' + (err instanceof Error ? err.message : String(err)));
      setSaving(false);
      return;
    }

    try {
      if (editorMode === 'create') {
        if (!providerName || providerName.trim() === '') {
          throw new Error('El nombre del proveedor es obligatorio');
        }
        await createSaasProvider(providerName.trim(), parsed);
        setSaveMessage('Proveedor creado');
      } else {
        await updateSaasProvider(providerName, parsed);
        setSaveMessage('Proveedor actualizado');
      }

      await loadProviders();

      // keep save message visible for 2 seconds then close
      setTimeout(() => {
        setEditorOpen(false);
        setSaveMessage(null);
      }, 2000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(name: string) {
    const confirmed = window.confirm(`¿Eliminar la integración "${name}"? Esta acción no se puede deshacer.`);
    if (!confirmed) return;

    try {
      await deleteSaasProvider(name);
      await loadProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar');
    }
  }

  return (
    <PageCard
      title="Integraciones"
      description=""
      headerActions={
        <button type="button" className="device-add-button" aria-label="Añadir integración" title="Añadir integración" onClick={openCreate}>
          <FontAwesomeIcon icon={faPlus} />
        </button>
      }
    >
      {loading ? (
        <div className="muted-block">Cargando integraciones...</div>
      ) : error ? (
        <div className="alert error">{error}</div>
      ) : Object.keys(providers).length === 0 ? (
        <div className="empty-state">
          <strong>No hay integraciones configuradas.</strong>
          <p>Puedes crear nuevas integraciones pulsando el botón +.</p>
        </div>
      ) : (
        <div className="metrics-grid devices-grid">
          {Object.keys(providers).map((name) => (
            <div key={name} className="metric device-card">
              <strong>{String((providers[name] as { provider_name?: unknown })?.provider_name ?? name)}</strong>
              <div className="device-details">
                <small></small>
              </div>
              <div className="device-card-actions">
                <button type="button" className="btn btn-ghost" onClick={() => void openEdit(name)} title="Editar">
                  <FontAwesomeIcon icon={faPen} />
                </button>
                <button type="button" className="device-delete-button" onClick={() => void handleDelete(name)} title="Eliminar">
                  <FontAwesomeIcon icon={faTrashCan} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <aside className={`device-drawer${editorOpen ? ' open' : ''}`} role="dialog" aria-modal="true" aria-hidden={!editorOpen}>
        <div className="device-drawer-header">
          <div>
            <p className="device-drawer-eyebrow">{editorMode === 'create' ? 'Crear integración' : 'Editar integración'}</p>
            <h3>{editorMode === 'create' ? 'Nueva integración' : providerName}</h3>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => setEditorOpen(false)}>
            Cerrar
          </button>
        </div>

        <div className="device-drawer-body">
          <label className="device-field">
            <span>Nombre del proveedor</span>
            <input type="text" value={providerName} onChange={(e) => setProviderName(e.target.value)} disabled={editorMode === 'edit'} />
          </label>

          <label className="device-field" style={{ gridColumn: '1 / -1' }}>
            <span>Configuración (JSON)</span>
            <textarea rows={12} value={editorJson} onChange={(e) => setEditorJson(e.target.value)} />
          </label>

          {saveError ? <div className="alert error">{saveError}</div> : null}
          {saveMessage ? <div className="alert success">{saveMessage}</div> : null}

          <div className="device-drawer-actions">
            <button type="button" className="btn btn-secondary" onClick={() => setEditorOpen(false)}>
              Cancelar
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Guardando...' : editorMode === 'create' ? 'Crear' : 'Guardar'}
            </button>
          </div>
        </div>
      </aside>

      <div className={`device-drawer-overlay${editorOpen ? ' open' : ''}`} onClick={() => setEditorOpen(false)} />
    </PageCard>
  );
}