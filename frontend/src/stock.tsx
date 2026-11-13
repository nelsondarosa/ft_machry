import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { api, apiListAll } from './api'
import { EmptyState, Metric, Modal, MoneyInput, PageHeading, SearchSelect } from './components'
import type { ItemLote, Localizacao, Lote, Produto, StatusItem, TipoProduto } from './types'

type Situacao = 'EM_DIA' | 'ATENCAO' | 'VENCIDO' | 'SEM_VALIDADE' | 'ESGOTADO'
type FiltroSituacao = 'TODAS' | Situacao
type Aba = 'ITENS' | 'MOVIMENTAR' | 'TRANSFERIR' | 'HISTORICO'
type ModoItens = 'VER' | 'EDITAR' | 'ADICIONAR'
type Operacao = 'TRANSFERENCIA' | 'TRANSFORMACAO'
type Movimento = {
  id: number
  tipo: string
  lote_id: number
  lote_destino_id: number | null
  quantidade: number
  quantidade_destino: number | null
  motivo: string | null
  usuario_id: number
  observacao: string | null
  criado_em: string
}

const DIAS_ATENCAO = 10
const DIA_MS = 86400000
const numero = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })
const tipoLabels: Record<TipoProduto, string> = { INSUMO: 'Insumo', INTERMEDIARIO: 'Intermediário', FINAL: 'Produto final' }
const statusLabels: Record<StatusItem, string> = { DISPONIVEL: 'Disponível', RESERVADA: 'Reservada', EM_USO: 'Em uso', CONSUMIDA: 'Consumida' }
const movimentoLabels: Record<string, string> = {
  ENTRADA: 'Entrada', SAIDA: 'Saída', PRODUCAO: 'Produção', CONSUMO_PRODUCAO: 'Consumo na produção',
  TRANSFERENCIA: 'Transferência', TRANSFORMACAO: 'Transformação', AJUSTE_ENTRADA: 'Ajuste de entrada', AJUSTE_SAIDA: 'Ajuste de saída',
}

const hojeIso = () => new Date().toLocaleDateString('sv-SE')
const paraData = (valor: string | null) => {
  if (!valor) return null
  const data = new Date(valor.length === 10 ? `${valor}T12:00:00` : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? null : data
}
const formatarData = (valor: string | null) => paraData(valor)?.toLocaleDateString('pt-BR') ?? '—'
const formatarDiaMes = (valor: string | null) => paraData(valor)?.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) ?? '—'
const formatarDataHora = (valor: string) => paraData(valor)?.toLocaleString('pt-BR') ?? valor
const inicioDoDia = (data: Date) => new Date(data.getFullYear(), data.getMonth(), data.getDate()).getTime()
const diasAte = (valor: string | null) => {
  const data = paraData(valor)
  return data ? Math.round((inicioDoDia(data) - inicioDoDia(new Date())) / DIA_MS) : null
}
const mensagemErro = (reason: unknown) => reason instanceof Error ? reason.message : 'Não foi possível concluir a operação.'

const dataEntrada = (lote: Lote) => lote.data_producao ?? lote.criado_em
const temItens = (lote: Lote) => lote.itens_total > 0
const itensAtivos = (lote: Lote) => lote.itens_total - lote.itens_consumidos - lote.itens_vencidos
const itemVencido = (item: ItemLote) =>
  item.status !== 'CONSUMIDA' && (diasAte(item.data_validade) ?? 0) < 0

function situacaoDo(lote: Lote): { tipo: Situacao; texto: string } {
  if (lote.quantidade <= 0) return { tipo: 'ESGOTADO', texto: 'Esgotado' }
  const dias = diasAte(lote.data_validade)
  if (dias === null) return { tipo: 'SEM_VALIDADE', texto: 'Sem validade' }
  if (dias < 0) return { tipo: 'VENCIDO', texto: `Vencido há ${-dias} ${-dias === 1 ? 'dia' : 'dias'}` }
  if (dias === 0) return { tipo: 'ATENCAO', texto: 'Vence hoje' }
  if (dias <= DIAS_ATENCAO) return { tipo: 'ATENCAO', texto: `Atenção · ${dias} ${dias === 1 ? 'dia' : 'dias'}` }
  return { tipo: 'EM_DIA', texto: `Em dia · ${dias} dias` }
}

function caminhoLocalizacao(id: number, porId: Map<number, Localizacao>, fallback: string) {
  const partes: string[] = []
  const visitados = new Set<number>()
  let atual = porId.get(id)
  while (atual && !visitados.has(atual.id)) {
    visitados.add(atual.id)
    partes.unshift(atual.nome)
    atual = atual.parent_id ? porId.get(atual.parent_id) : undefined
  }
  return partes.length ? partes.join(' · ') : fallback
}

function ordemDeUso(a: ItemLote, b: ItemLote) {
  if (a.status !== b.status && (a.status === 'EM_USO' || b.status === 'EM_USO')) return a.status === 'EM_USO' ? -1 : 1
  const validadeA = a.data_validade ?? '9999-12-31'
  const validadeB = b.data_validade ?? '9999-12-31'
  return validadeA.localeCompare(validadeB) || a.codigo.localeCompare(b.codigo)
}

type Contexto = {
  produtosPorId: Map<number, Produto>
  locaisPorId: Map<number, Localizacao>
}

function useItensDoLote(loteId: number | null, ativo: boolean) {
  const [itens, setItens] = useState<ItemLote[] | null>(null)
  const [erro, setErro] = useState('')
  const [versao, setVersao] = useState(0)
  const recarregar = useCallback(() => setVersao((valor) => valor + 1), [])

  useEffect(() => {
    if (!loteId || !ativo) { setItens([]); return }
    let vigente = true
    setErro('')
    apiListAll<ItemLote>(`/api/estoque/lotes/${loteId}/itens`)
      .then((dados) => { if (vigente) setItens(dados) })
      .catch((reason) => { if (vigente) setErro(mensagemErro(reason)) })
    return () => { vigente = false }
  }, [loteId, ativo, versao])

  return { itens, erro, recarregar }
}

