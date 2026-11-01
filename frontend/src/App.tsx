import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from './api'
import { Shell } from './components'
import { ProductModal, SheetModal, StockModal } from './forms'
import { LoginPage } from './LoginPage'
import { DashboardPage, ProductionPage, ProductsPage, SheetsPage, StockPage } from './pages'
import type { FaseCatalogo, FichaTecnica, ItemInventario, Localizacao, Lote, Produto, SolicitacaoProducao, Usuario, View } from './types'

export function App() {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined)
  const [view, setView] = useState<View>('inicio')
  const [menuOpen, setMenuOpen] = useState(false)
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [fichas, setFichas] = useState<FichaTecnica[]>([])
  const [fases, setFases] = useState<FaseCatalogo[]>([])
  const [inventario, setInventario] = useState<ItemInventario[]>([])
  const [lotes, setLotes] = useState<Lote[]>([])
  const [localizacoes, setLocalizacoes] = useState<Localizacao[]>([])
  const [solicitacoes, setSolicitacoes] = useState<SolicitacaoProducao[]>([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [productModal, setProductModal] = useState<Produto | 'new' | null>(null)
  const [sheetModal, setSheetModal] = useState<FichaTecnica | 'new' | null>(null)
  const [stockModal, setStockModal] = useState<Lote | 'new' | null>(null)
  const [toast, setToast] = useState<{ text: string; error?: boolean } | null>(null)

  const load = useCallback(async (loggedUser: Usuario) => {
    setLoading(true)
    setLoadError('')
    try {
      const canSeeCatalog = loggedUser.papel !== 'USER'
      const canSeeStock = loggedUser.papel !== 'USER'
      const [loadedProducts, loadedSheets, loadedPhases, loadedStock, loadedLots, loadedLocations, loadedProduction] = await Promise.all([
        canSeeCatalog ? api<Produto[]>('/api/produtos') : Promise.resolve([]),
        api<FichaTecnica[]>('/api/fichas-tecnicas'), api<FaseCatalogo[]>('/api/fichas-tecnicas/fases'),
        canSeeStock ? api<ItemInventario[]>('/api/estoque/inventario') : Promise.resolve([]),
        canSeeStock ? api<Lote[]>('/api/estoque/lotes') : Promise.resolve([]),
        canSeeStock ? api<Localizacao[]>('/api/estoque/localizacoes') : Promise.resolve([]),
        api<SolicitacaoProducao[]>('/api/producao/solicitacoes'),
      ])
      setProdutos(loadedProducts); setFichas(loadedSheets); setFases(loadedPhases); setInventario(loadedStock); setLotes(loadedLots); setLocalizacoes(loadedLocations); setSolicitacoes(loadedProduction)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setUsuario(null)
      else setLoadError(reason instanceof Error ? reason.message : 'Não foi possível carregar o sistema.')
    } finally { setLoading(false) }
  }, [])
  useEffect(() => {
    api<Usuario>('/api/auth/me').then((loggedUser) => { setUsuario(loggedUser); setView(loggedUser.papel === 'USER' ? 'producao' : 'inicio'); void load(loggedUser) }).catch(() => setUsuario(null))
  }, [load])
  useEffect(() => { if (!toast) return; const timeout = window.setTimeout(() => setToast(null), 3200); return () => window.clearTimeout(timeout) }, [toast])
  const navigate = (target: View) => { setView(target); setMenuOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const mutationDone = async (message: string) => { setProductModal(null); setSheetModal(null); setStockModal(null); if (usuario) await load(usuario); setToast({ text: message }) }
  const loggedIn = (loggedUser: Usuario) => { setUsuario(loggedUser); setView(loggedUser.papel === 'USER' ? 'producao' : 'inicio'); void load(loggedUser) }
  const logout = async () => { await api('/api/auth/logout', { method: 'POST' }).catch(() => undefined); setUsuario(null); setProdutos([]); setFichas([]); setInventario([]); setSolicitacoes([]) }
  const createProduction = async (fichaId: number) => {
    try { await api('/api/producao/solicitacoes', { method: 'POST', body: JSON.stringify({ ficha_tecnica_id: fichaId }) }); await load(usuario!); setToast({ text: 'Preparo adicionado à fila.' }) }
    catch (reason) { setToast({ text: reason instanceof Error ? reason.message : 'Não foi possível adicionar o preparo.', error: true }) }
  }
  const updateProduction = async (id: number, status: string) => {
    try { await api(`/api/producao/solicitacoes/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }); await load(usuario!); setToast({ text: status === 'CONCLUIDA' ? 'Preparo concluído.' : 'Preparo iniciado.' }) }
    catch (reason) { setToast({ text: reason instanceof Error ? reason.message : 'Não foi possível atualizar o preparo.', error: true }) }
  }

  if (usuario === undefined) return <div className="app-loading"><div className="brand-mark">M</div><span>Carregando Machry…</span></div>
  if (usuario === null) return <LoginPage onLogin={loggedIn} />
  const canManageCatalog = usuario.papel === 'OWNER'

  let page
  if (loading) page = <section className="panel load-error">Carregando dados da operação…</section>
  else if (loadError) page = <section className="panel load-error"><strong>Não foi possível acessar a API</strong><p>{loadError}</p><button className="primary" onClick={() => void load(usuario)}>Tentar novamente</button></section>
  else if (view === 'inicio') page = <DashboardPage produtos={produtos} fichas={fichas} inventario={inventario} canManage={canManageCatalog} onNewSheet={() => setSheetModal('new')} onEditSheet={setSheetModal} />
  else if (view === 'produtos') page = <ProductsPage produtos={produtos} onNew={() => setProductModal('new')} onEdit={setProductModal} />
  else if (view === 'fichas') page = <SheetsPage fichas={fichas} canManage={canManageCatalog} onNew={() => setSheetModal('new')} onEdit={setSheetModal} />
  else if (view === 'estoque') page = <StockPage inventario={inventario} lotes={lotes} onNew={() => setStockModal('new')} onMove={setStockModal} />
  else if (view === 'producao') page = <ProductionPage solicitacoes={solicitacoes} fichas={fichas} canPlan={usuario.papel !== 'USER'} onCreate={createProduction} onStatus={updateProduction} />
  else page = <ProductionPage solicitacoes={solicitacoes} fichas={fichas} canPlan={usuario.papel !== 'USER'} onCreate={createProduction} onStatus={updateProduction} />

  return <><Shell view={view} menuOpen={menuOpen} apiOnline={!loadError} usuario={usuario} onNavigate={navigate} onMenuToggle={() => setMenuOpen((open) => !open)} onLogout={() => void logout()}>{page}</Shell>
    {productModal && <ProductModal produto={productModal === 'new' ? null : productModal} onClose={() => setProductModal(null)} onSaved={() => void mutationDone('Produto salvo com sucesso.')} onDeleted={() => void mutationDone('Produto excluído.')} />}
    {sheetModal && <SheetModal ficha={sheetModal === 'new' ? null : sheetModal} produtos={produtos} catalogoFases={fases} onClose={() => setSheetModal(null)} onSaved={() => void mutationDone('Ficha técnica salva com sucesso.')} onDeleted={() => void mutationDone('Ficha técnica excluída.')} />}
    {stockModal && <StockModal lote={stockModal === 'new' ? null : stockModal} produtos={produtos} localizacoes={localizacoes} usuarioId={usuario.id} onClose={() => setStockModal(null)} onSaved={() => void mutationDone('Estoque atualizado com sucesso.')} />}
    {toast && <div className={`toast show ${toast.error ? 'error' : ''}`}>{toast.text}</div>}
  </>
}
