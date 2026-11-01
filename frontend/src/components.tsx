import type { ReactNode } from 'react'
import type { Usuario, View } from './types'

const primaryNavigation: Array<[View, string, string]> = [
  ['inicio', '⌂', 'Visão geral'], ['produtos', '◫', 'Produtos'], ['fichas', '≡', 'Fichas técnicas'],
  ['estoque', '▦', 'Estoque'], ['producao', '◉', 'Produção'],
]
const titles: Record<View, string> = {
  inicio: 'Visão geral', produtos: 'Produtos', fichas: 'Fichas técnicas', estoque: 'Estoque', producao: 'Produção',
}

export function Shell({ view, menuOpen, apiOnline, usuario, onNavigate, onMenuToggle, onLogout, children }: {
  view: View; menuOpen: boolean; apiOnline: boolean; usuario: Usuario; onNavigate: (view: View) => void; onMenuToggle: () => void; onLogout: () => void; children: ReactNode
}) {
  const allowedViews: Record<Usuario['papel'], View[]> = {
    OWNER: ['inicio', 'produtos', 'fichas', 'estoque', 'producao'],
    ADMIN: ['inicio', 'fichas', 'estoque', 'producao'],
    USER: ['fichas', 'producao'],
  }
  const visibleNavigation = primaryNavigation.filter(([target]) => allowedViews[usuario.papel].includes(target))
  const roleLabel = { OWNER: 'Proprietária', ADMIN: 'Gestor', USER: 'Cozinha' }[usuario.papel]
  const navButton = ([target, icon, label]: [View, string, string]) => <button className={`nav ${view === target ? 'active' : ''}`} key={target} onClick={() => onNavigate(target)} type="button"><span aria-hidden="true">{icon}</span>{label}</button>
  return <div className="layout">
    <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark">M</div><div><strong>Machry</strong><small>GESTÃO DE COZINHA</small></div></div>
      <p className="nav-caption">OPERAÇÃO</p><nav>{visibleNavigation.map((item) => navButton(item))}</nav>
      <div className="account"><div className="account-avatar">{usuario.nome.charAt(0).toUpperCase()}</div><div><strong>{usuario.nome}</strong><small>{roleLabel}</small></div><button onClick={onLogout} type="button">Sair</button></div>
      <div className={`api-state ${apiOnline ? '' : 'offline'}`}><i /><div><strong>{apiOnline ? 'API conectada' : 'API indisponível'}</strong><small>Flask · banco integrado</small></div></div>
    </aside>
    <main><header><button className="menu" onClick={onMenuToggle} aria-label="Abrir menu" type="button">☰</button><div><small>ÁREA ATUAL</small><strong>{titles[view]}</strong></div><span className="environment">Ambiente local</span></header><div className="content">{children}</div></main>
    {menuOpen && <button className="sidebar-scrim" onClick={onMenuToggle} aria-label="Fechar menu" type="button" />}
  </div>
}

export function Metric({ label, value, detail }: { label: string; value: ReactNode; detail: string }) {
  return <article className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></article>
}

export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>
}

export function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty"><strong>{title}</strong><p>{text}</p></div>
}

export function Modal({ title, eyebrow, wide, children, footer, onClose }: { title: string; eyebrow: string; wide?: boolean; children: ReactNode; footer: ReactNode; onClose: () => void }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><section className={`dialog modal-card ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}><div className="dialog-head"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><button className="icon-button" onClick={onClose} aria-label="Fechar" type="button">×</button></div>{children}<div className="dialog-actions">{footer}</div></section></div>
}
