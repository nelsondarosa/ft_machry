import { useMemo, useState } from 'react'
import { EmptyState, Metric, PageHeading, Pagination, SearchSelect } from './components'
import type { FichaTecnica, Lote, Produto, SolicitacaoProducao, TipoProduto } from './types'

const number = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })
const date = new Intl.DateTimeFormat('pt-BR')
const labels = { INSUMO: 'Insumo', INTERMEDIARIO: 'Intermediário', FINAL: 'Produto final' }

export function DashboardPage({ produtos, fichas, lotes, canManage, onNewSheet, onEditSheet }: { produtos: Produto[]; fichas: FichaTecnica[]; lotes: Lote[]; canManage: boolean; onNewSheet: () => void; onEditSheet: (ficha: FichaTecnica) => void }) {
  const lotesComSaldo = lotes.filter((lote) => lote.quantidade > 0)
  const unidadesCadastradas = lotesComSaldo.reduce((total, lote) => total + lote.itens_total - lote.itens_consumidos, 0)
  return <><section className="hero"><div><span className="eyebrow">CENTRAL DE OPERAÇÕES</span><h1>Sua cozinha, <em>sob controle.</em></h1><p>Produtos, receitas, estoque e produção reunidos em uma visão simples para a rotina do estabelecimento.</p></div>{canManage && <button className="primary" onClick={onNewSheet}>Nova ficha técnica</button>}</section><section className="metrics"><Metric label="PRODUTOS ATIVOS" value={produtos.length} detail="itens cadastrados" /><Metric label="FICHAS TÉCNICAS" value={fichas.length} detail="receitas padronizadas" /><Metric label="UNIDADES CADASTRADAS" value={unidadesCadastradas} detail={`em ${lotesComSaldo.length} ${lotesComSaldo.length === 1 ? 'lote ativo' : 'lotes ativos'}`} /></section><section className="panel"><div className="panel-title"><div><span className="eyebrow">RECEITAS</span><h2>Fichas recentes</h2></div>{canManage && <button className="text-button" onClick={onNewSheet}>Adicionar ficha →</button>}</div>{fichas.length ? <div className="recipe-grid">{fichas.slice(0, 6).map((ficha) => <article className="recipe-card" key={ficha.id}><span className="type">FICHA #{ficha.id}</span><h3>{ficha.produto}</h3><p>{ficha.observacao || 'Receita padronizada para a equipe.'}</p><div><span>{ficha.fases.length} fases</span><span>{ficha.componentes.length} componentes</span><span>{number.format(ficha.rendimento)} {ficha.unidade_rendimento}</span></div>{canManage && <button className="text-button" onClick={() => onEditSheet(ficha)}>Editar ficha →</button>}</article>)}</div> : <EmptyState title="Nenhuma ficha cadastrada" text="Cadastre a primeira receita para padronizar o preparo." />}</section></>
}

export function ProductsPage({ produtos, onNew, onImport, onEdit }: { produtos: Produto[]; onNew: () => void; onImport: () => void; onEdit: (produto: Produto) => void }) {
  const [query, setQuery] = useState('')
  const [tipo, setTipo] = useState<TipoProduto | 'TODOS'>('TODOS')
  const [subdivisao, setSubdivisao] = useState('')
  const [pagina, setPagina] = useState(1)
  const porPagina = 20
  const counts = useMemo(() => ({
    TODOS: produtos.length,
    INSUMO: produtos.filter((item) => item.tipo === 'INSUMO').length,
    INTERMEDIARIO: produtos.filter((item) => item.tipo === 'INTERMEDIARIO').length,
    FINAL: produtos.filter((item) => item.tipo === 'FINAL').length,
  }), [produtos])
  const subdivisoes = useMemo(() => [...new Set(produtos
    .filter((item) => tipo === 'TODOS' || item.tipo === tipo)
    .map((item) => item.subdivisao?.trim())
    .filter((value): value is string => Boolean(value)))]
    .sort((a, b) => a.localeCompare(b, 'pt-BR')), [produtos, tipo])
  const filtered = useMemo(() => {
    const search = query.trim().toLocaleLowerCase('pt-BR')
    return produtos.filter((item) => {
      if (tipo !== 'TODOS' && item.tipo !== tipo) return false
      if (subdivisao && item.subdivisao !== subdivisao) return false
      return !search || `${item.nome} ${item.subdivisao ?? ''} ${item.unidade_medida}`.toLocaleLowerCase('pt-BR').includes(search)
    }).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [produtos, tipo, subdivisao, query])
  const totalPaginas = Math.max(1, Math.ceil(filtered.length / porPagina))
  const paginaAtual = Math.min(pagina, totalPaginas)
  const visiveis = filtered.slice((paginaAtual - 1) * porPagina, paginaAtual * porPagina)
  const alterarTipo = (novo: TipoProduto | 'TODOS') => { setTipo(novo); setSubdivisao(''); setPagina(1) }

  return <>
    <PageHeading eyebrow="CATÁLOGO" title="Produtos" description="Catálogo organizado por insumos, preparos intermediários e produtos finais." action={<div className="heading-actions"><button className="secondary outline" onClick={onImport}>Importar CSV</button><button className="primary" onClick={onNew}>Novo produto</button></div>} />
    <section className="panel catalog-panel">
      <div className="catalog-tabs" role="group" aria-label="Tipo de produto">
        {([['TODOS', 'Todos'], ['INSUMO', 'Insumos'], ['INTERMEDIARIO', 'Intermediários'], ['FINAL', 'Produtos finais']] as const).map(([value, label]) => (
          <button key={value} type="button" aria-pressed={tipo === value} className={tipo === value ? 'active' : ''} onClick={() => alterarTipo(value)}>
            {label}<span>{counts[value]}</span>
          </button>
        ))}
      </div>
      <div className="catalog-filters">
        <label>Pesquisar produto<input value={query} onChange={(event) => { setQuery(event.target.value); setPagina(1) }} placeholder="Nome, subdivisão ou unidade" /></label>
        <label>Subdivisão<SearchSelect ariaLabel="Subdivisão" value={subdivisao} onChange={(value) => { setSubdivisao(value); setPagina(1) }} options={[{ value: '', label: 'Todas' }, ...subdivisoes.map((value) => ({ value, label: value }))]} /></label>
        <span className="catalog-total" aria-live="polite">{filtered.length} produto(s)</span>
      </div>
      <div className="table-wrap"><table><thead><tr><th>Produto</th><th>Tipo</th><th>Subdivisão</th><th>Unidade</th><th>Conservação</th><th>Validade padrão</th><th>Ação</th></tr></thead>
        <tbody>{visiveis.map((produto) => <tr key={produto.id}>
          <td><strong>{produto.nome}</strong><small className="catalog-id">#{produto.id}</small></td>
          <td><span className={`badge ${produto.tipo.toLowerCase()}`}>{labels[produto.tipo]}</span></td>
          <td>{produto.subdivisao || '—'}</td><td>{produto.unidade_medida}</td>
          <td>{produto.conservacao.toLowerCase()}</td><td>{produto.validade_padrao_dias == null ? '—' : `${produto.validade_padrao_dias} dias`}</td>
          <td><button className="text-button" onClick={() => onEdit(produto)}>Editar</button></td>
        </tr>)}</tbody>
      </table></div>
      {!filtered.length && <EmptyState title="Nenhum produto encontrado" text={produtos.length ? 'Ajuste a busca, a categoria ou a subdivisão.' : 'Cadastre o primeiro produto para começar.'} />}
      <Pagination page={paginaAtual} perPage={porPagina} total={filtered.length} label="Paginação de produtos" onChange={setPagina} />
    </section>
  </>
}

export function SheetsPage({ fichas, canManage, onNew, onImport, onEdit }: { fichas: FichaTecnica[]; canManage: boolean; onNew: () => void; onImport: () => void; onEdit: (ficha: FichaTecnica) => void }) {
  const [pagina, setPagina] = useState(1)
  const porPagina = 12
  const totalPaginas = Math.max(1, Math.ceil(fichas.length / porPagina))
  const paginaAtual = Math.min(pagina, totalPaginas)
  const visiveis = fichas.slice((paginaAtual - 1) * porPagina, paginaAtual * porPagina)
  return <><PageHeading eyebrow="PADRONIZAÇÃO" title="Fichas técnicas" description="Rendimento, etapas e componentes de cada preparo da cozinha." action={canManage ? <div className="heading-actions"><button className="secondary outline" onClick={onImport}>Importar CSV</button><button className="primary" onClick={onNew}>Nova ficha</button></div> : undefined} />{fichas.length ? <><div className="recipe-grid">{visiveis.map((ficha) => <article className="recipe-card panel" key={ficha.id}><span className="type">#{ficha.id}</span><h3>{ficha.produto}</h3><p>{ficha.observacao || 'Sem observações.'}</p><div><span>{number.format(ficha.rendimento)} {ficha.unidade_rendimento}</span><span>{ficha.fases.length} fases</span></div><ol className="phase-list">{ficha.fases.map((fase) => <li key={fase.id}><span>{fase.ordem}</span>{fase.fase}<small>{fase.tempo_previsto_min} min</small></li>)}</ol>{canManage && <button className="text-button" onClick={() => onEdit(ficha)}>Editar ficha →</button>}</article>)}</div><Pagination page={paginaAtual} perPage={porPagina} total={fichas.length} label="Paginação de fichas técnicas" onChange={(value) => { setPagina(value); window.scrollTo({ top: 0, behavior: 'smooth' }) }} /></> : <section className="panel"><EmptyState title="Nenhuma ficha cadastrada" text="Crie a primeira ficha técnica da cozinha." /></section>}</>
}

export function ProductionPage({ solicitacoes, fichas, canPlan, onCreate, onStatus }: { solicitacoes: SolicitacaoProducao[]; fichas: FichaTecnica[]; canPlan: boolean; onCreate: (fichaId: number) => Promise<void>; onStatus: (id: number, status: string) => Promise<void> }) {
  const productBySheet = new Map(fichas.map((ficha) => [ficha.id, ficha.produto]))
  const [selectedSheet, setSelectedSheet] = useState(fichas[0]?.id ?? 0)
  const [submitting, setSubmitting] = useState(false)
  const create = async () => { if (!selectedSheet) return; setSubmitting(true); try { await onCreate(selectedSheet) } finally { setSubmitting(false) } }
  const update = async (id: number, status: string) => { setSubmitting(true); try { await onStatus(id, status) } finally { setSubmitting(false) } }
  return <><PageHeading eyebrow="COZINHA" title="Produção" description="Fila de preparos definida pelo gestor para a equipe da cozinha." action={<button className="secondary no-print" onClick={() => window.print()}>Imprimir fila</button>} /><section className="metrics"><Metric label="SOLICITAÇÕES" value={solicitacoes.length} detail="total registrado" /><Metric label="EM ANDAMENTO" value={solicitacoes.filter((item) => !['CONCLUIDA', 'CANCELADA'].includes(item.status)).length} detail="aguardando conclusão" /><Metric label="CONCLUÍDAS" value={solicitacoes.filter((item) => item.status === 'CONCLUIDA').length} detail="produções finalizadas" /></section>{canPlan && <section className="panel production-planner"><div><span className="eyebrow">SOLICITAÇÕES DE PRODUÇÃO</span><h2>Adicionar preparo</h2></div><SearchSelect ariaLabel="Ficha técnica" placeholder="Buscar ficha técnica" value={selectedSheet} onChange={setSelectedSheet} options={fichas.map((ficha) => ({ value: ficha.id, label: fichaLabel(ficha) }))} /><button className="primary" disabled={!selectedSheet || submitting} onClick={() => void create()}>Adicionar à fila</button></section>}<section className="panel"><div className="table-wrap"><table><thead><tr><th>Solicitação</th><th>Produto</th><th>Status</th><th>Criada em</th><th>Concluída em</th><th>Ação</th></tr></thead><tbody>{solicitacoes.map((item) => <tr key={item.id}><td>#{item.id}</td><td><strong>{productBySheet.get(item.ficha_tecnica_id) || `Ficha #${item.ficha_tecnica_id}`}</strong></td><td><span className={`badge status-${item.status.toLowerCase()}`}>{item.status.replaceAll('_', ' ')}</span></td><td>{date.format(new Date(item.criado_em))}</td><td>{item.concluido_em ? date.format(new Date(item.concluido_em)) : '—'}</td><td>{['ABERTA', 'EM_SEPARACAO'].includes(item.status) ? <button className="text-button" disabled={submitting} onClick={() => void update(item.id, 'EM_PRODUCAO')}>Iniciar</button> : item.status === 'EM_PRODUCAO' ? <button className="text-button" disabled={submitting} onClick={() => void update(item.id, 'CONCLUIDA')}>Concluir</button> : '—'}</td></tr>)}</tbody></table></div>{!solicitacoes.length && <EmptyState title="Nenhum preparo na fila" text="O gestor ainda não definiu a produção." />}</section></>
}

const fichaLabel = (ficha: FichaTecnica) => `${ficha.produto} · ${number.format(ficha.rendimento)} ${ficha.unidade_rendimento}`
