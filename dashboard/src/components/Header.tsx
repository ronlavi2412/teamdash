interface HeaderProps {
  title: string;
  subtitle: string;
  generated: string;
  isCurrentQuarter: boolean;
}

export function Header({ title, subtitle, generated, isCurrentQuarter }: HeaderProps) {
  return (
    <div className="header">
      <h1 dangerouslySetInnerHTML={{ __html: title }} />
      <p>{subtitle} &middot; Generated {generated}</p>
      {isCurrentQuarter && (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 8 }}>
          <em>* Striped bars and dashed lines indicate in-progress quarter with incomplete data</em>
        </p>
      )}
    </div>
  );
}
