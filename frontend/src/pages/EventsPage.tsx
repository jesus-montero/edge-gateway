import { PageCard } from '../components/PageCard';

export function EventsPage() {
  return (
    <PageCard title="Eventos" description="Página placeholder para eventos entrantes y procesados.">
      <div className="empty-state">
        <strong>El registro de eventos está vacío.</strong>
        <p>Más adelante esta página puede mostrar resultados de despacho, errores y auditoría.</p>
      </div>
    </PageCard>
  );
}