export function StockPage({ lotes, produtos, localizacoes, usuarioId, onChanged }: {
  lotes: Lote[]
  produtos: Produto[]
  localizacoes: Localizacao[]
  usuarioId: number
  onChanged: (mensagem: string) => Promise<void>
}) {
  const [tipo, setTipo] = useState<TipoProduto | 'TODOS'>('TODOS')
  const [situacao, setSituacao] = useState<FiltroSituacao>('TODAS')
  const [busca, setBusca] = useState('')
  const [aberto, setAberto] = useState<{ loteId: number | null; aba: Aba } | null>(null)
  const [novoLote, setNovoLote] = useState(false)

  const contexto: Contexto = useMemo(() => ({
    produtosPorId: new Map(produtos.map((item) => [item.id, item])),
    locaisPorId: new Map(localizacoes.map((item) => [item.id, item])),
  }), [produtos, localizacoes])

  const comSaldo = lotes.filter((lote) => lote.quantidade > 0)
  const situacoes = new Map(lotes.map((lote) => [lote.id, situacaoDo(lote)]))
  const contar = (alvo: Situacao) => comSaldo.filter((lote) => situacoes.get(lote.id)?.tipo === alvo).length
  const lotesAtivos = comSaldo.length - contar('VENCIDO')
  const unidadesCadastradas = comSaldo.reduce((total, lote) => total + itensAtivos(lote), 0)

  const termo = busca.trim().toLocaleLowerCase('pt-BR').replace(/^#/, '')
  const visiveis = lotes
    .filter((lote) => situacao === 'ESGOTADO' ? lote.quantidade <= 0 : lote.quantidade > 0)
    .filter((lote) => situacao === 'TODAS' || situacao === 'ESGOTADO' || situacoes.get(lote.id)?.tipo === situacao)
    .filter((lote) => tipo === 'TODOS' || contexto.produtosPorId.get(lote.produto_id)?.tipo === tipo)
    .filter((lote) => !termo || String(lote.id) === termo || lote.produto.toLocaleLowerCase('pt-BR').includes(termo))
    .sort((a, b) => (a.data_validade ?? '9999').localeCompare(b.data_validade ?? '9999') || a.id - b.id)

  const loteAberto = aberto?.loteId ? lotes.find((lote) => lote.id === aberto.loteId) ?? null : null

  return <>
    <PageHeading
      eyebrow="CONTROLE GERAL"
      title="Estoque"
      description="Veja todos os lotes com entrada, validade e situação. Clique em um lote para ver os itens que ele contém."
      action={<div className="heading-actions">
        <button className="secondary outline" type="button" onClick={() => setAberto({ loteId: null, aba: 'TRANSFERIR' })}>Transferir ou transformar</button>
        <button className="primary" type="button" onClick={() => setNovoLote(true)}>+ Novo lote</button>
      </div>}
    />

    <section className="metrics four">
      <Metric label="LOTES ATIVOS" value={lotesAtivos} detail="com saldo disponível e dentro de validade" />
      <Metric label="UNIDADES CADASTRADAS" value={unidadesCadastradas} detail="itens rastreados individualmente" />
      <article className="metric warning">
        <span>ATENÇÃO À VALIDADE</span>
        <strong>{contar('ATENCAO')}</strong>
        <small>{contar('ATENCAO') === 1 ? 'lote vence' : 'lotes vencem'} em até {DIAS_ATENCAO} dias</small>
      </article>
      <article className="metric danger">
        <span>VENCIDOS</span>
        <strong>{contar('VENCIDO')}</strong>
        <small>{contar('VENCIDO') === 1 ? 'lote' : 'lotes'} para descarte</small>
      </article>
    </section>

    <section className="panel">
      <div className="stock-toolbar">
        <div className="stock-tabs">
          {([['TODOS', 'Todos'], ['INSUMO', 'Insumos'], ['INTERMEDIARIO', 'Intermediários'], ['FINAL', 'Produtos finais']] as const).map(([valor, label]) =>
            <button type="button" className={tipo === valor ? 'active' : ''} onClick={() => setTipo(valor)} key={valor}>{label}</button>)}
        </div>
        <div className="stock-filters">
          <label>
            Situação
            <SearchSelect<FiltroSituacao>
              ariaLabel="Situação"
              value={situacao}
              onChange={setSituacao}
              options={[
                { value: 'TODAS', label: 'Todas' },
                { value: 'EM_DIA', label: 'Em dia' },
                { value: 'ATENCAO', label: 'Atenção' },
                { value: 'VENCIDO', label: 'Vencidos' },
                { value: 'SEM_VALIDADE', label: 'Sem validade' },
                { value: 'ESGOTADO', label: 'Esgotados' },
              ]}
            />
          </label>
          <input value={busca} onChange={(event) => setBusca(event.target.value)} placeholder="Buscar lote ou produto" aria-label="Buscar lote ou produto" />
        </div>
      </div>

      <div className="table-wrap">
        <table className="stock-table">
          <thead>
            <tr><th>Lote</th><th>Produto</th><th>Tipo</th><th>Itens</th><th>Entrada</th><th>Vencimento</th><th>Localização</th><th>Situação</th><th /></tr>
          </thead>
          <tbody>
            {visiveis.map((lote) => {
              const produto = contexto.produtosPorId.get(lote.produto_id)
              const sit = situacoes.get(lote.id)!
              return <tr key={lote.id} className={`row-${sit.tipo.toLowerCase()}`}>
                <td><strong>#{lote.id}</strong></td>
                <td>{lote.produto}</td>
                <td>{produto && <span className={`badge ${produto.tipo.toLowerCase()}`}>{tipoLabels[produto.tipo]}</span>}</td>
                <td><ResumoItens lote={lote} unidade={produto?.unidade_medida ?? ''} vencido={sit.tipo === 'VENCIDO'} /></td>
                <td>{formatarData(dataEntrada(lote))}</td>
                <td><strong>{formatarData(lote.data_validade)}</strong></td>
                <td>{caminhoLocalizacao(lote.localizacao_id, contexto.locaisPorId, lote.localizacao)}</td>
                <td><span className={`pill ${sit.tipo.toLowerCase()}`}>{sit.texto}</span></td>
                <td><button className="secondary outline small" type="button" onClick={() => setAberto({ loteId: lote.id, aba: 'ITENS' })}>Ver itens</button></td>
              </tr>
            })}
          </tbody>
        </table>
      </div>
      {!visiveis.length && <EmptyState title="Nenhum lote encontrado" text="Ajuste os filtros ou cadastre um novo lote." />}
      <div className="stock-legend">
        <span><i className="disponivel" />Disponível</span>
        <span><i className="reservada" />Reservado</span>
        <span><i className="em_uso" />Em uso</span>
        <span><i className="consumida" />Consumido</span>
        <span><i className="vencido" />Vencido</span>
      </div>
    </section>

    {aberto && <LotModal
      lote={loteAberto}
      abaInicial={aberto.aba}
      lotes={lotes}
      produtos={produtos}
      contexto={contexto}
      usuarioId={usuarioId}
      onClose={() => setAberto(null)}
      onChanged={onChanged}
      onFinishedWithoutLot={() => setAberto(null)}
    />}

    {novoLote && <NewLotModal
      produtos={produtos}
      localizacoes={localizacoes}
      usuarioId={usuarioId}
      onClose={() => setNovoLote(false)}
      onSaved={async (loteId) => {
        setNovoLote(false)
        await onChanged(`Lote #${loteId} criado.`)
      }}
    />}
  </>
}

function ResumoItens({ lote, unidade, vencido }: { lote: Lote; unidade: string; vencido: boolean }) {
  if (!temItens(lote)) {
    return <div className="item-summary">
      <span><strong>{numero.format(lote.quantidade)} {unidade}</strong> · sem itens</span>
    </div>
  }
  return <div className="item-summary">
    <span><strong>{itensAtivos(lote)} un</strong> · {lote.itens_disponiveis} {lote.itens_disponiveis === 1 ? 'disponível' : 'disponíveis'}{lote.itens_vencidos > 0 && ` · ${lote.itens_vencidos} ${lote.itens_vencidos === 1 ? 'vencida' : 'vencidas'}`}</span>
    <BarraStatus lote={lote} vencido={vencido} />
  </div>
}

function BarraStatus({ lote, vencido }: { lote: Lote; vencido?: boolean }) {
  if (vencido) return <div className="status-bar"><i className="vencido" style={{ flex: 1 }} /></div>
  const partes: Array<[string, number]> = [
    ['disponivel', lote.itens_disponiveis],
    ['reservada', lote.itens_reservados],
    ['em_uso', lote.itens_em_uso],
    ['vencido', lote.itens_vencidos],
    ['consumida', lote.itens_consumidos],
  ]
  return <div className="status-bar">
    {partes.filter(([, quantidade]) => quantidade > 0).map(([classe, quantidade]) => <i key={classe} className={classe} style={{ flex: quantidade }} />)}
  </div>
}

function LotModal({ lote, abaInicial, lotes, produtos, contexto, usuarioId, onClose, onChanged, onFinishedWithoutLot }: {
  lote: Lote | null
  abaInicial: Aba
  lotes: Lote[]
  produtos: Produto[]
  contexto: Contexto
  usuarioId: number
  onClose: () => void
  onChanged: (mensagem: string) => Promise<void>
  onFinishedWithoutLot: () => void
}) {
  const [aba, setAba] = useState<Aba>(abaInicial)
  const [modo, setModo] = useState<ModoItens>('VER')
  const [origemId, setOrigemId] = useState<number | ''>(lote?.id ?? '')
  const [salvando, setSalvando] = useState(false)
  const origem = lote ?? lotes.find((item) => item.id === origemId) ?? null
  const produto = origem ? contexto.produtosPorId.get(origem.produto_id) : undefined
  const unidade = produto?.unidade_medida ?? ''
  const sit = origem ? situacaoDo(origem) : null
  const { itens, erro: erroItens, recarregar } = useItensDoLote(lote?.id ?? null, Boolean(lote && temItens(lote)))

  const trocarAba = (valor: Aba) => { setAba(valor); setModo('VER') }
  const concluir = async (mensagem: string) => {
    await onChanged(mensagem)
    recarregar()
    setModo('VER')
    if (lote) setAba('ITENS')
    else onFinishedWithoutLot()
  }

  let formId: string | undefined
  let textoSalvar = ''
  if (aba === 'MOVIMENTAR') { formId = 'move-form'; textoSalvar = 'Registrar movimento' }
  else if (aba === 'TRANSFERIR') { formId = 'transfer-form'; textoSalvar = 'Registrar operação' }
  else if (modo === 'EDITAR') { formId = 'lot-edit-form'; textoSalvar = 'Salvar lote' }
  else if (modo === 'ADICIONAR') { formId = 'add-items-form'; textoSalvar = 'Adicionar itens' }
  const podeAdicionarItens = lote !== null && (temItens(lote) || lote.quantidade === 0)

  function cancelar() {
    if (modo !== 'VER') setModo('VER')
    else if (lote && aba !== 'ITENS') trocarAba('ITENS')
    else onClose()
  }

  const footer = <>
    <button className="secondary outline" type="button" onClick={formId ? cancelar : onClose}>
      {formId ? 'Cancelar' : 'Fechar'}
    </button>
    <span className="dialog-actions-spacer" />
    {aba === 'ITENS' && modo === 'VER' && lote && <>
      <button className="secondary outline" type="button" onClick={() => setModo('EDITAR')}>Editar lote</button>
      <button
        className="primary"
        type="button"
        disabled={!podeAdicionarItens}
        title={podeAdicionarItens ? undefined : 'Este lote tem saldo sem itens. Zere o saldo (ajuste de saída) para passar a controlá-lo por itens.'}
        onClick={() => setModo('ADICIONAR')}
      >+ Adicionar itens</button>
    </>}
    {formId && <button className="primary" form={formId} type="submit" disabled={salvando || (aba === 'TRANSFERIR' && !origem)}>
      {salvando ? 'Salvando…' : textoSalvar}
    </button>}
  </>

  const subtitulo = !origem
    ? 'Escolha o lote de origem e o destino da operação.'
    : temItens(origem)
      ? `${origem.produto} · ${origem.itens_disponiveis} ${origem.itens_disponiveis === 1 ? 'unidade disponível' : 'unidades disponíveis'} · ${numero.format(origem.quantidade)} ${unidade} em estoque`
      : `${origem.produto} · ${numero.format(origem.quantidade)} ${unidade} em estoque`

  return <Modal
    wide
    title={lote ? `Lote #${lote.id}` : 'Transferir ou transformar'}
    titleAside={lote && <>
      {produto && <span className={`badge ${produto.tipo.toLowerCase()}`}>{tipoLabels[produto.tipo]}</span>}
      {sit && <span className={`pill ${sit.tipo.toLowerCase()}`}>{sit.texto}</span>}
    </>}
    subtitle={subtitulo}
    onClose={onClose}
    footer={footer}
  >
    {lote && <nav className="modal-tabs" aria-label="Seções do lote">
      {([['ITENS', temItens(lote) ? `Itens (${itensAtivos(lote)})` : 'Detalhes'], ['TRANSFERIR', 'Transferir ou transformar'], ['MOVIMENTAR', 'Movimentar'], ['HISTORICO', 'Histórico']] as const).map(([valor, label]) =>
        <button type="button" key={valor} className={aba === valor ? 'active' : ''} onClick={() => trocarAba(valor)}>{label}</button>)}
    </nav>}
    <div className="dialog-body lot-body">
      {aba === 'ITENS' && lote && modo === 'VER' && <LotDetails lote={lote} contexto={contexto} usuarioId={usuarioId} itens={itens} erroItens={erroItens} onItemChanged={concluir} />}
      {aba === 'ITENS' && lote && modo === 'EDITAR' && <LotEditForm lote={lote} produto={produto} contexto={contexto} onSaving={setSalvando} onSaved={() => concluir(`Lote #${lote.id} atualizado.`)} />}
      {aba === 'ITENS' && lote && modo === 'ADICIONAR' && <AddItemsForm lote={lote} unidade={unidade} validadeObrigatoria={Boolean(produto?.validade_obrigatoria)} validadePadraoDias={produto?.validade_padrao_dias} usuarioId={usuarioId} onSaving={setSalvando} onSaved={(quantidade) => concluir(`${quantidade} ${quantidade === 1 ? 'item adicionado' : 'itens adicionados'} ao lote #${lote.id}.`)} />}
      {aba === 'TRANSFERIR' && <>
        {!lote && <label className="field">
          Lote de origem
          <SearchSelect<number | ''>
            required
            ariaLabel="Lote de origem"
            placeholder="Buscar lote"
            value={origemId}
            onChange={setOrigemId}
            options={[{ value: '', label: 'Selecione' }, ...lotes.filter((item) => item.quantidade > 0).map((item) => ({
              value: item.id,
              label: `#${item.id} — ${item.produto} (${numero.format(item.quantidade)} ${contexto.produtosPorId.get(item.produto_id)?.unidade_medida ?? ''})`,
            }))]}
          />
        </label>}
        {origem
          ? <TransferForm key={origem.id} origem={origem} lotes={lotes} produtos={produtos} contexto={contexto} usuarioId={usuarioId} onSaving={setSalvando} onSaved={concluir} />
          : <EmptyState title="Selecione um lote" text="A operação parte de um lote com saldo disponível." />}
      </>}
      {aba === 'MOVIMENTAR' && lote && <MoveForm lote={lote} unidade={unidade} usuarioId={usuarioId} onSaving={setSalvando} onSaved={concluir} />}
      {aba === 'HISTORICO' && lote && <LotHistory lote={lote} />}
    </div>
  </Modal>
}

function LotDetails({ lote, contexto, usuarioId, itens, erroItens, onItemChanged }: {
  lote: Lote
  contexto: Contexto
  usuarioId: number
  itens: ItemLote[] | null
  erroItens: string
  onItemChanged: (mensagem: string) => Promise<void>
}) {
  const produto = contexto.produtosPorId.get(lote.produto_id)
  const unidade = produto?.unidade_medida ?? ''
  const sit = situacaoDo(lote)
  const vida = vidaUtil(lote)

  return <>
    <div className="info-grid">
      <div><span>ENTRADA</span><strong>{formatarData(dataEntrada(lote))}</strong></div>
      <div><span>VENCIMENTO</span><strong>{formatarData(lote.data_validade)}</strong></div>
      <div><span>LOCALIZAÇÃO</span><strong>{caminhoLocalizacao(lote.localizacao_id, contexto.locaisPorId, lote.localizacao)}</strong></div>
      <div><span>FORNECEDOR</span><strong>{lote.fornecedor ?? '—'}</strong></div>
    </div>

    {temItens(lote)
      ? <>
        <div className="lot-section">
          <div className="lot-section-head">
            <h3>Situação dos itens</h3>
            {vida && <small>{vida.decorridos} de {vida.total} dias de vida útil decorridos</small>}
          </div>
          <BarraStatus lote={lote} />
          <div className="status-counts">
            <span><i className="disponivel" /><strong>{lote.itens_disponiveis}</strong> disponíveis</span>
            <span><i className="reservada" /><strong>{lote.itens_reservados}</strong> reservadas</span>
            <span><i className="em_uso" /><strong>{lote.itens_em_uso}</strong> em uso</span>
            <span><i className="vencido" /><strong>{lote.itens_vencidos}</strong> vencidas</span>
            <span><i className="consumida" /><strong>{lote.itens_consumidos}</strong> consumidas</span>
          </div>
        </div>
        <ItemsTable loteId={lote.id} usuarioId={usuarioId} itens={itens} erro={erroItens} unidade={unidade} onItemChanged={onItemChanged} />
      </>
      : <>
        <div className="lot-section">
          <div className="lot-section-head">
            <h3>Vida útil</h3>
            {vida && <small>{vida.decorridos} de {vida.total} dias de vida útil decorridos</small>}
          </div>
          {vida ? <div className={`life-bar ${sit.tipo.toLowerCase()}`}><i style={{ width: `${(vida.decorridos / vida.total) * 100}%` }} /></div> : <p className="helper">Lote sem data de validade cadastrada.</p>}
        </div>
        <p className="notice">
          Este lote é controlado só pela quantidade total, sem itens individuais.{' '}
          {lote.quantidade === 0
            ? 'Como está sem saldo, você pode passar a controlá-lo por itens com “+ Adicionar itens”.'
            : 'Para cadastrar itens, primeiro zere o saldo com “Movimentar” → ajuste de saída, ou crie um novo lote já com os itens.'}
        </p>
      </>}

  </>
}

function vidaUtil(lote: Lote) {
  const inicio = paraData(dataEntrada(lote))
  const fim = paraData(lote.data_validade)
  if (!inicio || !fim) return null
  const total = Math.max(1, Math.round((inicioDoDia(fim) - inicioDoDia(inicio)) / DIA_MS))
  const decorridos = Math.min(total, Math.max(0, Math.round((inicioDoDia(new Date()) - inicioDoDia(inicio)) / DIA_MS)))
  return { total, decorridos }
}

function ItemsTable({ loteId, usuarioId, itens, erro, unidade, onItemChanged }: {
  loteId: number
  usuarioId: number
  itens: ItemLote[] | null
  erro: string
  unidade: string
  onItemChanged: (mensagem: string) => Promise<void>
}) {
  const [filtro, setFiltro] = useState<StatusItem | 'VENCIDA' | 'TODOS'>('TODOS')
  const [itemEmAcao, setItemEmAcao] = useState<number | null>(null)
  const [erroAcao, setErroAcao] = useState('')

  async function executar(item: ItemLote, acao: () => Promise<unknown>, mensagem: string) {
    setItemEmAcao(item.id); setErroAcao('')
    try {
      await acao()
      await onItemChanged(mensagem)
    } catch (reason) { setErroAcao(mensagemErro(reason)) } finally { setItemEmAcao(null) }
  }

  function abrir(item: ItemLote) {
    void executar(item, () => api(`/api/estoque/itens/${item.id}/abrir`, { method: 'POST' }), `${item.codigo} aberto.`)
  }

  function consumir(item: ItemLote) {
  const vencido = itemVencido(item)
  void executar(item, () => api('/api/estoque/movimentacoes', {
    method: 'POST',
    body: JSON.stringify({ tipo: 'SAIDA', lote_id: loteId, usuario_id: usuarioId, item_ids: [item.id], motivo: vencido ? 'Item vencido' : 'Item consumido' }),
  }), vencido ? `${item.codigo} saiu do estoque (vencido).` : `${item.codigo} consumido.`)
}

  if (erro) return <p className="form-error">{erro}</p>
  if (!itens) return <p className="helper">Carregando itens…</p>
  const visiveis = itens.filter((item) => {
    if (filtro === 'TODOS') return true
    if (filtro === 'VENCIDA') return itemVencido(item)
    return item.status === filtro && !itemVencido(item)
  })
  const ativos = itens.filter((item) => item.status !== 'CONSUMIDA' && !itemVencido(item)).length

  return <div className="lot-section">
    <div className="lot-section-head">
      <h3>Itens do lote ({ativos})</h3>
      <div className="stock-tabs compact">
        {([['TODOS', 'Todos'], ['DISPONIVEL', 'Disponíveis'], ['RESERVADA', 'Reservadas'], ['EM_USO', 'Em uso'], ['VENCIDA', 'Vencidas'], ['CONSUMIDA', 'Consumidas']] as const).map(([valor, label]) =>
          <button type="button" key={valor} className={filtro === valor ? 'active' : ''} onClick={() => setFiltro(valor)}>{label}</button>)}
      </div>
    </div>
    {erroAcao && <p className="form-error">{erroAcao}</p>}
    <div className="table-wrap items-table">
      <table>
        <thead>
          <tr><th>Código</th><th>Fabricante</th><th>Fabricação</th><th>Validade</th><th>Conteúdo</th><th>Status</th><th>Destino</th><th /></tr>
        </thead>
        <tbody>
          {visiveis.map((item) => <tr key={item.id}>
            <td><strong>{item.codigo}</strong></td>
            <td>{item.fabricante ?? '—'}</td>
            <td>{formatarData(item.data_fabricacao)}</td>
            <td><strong>{formatarData(item.data_validade)}</strong></td>
            <td>{item.saldo < item.quantidade && item.saldo > 0
              ? `${numero.format(item.saldo)} de ${numero.format(item.quantidade)} ${unidade}`
              : `${numero.format(item.quantidade)} ${unidade}`}</td>
            <td>{itemVencido(item)
              ? <span className="pill vencido">Vencido</span>
              : <span className={`pill item-${item.status.toLowerCase()}`}>{statusLabels[item.status]}</span>}</td>
            <td>{destinoDoItem(item)}</td>
            <td><div className="item-actions">
              {itemEmAcao === item.id && <span className="helper">Salvando…</span>}
              {itemEmAcao !== item.id && item.status === 'DISPONIVEL' && !itemVencido(item) && <button type="button" className="text-button" disabled={itemEmAcao !== null} onClick={() => abrir(item)}>Abrir</button>}
              {itemEmAcao !== item.id && (item.status === 'DISPONIVEL' || item.status === 'EM_USO') && <button type="button" className="text-button" disabled={itemEmAcao !== null} onClick={() => consumir(item)}>{itemVencido(item) ? 'Dar saída' : 'Consumir'}</button>}
            </div></td>
          </tr>)}
        </tbody>
      </table>
    </div>
    {!visiveis.length && <p className="helper">Nenhum item com este status.</p>}
  </div>
}

function destinoDoItem(item: ItemLote) {
  if (item.status === 'EM_USO') return item.aberto_em ? `Aberta em ${formatarDiaMes(item.aberto_em)}` : 'Aberta'
  if (item.status === 'RESERVADA') return item.solicitacao_producao_id ? `Produção #${item.solicitacao_producao_id}` : 'Reservada'
  if (item.status === 'CONSUMIDA') return 'Consumida'
  return '—'
}

// validadeManual: o usuário editou a validade, então ela não é mais sugerida automaticamente.
type Grupo = { chave: number; unidades: string; conteudo: string; fabricante: string; fabricacao: string; validade: string; validadeManual: boolean }

let proximaChave = 1
const grupoVazio = (): Grupo => ({ chave: proximaChave++, unidades: '1', conteudo: '', fabricante: '', fabricacao: '', validade: '', validadeManual: false })
const numeroDe = (texto: string) => Number(texto.replace(',', '.'))

/** Validade sugerida = data base (AAAA-MM-DD) + validade padrão do produto em dias. */
function sugerirValidade(base: string, dias: number | null | undefined): string {
  if (!base || dias == null) return ''
  const [ano, mes, dia] = base.split('-').map(Number)
  if (!ano || !mes || !dia) return ''
  return new Date(ano, mes - 1, dia + dias).toLocaleDateString('sv-SE')
}

const sugerirValidadeDosGrupos = (grupos: Grupo[], dias: number | null | undefined) =>
  grupos.map((grupo) => grupo.validadeManual ? grupo : { ...grupo, validade: sugerirValidade(grupo.fabricacao, dias) })

function gruposParaApi(grupos: Grupo[]) {
  return grupos.map((grupo) => ({
    quantidade_unidades: Math.trunc(numeroDe(grupo.unidades)),
    quantidade: numeroDe(grupo.conteudo),
    fabricante: grupo.fabricante.trim() || null,
    data_fabricacao: grupo.fabricacao || null,
    data_validade: grupo.validade || null,
  }))
}

function resumoDosGrupos(grupos: Grupo[]) {
  const unidades = grupos.reduce((total, grupo) => total + (Math.trunc(numeroDe(grupo.unidades)) || 0), 0)
  const quantidade = grupos.reduce((total, grupo) => total + (Math.trunc(numeroDe(grupo.unidades)) || 0) * (numeroDe(grupo.conteudo) || 0), 0)
  const validades = grupos.map((grupo) => grupo.validade).filter(Boolean).sort()
  return { unidades, quantidade, menorValidade: validades[0] ?? '' }
}

function Rotulo({ texto, opcional }: { texto: string; opcional?: boolean }) {
  return <span className="field-title">{texto}{opcional && <small className="optional"> (opcional)</small>}</span>
}

function GroupsEditor({ grupos, unidade, pedirValidade, validadeObrigatoria, validadePadraoDias, onChange }: {
  grupos: Grupo[]
  unidade: string
  pedirValidade: boolean
  validadeObrigatoria: boolean
  validadePadraoDias?: number | null
  onChange: (grupos: Grupo[]) => void
}) {
  const atualizar = (chave: number, campos: Partial<Grupo>) => onChange(grupos.map((grupo) => grupo.chave === chave ? { ...grupo, ...campos } : grupo))
  const trocarFabricacao = (grupo: Grupo, fabricacao: string) => atualizar(grupo.chave, grupo.validadeManual || !pedirValidade
    ? { fabricacao }
    : { fabricacao, validade: sugerirValidade(fabricacao, validadePadraoDias) })
  const remover = (chave: number) => onChange(grupos.filter((grupo) => grupo.chave !== chave))

  return <div className="groups">
    <div className="groups-head">
      <span>Grupos de unidades <small>· use mais de um quando a marca, a validade ou o tamanho mudar</small></span>
      <button type="button" className="chip-button" onClick={() => onChange([...grupos, grupoVazio()])}>+ Grupo</button>
    </div>
    {grupos.map((grupo, indice) => <fieldset className={pedirValidade ? 'group-row' : 'group-row sem-validade'} key={grupo.chave}>
      <legend>Grupo {indice + 1}</legend>
      <label>Unidades<input type="number" min="1" max="500" step="1" required value={grupo.unidades} onChange={(event) => atualizar(grupo.chave, { unidades: event.target.value })} /></label>
      <label>Conteúdo por unidade ({unidade || 'un'})<input type="number" min="0.001" step="any" required value={grupo.conteudo} onChange={(event) => atualizar(grupo.chave, { conteudo: event.target.value })} placeholder="Ex.: 1000" /></label>
      <label><Rotulo texto="Fabricante / marca" opcional /><input maxLength={100} value={grupo.fabricante} onChange={(event) => atualizar(grupo.chave, { fabricante: event.target.value })} placeholder="Ex.: Tio João" /></label>
      <label><Rotulo texto="Fabricação" opcional /><input type="date" value={grupo.fabricacao} onChange={(event) => trocarFabricacao(grupo, event.target.value)} /></label>
      {pedirValidade && <label><Rotulo texto="Validade" opcional={!validadeObrigatoria} /><input type="date" required={validadeObrigatoria} value={grupo.validade} onChange={(event) => atualizar(grupo.chave, { validade: event.target.value, validadeManual: true })} /></label>}
      {grupos.length > 1 && <button type="button" className="remove-row" aria-label={`Remover grupo ${indice + 1}`} onClick={() => remover(grupo.chave)}>×</button>}
    </fieldset>)}
  </div>
}

function AddItemsForm({ lote, unidade, validadeObrigatoria, validadePadraoDias, usuarioId, onSaving, onSaved }: {
  lote: Lote
  unidade: string
  validadeObrigatoria: boolean
  validadePadraoDias?: number | null
  usuarioId: number
  onSaving: (valor: boolean) => void
  onSaved: (quantidade: number) => Promise<void>
}) {
  const [grupos, setGrupos] = useState<Grupo[]>(() => [grupoVazio()])
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState('')
  const resumo = resumoDosGrupos(grupos)

  async function salvar(event: FormEvent) {
    event.preventDefault(); setErro(''); onSaving(true)
    try {
      const criados = await api<ItemLote[]>(`/api/estoque/lotes/${lote.id}/itens`, {
        method: 'POST',
        body: JSON.stringify({ usuario_id: usuarioId, itens: gruposParaApi(grupos), observacao: observacao.trim() || null }),
      })
      await onSaved(criados.length)
    } catch (reason) { setErro(mensagemErro(reason)) } finally { onSaving(false) }
  }

  return <form id="add-items-form" className="lot-form" onSubmit={salvar}>
    {erro && <p className="form-error">{erro}</p>}
    <p className="helper">Cada unidade recebe um código próprio ({`FT-${String(lote.id).padStart(3, '0')}-…`}).{validadeObrigatoria && ' Grupos sem validade usam a validade do lote.'}</p>
    <GroupsEditor grupos={grupos} unidade={unidade} pedirValidade={validadeObrigatoria} validadeObrigatoria={validadeObrigatoria && !lote.data_validade} validadePadraoDias={validadePadraoDias} onChange={setGrupos} />
    <label><Rotulo texto="Observação" opcional /><input value={observacao} onChange={(event) => setObservacao(event.target.value)} placeholder="Vai junto com a entrada" /></label>
    <div className="transfer-summary">
      <div><span>Unidades</span><strong>+{resumo.unidades}</strong></div>
      <div><span>Quantidade</span><strong>+{numero.format(resumo.quantidade)} {unidade}</strong></div>
      <div><span>Lote depois da entrada</span><strong>{numero.format(lote.quantidade + resumo.quantidade)} {unidade}</strong></div>
    </div>
  </form>
}

function NewLotModal({ produtos, localizacoes, usuarioId, onClose, onSaved }: {
  produtos: Produto[]
  localizacoes: Localizacao[]
  usuarioId: number
  onClose: () => void
  onSaved: (loteId: number) => Promise<void>
}) {
  const [produtoId, setProdutoId] = useState<number | ''>('')
  const produto = produtos.find((item) => item.id === produtoId)
  const unidade = produto?.unidade_medida ?? ''
  const locaisCompativeis = localizacoes.filter((item) => !produto || item.tipo === produto.conservacao)
  const [localizacaoId, setLocalizacaoId] = useState<number | ''>('')
  const [entrada, setEntrada] = useState(hojeIso())
  const [validadeLote, setValidadeLote] = useState('')
  const [validadeLoteManual, setValidadeLoteManual] = useState(false)
  const [fornecedor, setFornecedor] = useState('')
  const [notaFiscal, setNotaFiscal] = useState('')
  const [custo, setCusto] = useState('')
  const [grupos, setGrupos] = useState<Grupo[]>(() => [grupoVazio()])
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)

  const resumo = resumoDosGrupos(grupos)
  const vencimento = resumo.menorValidade || validadeLote
  const temValidade = (item?: Produto) => Boolean(item?.validade_obrigatoria) || item?.validade_padrao_dias != null
  const pedirValidade = temValidade(produto)
  const diasPadrao = produto?.validade_padrao_dias

  function trocarProduto(id: number | '') {
    setProdutoId(id)
    const escolhido = produtos.find((item) => item.id === id)
    setLocalizacaoId(localizacoes.find((item) => item.tipo === escolhido?.conservacao)?.id ?? '')
    // Outro produto tem outra validade padrão: descarta edições manuais e sugere de novo.
    setValidadeLoteManual(false)
    if (!temValidade(escolhido)) {
      setValidadeLote('')
      setGrupos((atuais) => atuais.map((grupo) => ({ ...grupo, validade: '', validadeManual: false })))
      return
    }
    setValidadeLote(sugerirValidade(entrada, escolhido?.validade_padrao_dias))
    setGrupos((atuais) => sugerirValidadeDosGrupos(atuais.map((grupo) => ({ ...grupo, validadeManual: false })), escolhido?.validade_padrao_dias))
  }

  function trocarEntrada(valor: string) {
    setEntrada(valor)
    if (pedirValidade && !validadeLoteManual) setValidadeLote(sugerirValidade(valor, diasPadrao))
  }

  async function salvar(event: FormEvent) {
    event.preventDefault()
    if (!produtoId || !localizacaoId) { setErro('Escolha o produto e a localização.'); return }
    setErro(''); setSalvando(true)
    try {
      const lote = await api<Lote>('/api/estoque/lotes', {
        method: 'POST',
        body: JSON.stringify({
          produto_id: produtoId,
          localizacao_id: localizacaoId,
          data_producao: entrada || null,
          data_validade: validadeLote || null,
          custo_unitario: custo === '' ? null : Number(custo),
          fornecedor: fornecedor.trim() || null,
          nota_fiscal: notaFiscal.trim() || null,
          itens: gruposParaApi(grupos),
          usuario_id: usuarioId,
          observacao: observacao.trim() || null,
        }),
      })
      await onSaved(lote.id)
    } catch (reason) { setErro(mensagemErro(reason)) } finally { setSalvando(false) }
  }

  const footer = <>
    <button className="secondary outline" type="button" onClick={onClose}>Cancelar</button>
    <span className="dialog-actions-spacer" />
    <button className="primary" form="new-lot-form" type="submit" disabled={salvando}>{salvando ? 'Salvando…' : 'Salvar lote'}</button>
  </>

  return <Modal wide eyebrow="ESTOQUE" title="Novo lote" subtitle="Registre a entrada e as unidades que chegaram; cada unidade recebe um código próprio." onClose={onClose} footer={footer}>
    <form id="new-lot-form" className="dialog-body lot-body new-lot" onSubmit={salvar}>
      {erro && <p className="form-error">{erro}</p>}

      <section className="lot-section">
        <h3>Dados do lote</h3>
        <div className="form-grid">
          <label>
            Produto
            <SearchSelect<number | ''>
              required
              ariaLabel="Produto"
              placeholder="Buscar produto"
              value={produtoId}
              onChange={trocarProduto}
              options={[{ value: '', label: 'Selecione' }, ...produtos.map((item) => ({ value: item.id, label: `${item.nome} · ${tipoLabels[item.tipo]}` }))]}
            />
          </label>
          <label>
            Localização
            <SearchSelect<number | ''>
              required
              ariaLabel="Localização"
              disabled={!produto}
              placeholder={produto ? 'Buscar localização' : 'Escolha o produto'}
              value={localizacaoId}
              onChange={setLocalizacaoId}
              options={[{ value: '', label: 'Selecione' }, ...locaisCompativeis.map((item) => ({ value: item.id, label: item.nome }))]}
            />
          </label>
          <label><Rotulo texto="Fornecedor" opcional /><input maxLength={150} value={fornecedor} onChange={(event) => setFornecedor(event.target.value)} /></label>
          <label><Rotulo texto="Nota fiscal" opcional /><input maxLength={60} value={notaFiscal} onChange={(event) => setNotaFiscal(event.target.value)} /></label>
          <label><Rotulo texto="Custo unitário" opcional /><MoneyInput value={custo} onChange={setCusto} placeholder="R$ 0,00" /></label>
          <label>Tipo<input value={produto ? tipoLabels[produto.tipo] : ''} placeholder="Definido pelo produto" disabled /></label>
          <label>Data de entrada<input type="date" value={entrada} onChange={(event) => trocarEntrada(event.target.value)} /></label>
          {pedirValidade && <label><Rotulo texto="Validade do lote" opcional /><input type="date" value={validadeLote} onChange={(event) => { setValidadeLote(event.target.value); setValidadeLoteManual(true) }} /></label>}
        </div>
        {pedirValidade && diasPadrao != null && <p className="helper">Validade sugerida pela validade padrão do produto ({diasPadrao} {diasPadrao === 1 ? 'dia' : 'dias'} a partir da entrada ou da fabricação do grupo). Pode ser alterada.</p>}
      </section>

      <section className="lot-section">
        <h3>Itens do lote</h3>
        <GroupsEditor grupos={grupos} unidade={unidade} pedirValidade={pedirValidade} validadeObrigatoria={Boolean(produto?.validade_obrigatoria) && !validadeLote} validadePadraoDias={diasPadrao} onChange={setGrupos} />
        {pedirValidade && <p className="helper">O vencimento do lote passa a ser a validade mais próxima entre as unidades. Grupos sem validade usam a validade do lote.</p>}
        <label><Rotulo texto="Observação" opcional /><textarea rows={3} value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
      </section>

      <div className="transfer-summary four">
        <div><span>Unidades</span><strong>{resumo.unidades}</strong></div>
        <div><span>Quantidade total</span><strong>{numero.format(resumo.quantidade)} {unidade}</strong></div>
        <div><span>Entrada</span><strong>{formatarData(entrada || null)}</strong></div>
        <div><span>Vencimento</span><strong>{produto && !pedirValidade ? 'Sem validade' : formatarData(vencimento || null)}</strong></div>
      </div>
    </form>
  </Modal>
}

