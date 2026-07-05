import type { ReactNode } from 'react';

type PageCardProps = {
  title: string;
  description: string;
  children: ReactNode;
  headerActions?: ReactNode;
};

export function PageCard({ title, description, children, headerActions }: PageCardProps) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div className="panel-header-copy">
          <div className="panel-title-row">
            <h2>{title}</h2>
            {headerActions ? <div className="panel-header-actions">{headerActions}</div> : null}
          </div>
          <p>{description}</p>
        </div>
      </div>
      {children}
    </section>
  );
}