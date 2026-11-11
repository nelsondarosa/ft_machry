import { useState, type FormEvent } from 'react'
import { api } from './api'
import { Modal, SearchSelect } from './components'
import type { Conservacao, FaseCatalogo, FichaTecnica, Produto, TipoProduto } from './types'

const unidadesMedida = [
  { valor: 'kg', nome: 'Quilograma (kg)' },
  { valor: 'g', nome: 'Grama (g)' },
  { valor: 'mg', nome: 'Miligrama (mg)' },
  { valor: 'L', nome: 'Litro (L)' },
  { valor: 'ml', nome: 'Mililitro (ml)' },
  { valor: 'un', nome: 'Unidade (un)' },
  { valor: 'pct', nome: 'Pacote (pct)' },
  { valor: 'cx', nome: 'Caixa (cx)' },
  { valor: 'dz', nome: 'Dúzia (dz)' },
  { valor: 'pç', nome: 'Peça (pç)' },
] as const

export function ProductModal({ produto, onClose, onSaved, onDeleted }: { produto: Produto | null; onClose: () => void; onSaved: () => void; onDeleted: () => void }) {
  const [nome, setNome] = useState(produto?.nome ?? '')
  const [tipo, setTipo] = useState<TipoProduto>(produto?.tipo ?? 'INSUMO')
  const [unidade, setUnidade] = useState(produto?.unidade_medida ?? 'kg')
  const [subdivisao, setSubdivisao] = useState(produto?.subdivisao ?? '')
  const [conservacao, setConservacao] = useState<Conservacao>(produto?.conservacao ?? 'SECO')
  const [validadeObrigatoria, setValidadeObrigatoria] = useState(Boolean(produto?.validade_obrigatoria))
  const [validadeDias, setValidadeDias] = useState(produto?.validade_padrao_dias?.toString() ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      await api(produto ? `/api/produtos/${produto.id}` : '/api/produtos', { method: produto ? 'PUT' : 'POST', body: JSON.stringify({ nome: nome.trim(), tipo, unidade_medida: unidade, subdivisao: subdivisao.trim() || null, conservacao, validade_obrigatoria: validadeObrigatoria ? 1 : 0, validade_padrao_dias: validadeDias === '' ? null : Number(validadeDias) }) })
      onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar o produto.') } finally { setSaving(false) }
  }
  async function remove() {
    if (!produto || !window.confirm(`Excluir o produto “${produto.nome}”?`)) return
    setSaving(true); setError('')
    try { await api(`/api/produtos/${produto.id}`, { method: 'DELETE' }); onDeleted() } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível excluir o produto.'); setSaving(false) }
  }
  return <Modal eyebrow="CATÁLOGO" title={produto ? 'Editar produto' : 'Novo produto'} onClose={onClose} footer={<>{produto && <button className="danger-link" onClick={remove} disabled={saving}>Excluir produto</button>}<button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" form="product-form" disabled={saving}>{saving ? 'Salvando…' : 'Salvar produto'}</button></>}>
    <form className="dialog-body" id="product-form" onSubmit={save}>{error && <p className="form-error">{error}</p>}<label>Nome<input required maxLength={150} value={nome} onChange={(event) => setNome(event.target.value)} /></label><div className="form-grid"><label>Tipo<SearchSelect ariaLabel="Tipo" value={tipo} onChange={setTipo} options={[{ value: 'INSUMO', label: 'Insumo' }, { value: 'INTERMEDIARIO', label: 'Intermediário' }, { value: 'FINAL', label: 'Produto final' }]} /></label><label>Unidade de medida<SearchSelect required ariaLabel="Unidade de medida" value={unidade} onChange={setUnidade} options={[...(!unidadesMedida.some((item) => item.valor === unidade) && unidade ? [{ value: unidade, label: `${unidade} (cadastrada anteriormente)` }] : []), ...unidadesMedida.map((item) => ({ value: item.valor, label: item.nome }))]} /></label><label>Conservação<SearchSelect ariaLabel="Conservação" value={conservacao} onChange={setConservacao} options={[{ value: 'SECO', label: 'Seco' }, { value: 'RESFRIADO', label: 'Resfriado' }, { value: 'CONGELADO', label: 'Congelado' }]} /></label><label>Validade padrão (dias)<input type="number" min="0" value={validadeDias} onChange={(event) => setValidadeDias(event.target.value)} placeholder="Opcional" /></label></div><label>Subdivisão (opcional)<input maxLength={100} value={subdivisao} onChange={(event) => setSubdivisao(event.target.value)} placeholder="Ex.: sal fino, sal grosso, sal parrillero" /><small>Especifique a variação do produto para facilitar a busca e a organização.</small></label><label className="checkbox"><input type="checkbox" checked={validadeObrigatoria} onChange={(event) => setValidadeObrigatoria(event.target.checked)} /> Exigir data de validade nos lotes</label></form>
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
  const componentOptions = produtos.map((produto) => ({ value: produto.id, label: `${produto.nome} (${produto.unidade_medida})` }))
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
  const addPhase = () => setFases((rows) => [...rows, { key: key(), fase_id: catalogoFases[0]?.id ?? 0, ordem: rows.length + 1, tempo_previsto_min: 10 }])
  const addComponent = () => setComponentes((rows) => [...rows, { key: key(), produto_id: produtos[0]?.id ?? 0, quantidade: 1, fase_ordem: fases[0]?.ordem ?? null }])
  const etapaOptions = [{ value: '' as const, label: 'Sem vínculo' }, ...fases.map((fase) => ({ value: fase.ordem, label: `Etapa ${fase.ordem}` }))]

  const footer = <>
    {ficha && <button className="danger-link" onClick={remove} disabled={saving}>Excluir ficha</button>}
    <button className="secondary" onClick={onClose} type="button">Cancelar</button>
    <button className="primary" form="sheet-form" disabled={saving}>{saving ? 'Salvando…' : 'Salvar ficha'}</button>
  </>

  return <Modal eyebrow="PADRONIZAÇÃO" title={ficha ? 'Editar ficha técnica' : 'Nova ficha técnica'} wide onClose={onClose} footer={footer}>
    <form className="dialog-body" id="sheet-form" onSubmit={save}>
      {error && <p className="form-error">{error}</p>}
      {!productsForSheet.length && <p className="form-error">Cadastre um produto intermediário ou final antes de criar uma ficha.</p>}

      <div className="form-grid">
        <label>
          Produto produzido
          <SearchSelect
            required
            ariaLabel="Produto da ficha"
            placeholder="Buscar produto"
            value={produtoId}
            onChange={setProdutoId}
            options={productsForSheet.map((produto) => ({ value: produto.id, label: produto.nome }))}
          />
        </label>
        <label>
          Rendimento
          <input required type="number" min="0.001" step="0.001" value={rendimento} onChange={(event) => setRendimento(Number(event.target.value))} />
        </label>
      </div>

      <label>
        Observações
        <textarea rows={3} maxLength={2000} value={observacao} onChange={(event) => setObservacao(event.target.value)} />
      </label>

      <section className="subsection">
        <div>
          <h3>Etapas de preparo</h3>
          <button className="text-button" type="button" onClick={addPhase}>+ Adicionar etapa</button>
        </div>
        {fases.map((fase) => (
          <div className="form-row" key={fase.key}>
            <label>
              Ordem
              <input required type="number" min="1" value={fase.ordem} onChange={(event) => updatePhase(fase.key, { ordem: Number(event.target.value) })} />
            </label>
            <label>
              Fase
              <SearchSelect
                required
                ariaLabel="Fase"
                value={fase.fase_id}
                onChange={(faseId) => updatePhase(fase.key, { fase_id: faseId })}
                options={catalogoFases.map((item) => ({ value: item.id, label: item.nome }))}
              />
            </label>
            <label>
              Tempo (min)
              <input required type="number" min="1" value={fase.tempo_previsto_min} onChange={(event) => updatePhase(fase.key, { tempo_previsto_min: Number(event.target.value) })} />
            </label>
            <button className="remove-row" type="button" aria-label="Remover etapa" disabled={fases.length === 1} onClick={() => setFases((rows) => rows.filter((row) => row.key !== fase.key))}>×</button>
          </div>
        ))}
      </section>

      <section className="subsection">
        <div>
          <h3>Componentes</h3>
          <button className="text-button" type="button" onClick={addComponent}>+ Adicionar componente</button>
        </div>
        {componentes.map((item) => (
          <div className="form-row component-row" key={item.key}>
            <label>
              Produto
              <SearchSelect
                required
                ariaLabel="Componente"
                placeholder="Buscar produto"
                value={item.produto_id}
                onChange={(produtoId) => updateComponent(item.key, { produto_id: produtoId })}
                options={componentOptions}
              />
            </label>
            <label>
              Quantidade
              <input required type="number" min="0.001" step="0.001" value={item.quantidade} onChange={(event) => updateComponent(item.key, { quantidade: Number(event.target.value) })} />
            </label>
            <label>
              Etapa
              <SearchSelect<number | ''>
                ariaLabel="Etapa"
                value={item.fase_ordem ?? ''}
                onChange={(ordem) => updateComponent(item.key, { fase_ordem: ordem === '' ? null : ordem })}
                options={etapaOptions}
              />
            </label>
            <button className="remove-row" type="button" aria-label="Remover componente" disabled={componentes.length === 1} onClick={() => setComponentes((rows) => rows.filter((row) => row.key !== item.key))}>×</button>
          </div>
        ))}
      </section>
    </form>
  </Modal>
}