function LotEditForm({ lote, produto, contexto, onSaving, onSaved }: {
  lote: Lote
  produto: Produto | undefined
  contexto: Contexto
  onSaving: (valor: boolean) => void
  onSaved: () => Promise<void>
}) {
  const [localizacaoId, setLocalizacaoId] = useState(lote.localizacao_id)
  const [entrada, setEntrada] = useState(lote.data_producao ?? '')
  const [validade, setValidade] = useState(lote.data_validade ?? '')
  const [custo, setCusto] = useState(lote.custo_unitario === null ? '' : lote.custo_unitario.toFixed(2))
  const [fornecedor, setFornecedor] = useState(lote.fornecedor ?? '')
  const [notaFiscal, setNotaFiscal] = useState(lote.nota_fiscal ?? '')
  const [erro, setErro] = useState('')

  async function salvar(event: FormEvent) {
    event.preventDefault(); setErro(''); onSaving(true)
    const campos: Record<string, unknown> = {
      localizacao_id: localizacaoId,
      data_producao: entrada || null,
      custo_unitario: custo === '' ? null : Number(custo),
      fornecedor: fornecedor.trim() || null,
      nota_fiscal: notaFiscal.trim() || null,
    }
    if (!temItens(lote)) campos.data_validade = validade || null
    try {
      await api(`/api/estoque/lotes/${lote.id}`, { method: 'PUT', body: JSON.stringify(campos) })
      await onSaved()
    } catch (reason) { setErro(mensagemErro(reason)) } finally { onSaving(false) }
  }

  const locaisCompativeis = [...contexto.locaisPorId.values()].filter((local) => !produto || local.tipo === produto.conservacao)

  return <form id="lot-edit-form" className="lot-form" onSubmit={salvar}>
    {erro && <p className="form-error">{erro}</p>}
    <div className="form-grid">
      <label>
        Localização
        <SearchSelect
          required
          ariaLabel="Localização"
          placeholder="Buscar localização"
          value={localizacaoId}
          onChange={setLocalizacaoId}
          options={locaisCompativeis.map((local) => ({ value: local.id, label: caminhoLocalizacao(local.id, contexto.locaisPorId, local.nome) }))}
        />
      </label>
      <label><Rotulo texto="Fornecedor" opcional /><input maxLength={150} value={fornecedor} onChange={(event) => setFornecedor(event.target.value)} /></label>
      <label><Rotulo texto="Nota fiscal" opcional /><input maxLength={60} value={notaFiscal} onChange={(event) => setNotaFiscal(event.target.value)} /></label>
      <label><Rotulo texto="Custo unitário" opcional /><MoneyInput value={custo} onChange={setCusto} placeholder="R$ 0,00" /></label>
      <label>Data de entrada<input type="date" value={entrada} onChange={(event) => setEntrada(event.target.value)} /></label>
      <label>
        Validade
        <input type="date" value={validade} disabled={temItens(lote)} onChange={(event) => setValidade(event.target.value)} />
      </label>
    </div>
    {temItens(lote) && <p className="helper">Em lotes com itens, o vencimento é a validade mais próxima entre os itens; edite a validade de cada item.</p>}
  </form>
}

