import { useState, type FormEvent } from 'react'
import { api } from './api'
import type { Usuario } from './types'

export function LoginPage({ onLogin }: { onLogin: (usuario: Usuario) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setLoading(true)
    try {
      const usuario = await api<Usuario>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) })
      onLogin(usuario)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Não foi possível entrar.')
    } finally { setLoading(false) }
  }

  return <main className="login-page">
    <section className="login-brand"><div className="login-mark">M</div><span className="eyebrow">MACHRY · GESTÃO DE COZINHA</span><h1>Organize o trabalho de hoje.</h1><p>Estoque, fichas técnicas e produção em um só lugar para toda a equipe.</p><div className="login-feature"><span>01</span><div><strong>Planejamento claro</strong><small>Cada pessoa vê exatamente o que precisa fazer.</small></div></div><div className="login-feature"><span>02</span><div><strong>Receitas padronizadas</strong><small>Etapas e quantidades sempre disponíveis.</small></div></div></section>
    <section className="login-panel"><form className="login-card" onSubmit={submit}><span className="eyebrow">ACESSO AO SISTEMA</span><h2>Bem-vindo</h2><p>Entre com o usuário fornecido pela proprietária.</p>{error && <p className="form-error">{error}</p>}<label>Usuário<input autoComplete="username" autoFocus required value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Seu usuário" /></label><label>Senha<input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Sua senha" /></label><button className="primary login-submit" disabled={loading}>{loading ? 'Entrando…' : 'Entrar'}</button><small className="login-help">Em caso de dificuldade, fale com a proprietária ou o gestor.</small></form></section>
  </main>
}
