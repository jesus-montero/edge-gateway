import { useCallback, useEffect, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus, faTrashCan } from '@fortawesome/free-solid-svg-icons';
import { PageCard } from '../components/PageCard';
import { createRule, deleteRule, getRule, getRules, updateRule, type BackendRule } from '../services/api';

type RuleEditorMode = 'create' | 'edit';
type RuleActionForm = { device: string; command: string };

export function RulesPage() {
  const [rules, setRules] = useState<BackendRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedRuleName, setSelectedRuleName] = useState<string | null>(null);
  const [editorMode, setEditorMode] = useState<RuleEditorMode>('edit');
  const [ruleName, setRuleName] = useState('');
  const [whenSource, setWhenSource] = useState('');
  const [whenType, setWhenType] = useState('');
  const [actionsForm, setActionsForm] = useState<RuleActionForm[]>([{ device: '', command: '' }]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const loadRules = useCallback(async () => {
    try {
      setLoading(true);
      const result = await getRules();
      setRules(result.rules ?? []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar la lista de reglas');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadRules();
  }, [loadRules]);

  function openNewRuleDrawer() {
    setEditorMode('create');
    setSelectedRuleName('new');
    setRuleName('');
    setWhenSource('');
    setWhenType('');
    setActionsForm([{ device: '', command: '' }]);
    setSaveError(null);
  }

  async function openExistingRuleDrawer(rule: BackendRule) {
    try {
      setEditorMode('edit');
      setSaveError(null);
      const response = await getRule(rule.name);
      const current = response.rule;

      setSelectedRuleName(rule.name);
      setRuleName(current.name ?? rule.name);
      setWhenSource(String((current.when as { source?: unknown })?.source ?? ''));
      setWhenType(String((current.when as { type?: unknown })?.type ?? ''));

      const nextActions = Array.isArray(current.actions)
        ? current.actions.map((action) => ({
            device: String((action as { device?: unknown })?.device ?? ''),
            command: String((action as { command?: unknown })?.command ?? ''),
          }))
        : [];

      setActionsForm(nextActions.length > 0 ? nextActions : [{ device: '', command: '' }]);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo cargar la regla');
    }
  }

  function handleActionChange(index: number, field: keyof RuleActionForm, value: string) {
    setActionsForm((current) => current.map((action, i) => (i === index ? { ...action, [field]: value } : action)));
  }

  function handleAddAction() {
    setActionsForm((current) => [...current, { device: '', command: '' }]);
  }

  function handleRemoveAction(index: number) {
    setActionsForm((current) => {
      const next = current.filter((_, i) => i !== index);
      return next.length > 0 ? next : [{ device: '', command: '' }];
    });
  }

  async function handleSaveRule() {
    setSaving(true);
    setSaveError(null);

    try {
      const trimmedRuleName = ruleName.trim();
      const trimmedWhenSource = whenSource.trim();
      const trimmedWhenType = whenType.trim();

      if (!trimmedRuleName) {
        throw new Error('El nombre de la regla es obligatorio');
      }

      if (!trimmedWhenSource || !trimmedWhenType) {
        throw new Error('when.source y when.type son obligatorios');
      }

      const normalizedActions = actionsForm
        .map((action) => ({ device: action.device.trim(), command: action.command.trim() }))
        .filter((action) => action.device || action.command);

      if (normalizedActions.length === 0) {
        throw new Error('Debe existir al menos una acción con device y command');
      }

      const hasInvalidAction = normalizedActions.some((action) => !action.device || !action.command);
      if (hasInvalidAction) {
        throw new Error('Cada acción debe incluir device y command');
      }

      const payloadWhen: Record<string, unknown> = {
        source: trimmedWhenSource,
        type: trimmedWhenType,
      };
      const payloadActions = normalizedActions as Record<string, unknown>[];

      if (editorMode === 'create') {
        const payload: BackendRule = {
          name: trimmedRuleName,
          when: payloadWhen,
          actions: payloadActions,
        };
        await createRule(payload);
      } else if (selectedRuleName) {
        await updateRule(selectedRuleName, {
          when: payloadWhen,
          actions: payloadActions,
        });
      }

      setSelectedRuleName(null);
      await loadRules();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo guardar la regla');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteRule(rule: BackendRule) {
    const confirmed = window.confirm(`¿Eliminar la regla "${rule.name}"? Esta acción no se puede deshacer.`);
    if (!confirmed) {
      return;
    }

    try {
      await deleteRule(rule.name);
      if (selectedRuleName === rule.name) {
        setSelectedRuleName(null);
      }
      await loadRules();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo eliminar la regla');
    }
  }

  return (
    <PageCard
      title="Reglas"
      description="Listado y edición de reglas when/actions"
      headerActions={
        <button
          type="button"
          className="device-add-button"
          aria-label="Añadir regla"
          title="Añadir regla"
          onClick={openNewRuleDrawer}
        >
          <FontAwesomeIcon icon={faPlus} />
        </button>
      }
    >
      {loading ? (
        <div className="muted-block">Cargando reglas...</div>
      ) : error ? (
        <div className="alert error">{error}</div>
      ) : rules.length === 0 ? (
        <div className="empty-state">
          <strong>No hay reglas configuradas.</strong>
          <p>Puedes crear nuevas reglas pulsando el botón +.</p>
        </div>
      ) : (
        <>
          {saveError ? <div className="alert error">{saveError}</div> : null}

          <div className="metrics-grid devices-grid">
            {rules.map((rule) => {
              const ruleActions = Array.isArray(rule.actions) ? rule.actions : [];
              const previewActions = ruleActions.slice(0, 3);
              const hiddenActionsCount = Math.max(ruleActions.length - previewActions.length, 0);

              return (
                <div
                  key={rule.name}
                  role="button"
                  tabIndex={0}
                  className="metric device-card device-card-button"
                  onClick={() => void openExistingRuleDrawer(rule)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      void openExistingRuleDrawer(rule);
                    }
                  }}
                >
                  <span>Rule</span>
                  <strong>{rule.name}</strong>
                  <div className="device-details">
                    <small>When source: {String((rule.when as { source?: unknown })?.source ?? '-')}</small>
                    <small>When type: {String((rule.when as { type?: unknown })?.type ?? '-')}</small>
                    {previewActions.length === 0 ? (
                      <small>Actions: sin acciones</small>
                    ) : (
                      previewActions.map((action, index) => {
                        const device = String((action as { device?: unknown })?.device ?? '-');
                        const command = String((action as { command?: unknown })?.command ?? '-');
                        return (
                          <small key={`${rule.name}-action-${index}`}>
                            Action {index + 1}: {device}{' -> '}{command}
                          </small>
                        );
                      })
                    )}
                    {hiddenActionsCount > 0 ? <small>+{hiddenActionsCount} acciones más...</small> : null}
                  </div>
                  <button
                    type="button"
                    className="device-delete-button"
                    aria-label={`Eliminar regla ${rule.name}`}
                    title="Eliminar regla"
                    onClick={(event) => {
                      event.stopPropagation();
                      void handleDeleteRule(rule);
                    }}
                  >
                    <FontAwesomeIcon icon={faTrashCan} />
                  </button>
                </div>
              );
            })}
          </div>

        </>
      )}

      <aside
        className={`device-drawer${selectedRuleName ? ' open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-hidden={!selectedRuleName}
      >
        <div className="device-drawer-header">
          <div>
            <p className="device-drawer-eyebrow">
              {editorMode === 'create' ? 'Alta de regla' : 'Edición de regla'}
            </p>
            <h3>{editorMode === 'create' ? 'Nueva regla' : ruleName || 'Sin seleccionar'}</h3>
          </div>
          <button type="button" className="btn btn-secondary" onClick={() => setSelectedRuleName(null)}>
            Cerrar
          </button>
        </div>

        {selectedRuleName ? (
          <div className="device-drawer-body">
            {saveError ? <div className="alert error">{saveError}</div> : null}

            <div className="device-form-grid">
              <label className="device-field">
                <span>Nombre</span>
                <input
                  type="text"
                  value={ruleName}
                  disabled={editorMode === 'edit'}
                  onChange={(event) => setRuleName(event.target.value)}
                />
              </label>

              <label className="device-field">
                <span>When source</span>
                <input
                  type="text"
                  value={whenSource}
                  onChange={(event) => setWhenSource(event.target.value)}
                />
              </label>

              <label className="device-field">
                <span>When type</span>
                <input
                  type="text"
                  value={whenType}
                  onChange={(event) => setWhenType(event.target.value)}
                />
              </label>
            </div>

            <div className="device-form-grid" style={{ marginTop: '1rem' }}>
              <div className="device-field" style={{ gridColumn: '1 / -1' }}>
                <span>Actions</span>
              </div>

              {actionsForm.map((action, index) => (
                <div key={`action-${index}`} className="device-form-grid" style={{ gridColumn: '1 / -1' }}>
                  <label className="device-field">
                    <span>Device</span>
                    <input
                      type="text"
                      value={action.device}
                      onChange={(event) => handleActionChange(index, 'device', event.target.value)}
                    />
                  </label>

                  <label className="device-field">
                    <span>Command</span>
                    <input
                      type="text"
                      value={action.command}
                      onChange={(event) => handleActionChange(index, 'command', event.target.value)}
                    />
                  </label>

                  <div className="device-drawer-actions" style={{ marginTop: 0 }}>
                    <button type="button" className="btn btn-secondary" onClick={() => handleRemoveAction(index)}>
                      Quitar acción
                    </button>
                  </div>
                </div>
              ))}

              <div className="device-drawer-actions" style={{ gridColumn: '1 / -1', justifyContent: 'flex-start' }}>
                <button type="button" className="btn btn-secondary" onClick={handleAddAction}>
                  Añadir acción
                </button>
              </div>
            </div>

            <div className="device-drawer-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setSelectedRuleName(null)}>
                Cancelar
              </button>
              <button type="button" className="btn btn-primary" onClick={handleSaveRule} disabled={saving}>
                {saving ? 'Guardando...' : editorMode === 'create' ? 'Crear regla' : 'Guardar cambios'}
              </button>
            </div>
          </div>
        ) : null}
      </aside>

      <div className={`device-drawer-overlay${selectedRuleName ? ' open' : ''}`} onClick={() => setSelectedRuleName(null)} />
    </PageCard>
  );
}