type TipoMovimento = 'ENTRADA' | 'SAIDA' | 'AJUSTE_ENTRADA' | 'AJUSTE_SAIDA'

function MoveForm({ lote, unidade, usuarioId, onSaving, onSaved }: {
  lote: Lote
  unidade: string
  usuarioId: number
  onSaving: (valor: boolean) => void
  onSaved: (mensagem: string) => Promise<void>
}) {
  const porItens = temItens(lote)
  const vencido = situacaoDo(lote).tipo === 'VENCIDO'
  const [tipo, setTipo] = useState<TipoMovimento>(porItens || vencido ? 'SAIDA' : 'ENTRADA')
  const [quantidade, setQuantidade] = useState('')
  const [motivo, setMotivo] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState('')

  const opcoes: { value: TipoMovimento; label: string }[] = vencido
    ? [{ value: 'SAIDA', label: 'Saída' }]
    : porItens
        ? [{ value: 'SAIDA', label: 'Saída' }, { value: 'AJUSTE_SAIDA', label: 'Ajuste de saída' }]
        : [{ value: 'ENTRADA', label: 'Entrada' }, { value: 'SAIDA', label: 'Saída' }, { value: 'AJUSTE_ENTRADA', label: 'Ajuste de entrada' }, { value: 'AJUSTE_SAIDA', label: 'Ajuste de saída' }]
  const pedeMotivo = tipo !== 'ENTRADA'
  const qtd = numeroDe(quantidade) || 0
  const somaNoLote = tipo === 'ENTRADA' || tipo === 'AJUSTE_ENTRADA'
  const saldoDepois = somaNoLote ? lote.quantidade + qtd : lote.quantidade - qtd

  async function salvar(event: FormEvent) {
    event.preventDefault(); setErro(''); onSaving(true)
    try {
      await api('/api/estoque/movimentacoes', {
        method: 'POST',
        body: JSON.stringify({ tipo, lote_id: lote.id, usuario_id: usuarioId, quantidade: qtd, motivo: motivo.trim() || null, observacao: observacao.trim() || null }),
      })
      await onSaved('Movimento registrado.')
    } catch (reason) { setErro(mensagemErro(reason)) } finally { onSaving(false) }
  }

  return <form id="move-form" className="lot-form" onSubmit={salvar}>
    {erro && <p className="form-error">{erro}</p>}
    {porItens && <p className="notice">Lote com itens: a saída consome primeiro os itens abertos e depois os que vencem antes. Para escolher os itens, use a aba “Transferir ou transformar” ou o botão “Consumir” na lista de itens.</p>}
    {vencido && <p className="notice">Lote vencido: só é permitida saída. {porItens && 'Itens vencidos saem pelo botão “Dar saída” na lista de itens; a saída por quantidade usa só os itens dentro da validade.'}</p>}
    <div className="form-grid">
      <label>Movimento<SearchSelect ariaLabel="Tipo de movimentação" value={tipo} onChange={setTipo} options={opcoes} /></label>
      <label>Quantidade ({unidade || 'unidade'})<input required type="number" min="0.001" step="any" value={quantidade} onChange={(event) => setQuantidade(event.target.value)} /></label>
    </div>
    {pedeMotivo && <label>Motivo<input required value={motivo} onChange={(event) => setMotivo(event.target.value)} placeholder="Ex.: uso na cozinha, perda ou correção" /></label>}
    <label><Rotulo texto="Observação" opcional /><textarea rows={4} value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
    <div className="transfer-summary">
      <div><span>Saldo atual</span><strong>{numero.format(lote.quantidade)} {unidade}</strong></div>
      <div><span>Movimento</span><strong>{qtd > 0 ? `${somaNoLote ? '+' : '−'}${numero.format(qtd)} ${unidade}` : '—'}</strong></div>
      <div><span>Saldo depois</span><strong>{numero.format(Math.max(0, saldoDepois))} {unidade}</strong></div>
    </div>
  </form>
}

