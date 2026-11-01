import { useState, type FormEvent } from 'react'
import { api } from './api'
import { Modal } from './components'
import type { Conservacao, FaseCatalogo, FichaTecnica, Localizacao, Lote, Produto, TipoProduto } from './types'

export function ProductModal({ produto, onClose, onSaved, onDeleted }: { produto: Produto | null; onClose: () => void; onSaved: () => void; onDeleted: () => void }) {
  const [nome, setNome] = useState(produto?.nome ?? '')
  const [tipo, setTipo] = useState<TipoProduto>(produto?.tipo ?? 'INSUMO')
  const [unidade, setUnidade] = useState(produto?.unidade_medida ?? 'kg')
  const [conservacao, setConservacao] = useState<Conservacao>(produto?.conservacao ?? 'SECO')
  const [validadeObrigatoria, setValidadeObrigatoria] = useState(Boolean(produto?.validade_obrigatoria))
  const [validadeDias, setValidadeDias] = useState(produto?.validade_padrao_dias?.toString() ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await api(produto ? `/api/produtos/${produto.id}` : '/api/produtos', { method: produto ? 'PUT' : 'POST', body: JSON.stringify({ nome, tipo, unidade_medida: unidade, conservacao, validade_obrigatoria: validadeObrigatoria ? 1 : 0, validade_padrao_dias: validadeDias === '' ? null : Number(validadeDias) }) })
      onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar o produto.') } finally { setSaving(false) }
  }
  async function remove() {
    if (!produto || !window.confirm(`Excluir o produto “${produto.nome}”?`)) return
    setSaving(true); setError('')
    try { await api(`/api/produtos/${produto.id}`, { method: 'DELETE' }); onDeleted() } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível excluir o produto.'); setSaving(false) }
  }
  return <Modal eyebrow="CATÁLOGO" title={produto ? 'Editar produto' : 'Novo produto'} onClose={onClose} footer={<>{produto && <button className="danger-link" onClick={remove} disabled={saving}>Excluir produto</button>}<button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" form="product-form" disabled={saving}>{saving ? 'Salvando…' : 'Salvar produto'}</button></>}>
    <form className="dialog-body" id="product-form" onSubmit={save}>{error && <p className="form-error">{error}</p>}<label>Nome<input required maxLength={150} value={nome} onChange={(event) => setNome(event.target.value)} /></label><div className="form-grid"><label>Tipo<select value={tipo} onChange={(event) => setTipo(event.target.value as TipoProduto)}><option value="INSUMO">Insumo</option><option value="INTERMEDIARIO">Intermediário</option><option value="FINAL">Produto final</option></select></label><label>Unidade de medida<input required maxLength={20} value={unidade} onChange={(event) => setUnidade(event.target.value)} /></label><label>Conservação<select value={conservacao} onChange={(event) => setConservacao(event.target.value as Conservacao)}><option value="SECO">Seco</option><option value="RESFRIADO">Resfriado</option><option value="CONGELADO">Congelado</option></select></label><label>Validade padrão (dias)<input type="number" min="0" value={validadeDias} onChange={(event) => setValidadeDias(event.target.value)} placeholder="Opcional" /></label></div><label className="checkbox"><input type="checkbox" checked={validadeObrigatoria} onChange={(event) => setValidadeObrigatoria(event.target.checked)} /> Exigir data de validade nos lotes</label></form>
  </Modal>
}

type DraftPhase = { key: string; fase_id: number; ordem: number; tempo_previsto_min: number }
type DraftComponent = { key: string; produto_id: number; quantidade: number; fase_ordem: number | null }
let keySequence = 0
const key = () => {
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()
  keySequence += 1
  return `${Date.now().toString(36)}-${keySequence.toString(36)}-${Math.random().toString(36).slice(2)}`
}

export function SheetModal({ ficha, produtos, catalogoFases, onClose, onSaved, onDeleted }: { ficha: FichaTecnica | null; produtos: Produto[]; catalogoFases: FaseCatalogo[]; onClose: () => void; onSaved: () => void; onDeleted: () => void }) {
  const productsForSheet = produtos.filter((produto) => produto.tipo !== 'INSUMO')
  const [produtoId, setProdutoId] = useState(ficha?.produto_id ?? productsForSheet[0]?.id ?? 0)
  const [rendimento, setRendimento] = useState(ficha?.rendimento ?? 1)
  const [observacao, setObservacao] = useState(ficha?.observacao ?? '')
  const [fases, setFases] = useState<DraftPhase[]>(ficha?.fases.map((fase) => ({ key: key(), fase_id: fase.fase_id, ordem: fase.ordem, tempo_previsto_min: fase.tempo_previsto_min })) ?? [{ key: key(), fase_id: catalogoFases[0]?.id ?? 0, ordem: 1, tempo_previsto_min: 10 }])
  const [componentes, setComponentes] = useState<DraftComponent[]>(ficha?.componentes.map((item) => ({ key: key(), produto_id: item.produto_id, quantidade: item.quantidade, fase_ordem: item.fase_ordem })) ?? [{ key: key(), produto_id: produtos[0]?.id ?? 0, quantidade: 1, fase_ordem: 1 }])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const updatePhase = (rowKey: string, change: Partial<DraftPhase>) => setFases((rows) => rows.map((row) => row.key === rowKey ? { ...row, ...change } : row))
  const updateComponent = (rowKey: string, change: Partial<DraftComponent>) => setComponentes((rows) => rows.map((row) => row.key === rowKey ? { ...row, ...change } : row))
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const body = { produto_id: produtoId, rendimento, observacao: observacao.trim() || null, fases: fases.map(({ fase_id, ordem, tempo_previsto_min }) => ({ fase_id, ordem, tempo_previsto_min })), componentes: componentes.map(({ produto_id, quantidade, fase_ordem }) => ({ produto_id, quantidade, fase_ordem })) }
      await api(ficha ? `/api/fichas-tecnicas/${ficha.id}` : '/api/fichas-tecnicas', { method: ficha ? 'PUT' : 'POST', body: JSON.stringify(body) }); onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar a ficha.') } finally { setSaving(false) }
  }
  async function remove() {
    if (!ficha || !window.confirm(`Excluir a ficha de “${ficha.produto}”?`)) return
    setSaving(true); setError('')
    try { await api(`/api/fichas-tecnicas/${ficha.id}`, { method: 'DELETE' }); onDeleted() } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível excluir a ficha.'); setSaving(false) }
  }
  return <Modal eyebrow="PADRONIZAÇÃO" title={ficha ? 'Editar ficha técnica' : 'Nova ficha técnica'} wide onClose={onClose} footer={<>{ficha && <button className="danger-link" onClick={remove} disabled={saving}>Excluir ficha</button>}<button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" form="sheet-form" disabled={saving}>{saving ? 'Salvando…' : 'Salvar ficha'}</button></>}>
    <form className="dialog-body" id="sheet-form" onSubmit={save}>{error && <p className="form-error">{error}</p>}{!productsForSheet.length && <p className="form-error">Cadastre um produto intermediário ou final antes de criar uma ficha.</p>}<div className="form-grid"><label>Produto produzido<select required value={produtoId} onChange={(event) => setProdutoId(Number(event.target.value))}>{productsForSheet.map((produto) => <option key={produto.id} value={produto.id}>{produto.nome}</option>)}</select></label><label>Rendimento<input required type="number" min="0.001" step="0.001" value={rendimento} onChange={(event) => setRendimento(Number(event.target.value))} /></label></div><label>Observações<textarea rows={3} maxLength={2000} value={observacao} onChange={(event) => setObservacao(event.target.value)} /></label>
      <section className="subsection"><div><h3>Etapas de preparo</h3><button className="text-button" type="button" onClick={() => setFases((rows) => [...rows, { key: key(), fase_id: catalogoFases[0]?.id ?? 0, ordem: rows.length + 1, tempo_previsto_min: 10 }])}>+ Adicionar etapa</button></div>{fases.map((fase) => <div className="form-row" key={fase.key}><label>Ordem<input required type="number" min="1" value={fase.ordem} onChange={(event) => updatePhase(fase.key, { ordem: Number(event.target.value) })} /></label><label>Fase<select required value={fase.fase_id} onChange={(event) => updatePhase(fase.key, { fase_id: Number(event.target.value) })}>{catalogoFases.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label><label>Tempo (min)<input required type="number" min="1" value={fase.tempo_previsto_min} onChange={(event) => updatePhase(fase.key, { tempo_previsto_min: Number(event.target.value) })} /></label><button className="remove-row" type="button" aria-label="Remover etapa" disabled={fases.length === 1} onClick={() => setFases((rows) => rows.filter((row) => row.key !== fase.key))}>×</button></div>)}</section>
      <section className="subsection"><div><h3>Componentes</h3><button className="text-button" type="button" onClick={() => setComponentes((rows) => [...rows, { key: key(), produto_id: produtos[0]?.id ?? 0, quantidade: 1, fase_ordem: fases[0]?.ordem ?? null }])}>+ Adicionar componente</button></div>{componentes.map((item) => <div className="form-row component-row" key={item.key}><label>Produto<select required value={item.produto_id} onChange={(event) => updateComponent(item.key, { produto_id: Number(event.target.value) })}>{produtos.map((produto) => <option key={produto.id} value={produto.id}>{produto.nome} ({produto.unidade_medida})</option>)}</select></label><label>Quantidade<input required type="number" min="0.001" step="0.001" value={item.quantidade} onChange={(event) => updateComponent(item.key, { quantidade: Number(event.target.value) })} /></label><label>Etapa<select value={item.fase_ordem ?? ''} onChange={(event) => updateComponent(item.key, { fase_ordem: event.target.value ? Number(event.target.value) : null })}><option value="">Sem vínculo</option>{fases.map((fase) => <option key={fase.key} value={fase.ordem}>Etapa {fase.ordem}</option>)}</select></label><button className="remove-row" type="button" aria-label="Remover componente" disabled={componentes.length === 1} onClick={() => setComponentes((rows) => rows.filter((row) => row.key !== item.key))}>×</button></div>)}</section>
    </form>
  </Modal>
}

export function StockModal({ lote, produtos, localizacoes, usuarioId, onClose, onSaved }: { lote: Lote | null; produtos: Produto[]; localizacoes: Localizacao[]; usuarioId: number; onClose: () => void; onSaved: () => void }) {
  const [produtoId, setProdutoId] = useState(lote?.produto_id ?? produtos[0]?.id ?? 0)
  const produto = produtos.find((item) => item.id === produtoId)
  const locaisCompativeis = localizacoes.filter((item) => !produto || item.tipo === produto.conservacao)
  const [localizacaoId, setLocalizacaoId] = useState(lote?.localizacao_id ?? locaisCompativeis[0]?.id ?? 0)
  const [tipo, setTipo] = useState<'ENTRADA' | 'SAIDA' | 'AJUSTE_ENTRADA' | 'AJUSTE_SAIDA'>('ENTRADA')
  const [quantidade, setQuantidade] = useState(1)
  const [dataProducao, setDataProducao] = useState(lote?.data_producao ?? '')
  const [dataValidade, setDataValidade] = useState(lote?.data_validade ?? '')
  const [custo, setCusto] = useState(lote?.custo_unitario?.toString() ?? '')
  const [motivo, setMotivo] = useState('')
  const [observacao, setObservacao] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function changeProduct(id: number) {
    setProdutoId(id)
    const selected = produtos.find((item) => item.id === id)
    const location = localizacoes.find((item) => item.tipo === selected?.conservacao)
    setLocalizacaoId(location?.id ?? 0)
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      let loteId = lote?.id
      if (!loteId) {
        const created = await api<{ id: number }>('/api/estoque/lotes', { method: 'POST', body: JSON.stringify({ produto_id: produtoId, localizacao_id: localizacaoId, data_producao: dataProducao || null, data_validade: dataValidade || null, custo_unitario: custo === '' ? null : Number(custo) }) })
        loteId = created.id
      }
      await api('/api/estoque/movimentacoes', { method: 'POST', body: JSON.stringify({ tipo: lote ? tipo : 'ENTRADA', lote_id: loteId, usuario_id: usuarioId, quantidade, motivo: lote ? (motivo.trim() || null) : null, observacao: observacao.trim() || null }) })
      onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível movimentar o estoque.') } finally { setSaving(false) }
  }
  const needsReason = Boolean(lote && tipo !== 'ENTRADA')
  return <Modal eyebrow="ESTOQUE GERAL" title={lote ? `Movimentar lote #${lote.id}` : 'Nova entrada de estoque'} onClose={onClose} footer={<><button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" form="stock-form" disabled={saving || !localizacaoId}>{saving ? 'Salvando…' : lote ? 'Registrar movimento' : 'Criar lote e dar entrada'}</button></>}>
    <form className="dialog-body" id="stock-form" onSubmit={save}>{error && <p className="form-error">{error}</p>}{lote ? <div className="stock-lot-summary"><span className={`badge ${produto?.tipo.toLowerCase()}`}>{produto?.tipo === 'FINAL' ? 'Produto final' : produto?.tipo === 'INTERMEDIARIO' ? 'Intermediário' : 'Insumo'}</span><strong>{lote.produto}</strong><small>{lote.quantidade} {produto?.unidade_medida} em {lote.localizacao}</small></div> : <><label>Produto<select required value={produtoId} onChange={(event) => changeProduct(Number(event.target.value))}>{produtos.map((item) => <option key={item.id} value={item.id}>{item.nome} · {item.tipo === 'FINAL' ? 'Produto final' : item.tipo === 'INTERMEDIARIO' ? 'Intermediário' : 'Insumo'}</option>)}</select></label><label>Localização<select required value={localizacaoId} onChange={(event) => setLocalizacaoId(Number(event.target.value))}>{locaisCompativeis.map((item) => <option key={item.id} value={item.id}>{item.nome}</option>)}</select></label><div className="form-grid"><label>Data de produção<input type="date" value={dataProducao} onChange={(event) => setDataProducao(event.target.value)} /></label><label>Data de validade<input type="date" required={Boolean(produto?.validade_obrigatoria)} value={dataValidade} onChange={(event) => setDataValidade(event.target.value)} /></label><label>Custo unitário<input type="number" min="0" step="0.01" value={custo} onChange={(event) => setCusto(event.target.value)} placeholder="Opcional" /></label></div></>}{lote && <label>Movimento<select value={tipo} onChange={(event) => setTipo(event.target.value as typeof tipo)}><option value="ENTRADA">Entrada</option><option value="SAIDA">Saída</option><option value="AJUSTE_ENTRADA">Ajuste de entrada</option><option value="AJUSTE_SAIDA">Ajuste de saída</option></select></label>}<label>Quantidade ({produto?.unidade_medida || 'unidade'})<input required type="number" min="0.001" step="0.001" value={quantidade} onChange={(event) => setQuantidade(Number(event.target.value))} /></label>{needsReason && <label>Motivo<input required value={motivo} onChange={(event) => setMotivo(event.target.value)} placeholder="Ex.: uso na cozinha, perda ou correção" /></label>}<label>Observação<textarea rows={2} value={observacao} onChange={(event) => setObservacao(event.target.value)} placeholder="Opcional" /></label></form>
  </Modal>
}