function TransferForm({ origem, lotes, produtos, contexto, usuarioId, onSaving, onSaved }: {
  origem: Lote
  lotes: Lote[]
  produtos: Produto[]
  contexto: Contexto
  usuarioId: number
  onSaving: (valor: boolean) => void
  onSaved: (mensagem: string) => Promise<void>
}) {
  const [operacao, setOperacao] = useState<Operacao>('TRANSFERENCIA')
  const [quantidade, setQuantidade] = useState('')
  const [selecionados, setSelecionados] = useState<number[]>([])
  const [produtoDestinoId, setProdutoDestinoId] = useState<number | ''>('')
  const [destinoId, setDestinoId] = useState<number | ''>('')
  const [rendimento, setRendimento] = useState('')
  const [observacao, setObservacao] = useState('')
  const [erro, setErro] = useState('')

  const porItens = temItens(origem)
  const { itens } = useItensDoLote(origem.id, porItens)
  const livres = (itens ?? []).filter((item) => (item.status === 'DISPONIVEL' || item.status === 'EM_USO') && !itemVencido(item)).sort(ordemDeUso)
  const escolhidos = livres.filter((item) => selecionados.includes(item.id))

  const produtoOrigem = contexto.produtosPorId.get(origem.produto_id)
  const unidadeOrigem = produtoOrigem?.unidade_medida ?? ''
  const produtoDestino = operacao === 'TRANSFERENCIA' ? produtoOrigem : produtoDestinoId === '' ? undefined : contexto.produtosPorId.get(produtoDestinoId)
  const unidadeDestino = produtoDestino?.unidade_medida ?? ''
  const lotesDestino = lotes.filter((lote) => {
    if (lote.id === origem.id || !produtoDestino || lote.produto_id !== produtoDestino.id) return false
    if (operacao === 'TRANSFORMACAO') return true
    return porItens ? temItens(lote) || lote.quantidade === 0 : !temItens(lote)
  })
  const loteDestino = lotes.find((lote) => lote.id === destinoId)

  const qtd = porItens ? escolhidos.reduce((total, item) => total + item.saldo, 0) : numeroDe(quantidade)
  const qtdDestino = operacao === 'TRANSFERENCIA' ? qtd : numeroDe(rendimento)
  const qtdValida = qtd > 0 && qtd <= origem.quantidade
  const fator = qtd > 0 && qtdDestino > 0 ? qtdDestino / qtd : null

  const trocarOperacao = (valor: Operacao) => { setOperacao(valor); setDestinoId(''); setProdutoDestinoId(''); setRendimento('') }
  const alternar = (id: number) => setSelecionados((atual) => atual.includes(id) ? atual.filter((valor) => valor !== id) : [...atual, id])
  const usarPrimeiros = (quantos: number) => setSelecionados(livres.slice(0, Math.max(0, quantos)).map((item) => item.id))

  async function salvar(event: FormEvent) {
    event.preventDefault()
    setErro('')
    if (porItens && !escolhidos.length) { setErro('Selecione os itens a usar.'); return }
    if (!qtdValida) { setErro(`Informe uma quantidade entre 0 e ${numero.format(origem.quantidade)} ${unidadeOrigem}.`); return }
    if (!loteDestino) { setErro('Selecione o lote de destino.'); return }
    if (operacao === 'TRANSFORMACAO' && !(qtdDestino > 0)) { setErro('Informe o rendimento da transformação.'); return }
    onSaving(true)
    try {
      await api('/api/estoque/movimentacoes', {
        method: 'POST',
        body: JSON.stringify({
          tipo: operacao,
          lote_id: origem.id,
          lote_destino_id: loteDestino.id,
          usuario_id: usuarioId,
          quantidade: porItens ? null : qtd,
          item_ids: porItens ? escolhidos.map((item) => item.id) : null,
          quantidade_destino: operacao === 'TRANSFORMACAO' ? qtdDestino : null,
          observacao: observacao.trim() || null,
        }),
      })
      await onSaved(operacao === 'TRANSFERENCIA' ? 'Transferência registrada.' : 'Transformação registrada.')
    } catch (reason) { setErro(mensagemErro(reason)) } finally { onSaving(false) }
  }

  const disponiveisDepois = origem.itens_disponiveis - escolhidos.filter((item) => item.status === 'DISPONIVEL').length

  return <form id="transfer-form" className="transfer-form" onSubmit={salvar}>
    {erro && <p className="form-error">{erro}</p>}
    <fieldset className="operation-cards">
      <legend>Operação</legend>
      <label className={operacao === 'TRANSFERENCIA' ? 'active' : ''}>
        <input type="radio" name="operacao" checked={operacao === 'TRANSFERENCIA'} onChange={() => trocarOperacao('TRANSFERENCIA')} />
        <span><strong>Transferência</strong><small>Move o mesmo produto para outro lote ou local.</small></span>
      </label>
      <label className={operacao === 'TRANSFORMACAO' ? 'active' : ''}>
        <input type="radio" name="operacao" checked={operacao === 'TRANSFORMACAO'} onChange={() => trocarOperacao('TRANSFORMACAO')} />
        <span><strong>Transformação</strong><small>Converte itens deste lote em outro produto, com rendimento informado.</small></span>
      </label>
    </fieldset>

    <div className="transfer-grid">
      <section className="transfer-card">
        <div className="transfer-card-head"><h3>Origem · lote #{origem.id}</h3><small>{origem.produto}</small></div>
        {porItens
          ? <>
            <span className="field-label">Itens a usar (selecione as unidades)</span>
            {itens === null && <p className="helper">Carregando itens…</p>}
            <div className="item-picker">
              {livres.map((item) => <label key={item.id} className={selecionados.includes(item.id) ? 'checked' : ''}>
                <input type="checkbox" checked={selecionados.includes(item.id)} onChange={() => alternar(item.id)} />
                <strong>{item.codigo}</strong>
                <small>{numero.format(item.saldo)} {unidadeOrigem}{item.status === 'EM_USO' ? ' · aberta' : ''} · vence {formatarDiaMes(item.data_validade)}</small>
              </label>)}
              {itens !== null && !livres.length && <p className="helper">Nenhum item disponível neste lote.</p>}
            </div>
            <div className="transfer-total">
              <label className="inline-number">
                Usar as que vencem primeiro
                <input type="number" min="0" max={livres.length} value={escolhidos.length} onChange={(event) => usarPrimeiros(Number(event.target.value))} aria-label="Quantidade de itens" />
              </label>
              <strong>{escolhidos.length} un · {numero.format(qtd)} {unidadeOrigem}</strong>
            </div>
          </>
          : <>
            <label>
              Quantidade a usar ({unidadeOrigem})
              <input type="number" min="0" step="any" max={origem.quantidade} required value={quantidade} onChange={(event) => setQuantidade(event.target.value)} placeholder={`até ${numero.format(origem.quantidade)}`} />
            </label>
            <button type="button" className="text-button" onClick={() => setQuantidade(String(origem.quantidade))}>Usar todo o saldo</button>
            <div className="transfer-total"><span>Saldo disponível</span><strong>{numero.format(origem.quantidade)} {unidadeOrigem}</strong></div>
          </>}
      </section>

      <span className="transfer-arrow" aria-hidden="true">→</span>

      <section className="transfer-card">
        <div className="transfer-card-head"><h3>Destino</h3></div>
        {operacao === 'TRANSFORMACAO' && <label>
          Produto resultante
          <SearchSelect<number | ''>
            required
            ariaLabel="Produto resultante"
            placeholder="Buscar produto"
            value={produtoDestinoId}
            onChange={(valor) => { setProdutoDestinoId(valor); setDestinoId('') }}
            options={[{ value: '', label: 'Selecione' }, ...produtos.filter((item) => item.id !== origem.produto_id).map((item) => ({ value: item.id, label: `${item.nome} (${tipoLabels[item.tipo].toLowerCase()})` }))]}
          />
        </label>}
        <label>
          Lote de destino
          <SearchSelect<number | ''>
            required
            disabled={!produtoDestino}
            ariaLabel="Lote de destino"
            placeholder={produtoDestino ? 'Buscar lote' : 'Escolha o produto resultante'}
            value={destinoId}
            onChange={setDestinoId}
            options={[{ value: '', label: lotesDestino.length ? 'Selecione um lote existente' : 'Nenhum lote compatível' }, ...lotesDestino.map((lote) => ({
              value: lote.id,
              label: `#${lote.id} — ${caminhoLocalizacao(lote.localizacao_id, contexto.locaisPorId, lote.localizacao)} · ${numero.format(lote.quantidade)} ${unidadeDestino}`,
            }))]}
          />
        </label>
        {operacao === 'TRANSFORMACAO' && <label>
          Rendimento ({unidadeDestino || 'un. do produto'})
          <input type="number" min="0" step="any" required value={rendimento} onChange={(event) => setRendimento(event.target.value)} placeholder="Quantidade obtida" />
        </label>}
        <label><Rotulo texto="Observação" opcional /><input value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
        {produtoDestino && !lotesDestino.length && <p className="helper">Cadastre antes um lote de {produtoDestino.nome} pelo botão “+ Novo lote”.</p>}
      </section>
    </div>

    <div className="transfer-summary">
      <div>
        <span>Lote #{origem.id} depois da operação</span>
        <strong>{porItens
          ? `${origem.itens_disponiveis} → ${disponiveisDepois} unidades disponíveis`
          : `${numero.format(origem.quantidade)} → ${numero.format(qtdValida ? origem.quantidade - qtd : origem.quantidade)} ${unidadeOrigem}`}</strong>
      </div>
      <div><span>Destino recebe</span><strong>{qtdDestino > 0 && produtoDestino ? `+${numero.format(qtdDestino)} ${unidadeDestino} de ${produtoDestino.nome}` : '—'}</strong></div>
      <div><span>{operacao === 'TRANSFORMACAO' ? 'Rendimento' : 'Destino'}</span><strong>{operacao === 'TRANSFORMACAO'
        ? (fator ? `${numero.format(fator)} ${unidadeDestino} por ${unidadeOrigem}` : '—')
        : (loteDestino ? `Lote #${loteDestino.id} · ${caminhoLocalizacao(loteDestino.localizacao_id, contexto.locaisPorId, loteDestino.localizacao)}` : '—')}</strong></div>
    </div>
  </form>
}

function LotHistory({ lote }: { lote: Lote }) {
  const [movimentos, setMovimentos] = useState<Movimento[] | null>(null)
  const [erro, setErro] = useState('')

  useEffect(() => {
    let vigente = true
    apiListAll<Movimento>(`/api/estoque/movimentacoes?lote_id=${lote.id}`)
      .then((dados) => { if (vigente) setMovimentos([...dados].sort((a, b) => b.criado_em.localeCompare(a.criado_em) || b.id - a.id)) })
      .catch((reason) => { if (vigente) setErro(mensagemErro(reason)) })
    return () => { vigente = false }
  }, [lote.id, lote.quantidade])

  if (erro) return <p className="form-error">{erro}</p>
  if (!movimentos) return <p className="helper">Carregando histórico…</p>
  if (!movimentos.length) return <EmptyState title="Sem movimentações" text="Nenhuma movimentação registrada para este lote." />
  return <ol className="timeline">
    {movimentos.map((item) => <li key={item.id}>
      <div>
        <strong>{movimentoLabels[item.tipo] ?? item.tipo}</strong>
        <span>{numero.format(item.quantidade)}{item.quantidade_destino ? ` → ${numero.format(item.quantidade_destino)}` : ''}{item.lote_destino_id ? ` · para o lote #${item.lote_destino_id}` : ''}</span>
      </div>
      <small>{formatarDataHora(item.criado_em)} · usuário #{item.usuario_id}{[item.motivo, item.observacao].filter(Boolean).length ? ` · ${[item.motivo, item.observacao].filter(Boolean).join(' · ')}` : ''}</small>
    </li>)}
  </ol>
}
