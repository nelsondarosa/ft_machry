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

const csvColunas = ['nome', 'tipo', 'unidade_medida', 'subdivisao', 'conservacao', 'validade_obrigatoria', 'validade_padrao_dias'] as const
const csvModelo = 'nome;tipo;unidade_medida;subdivisao;conservacao;validade_obrigatoria;validade_padrao_dias\nFarinha de trigo;INSUMO;kg;tipo 1;SECO;0;180\nMolho de tomate;INTERMEDIARIO;L;;RESFRIADO;1;5\nLasanha;FINAL;un;;CONGELADO;1;30\n'
const normalizar = (valor: string) => valor.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toUpperCase()
const tiposCsv: Record<string, TipoProduto> = { INSUMO: 'INSUMO', INSUMOS: 'INSUMO', INTERMEDIARIO: 'INTERMEDIARIO', INTERMEDIARIOS: 'INTERMEDIARIO', FINAL: 'FINAL', 'PRODUTO FINAL': 'FINAL', 'PRODUTOS FINAIS': 'FINAL' }
const conservacoesCsv: Record<string, Conservacao> = { SECO: 'SECO', RESFRIADO: 'RESFRIADO', CONGELADO: 'CONGELADO' }
const simCsv = new Set(['1', 'SIM', 'S', 'TRUE', 'X'])
const naoCsv = new Set(['', '0', 'NAO', 'N', 'FALSE'])

type LinhaCsv = { linha: number; dados: Record<string, unknown>; erros: string[] }

/** Parser CSV com suporte a aspas; detecta `;` (Excel pt-BR) ou `,` pelo cabeçalho. */
function lerCsv(texto: string): string[][] {
  texto = texto.replace(/^﻿/, '')
  const primeira = texto.split(/\r?\n/, 1)[0] ?? ''
  const sep = (primeira.match(/;/g)?.length ?? 0) >= (primeira.match(/,/g)?.length ?? 0) ? ';' : ','
  const linhas: string[][] = []
  let linha: string[] = [], campo = '', aspas = false
  for (let i = 0; i < texto.length; i += 1) {
    const c = texto[i]
    if (aspas) {
      if (c === '"' && texto[i + 1] === '"') { campo += '"'; i += 1 }
      else if (c === '"') aspas = false
      else campo += c
    } else if (c === '"') aspas = true
    else if (c === sep) { linha.push(campo); campo = '' }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && texto[i + 1] === '\n') i += 1
      linha.push(campo); linhas.push(linha); linha = []; campo = ''
    } else campo += c
  }
  if (campo || linha.length) { linha.push(campo); linhas.push(linha) }
  return linhas
}

function converterCsv(texto: string): { linhas: LinhaCsv[]; erro?: string } {
  const [cabecalho, ...corpo] = lerCsv(texto)
  if (!cabecalho) return { linhas: [], erro: 'Arquivo vazio.' }
  const indices = cabecalho.map((coluna) => coluna.trim().toLowerCase())
  const faltando = ['nome', 'tipo', 'unidade_medida'].filter((coluna) => !indices.includes(coluna))
  if (faltando.length) return { linhas: [], erro: `Colunas obrigatórias ausentes: ${faltando.join(', ')}.` }
  const desconhecidas = indices.filter((coluna) => coluna && !(csvColunas as readonly string[]).includes(coluna))
  if (desconhecidas.length) return { linhas: [], erro: `Colunas desconhecidas: ${desconhecidas.join(', ')}.` }
  const linhas = corpo.map((valores, posicao) => ({ valores, linha: posicao + 2 }))
    .filter(({ valores }) => valores.some((valor) => valor.trim()))
    .map(({ valores, linha }) => {
      const valor = (coluna: string) => (valores[indices.indexOf(coluna)] ?? '').trim()
      const erros: string[] = []
      const nome = valor('nome'), unidade = valor('unidade_medida'), subdivisao = valor('subdivisao')
      if (!nome) erros.push('nome vazio'); else if (nome.length > 150) erros.push('nome com mais de 150 caracteres')
      if (!unidade) erros.push('unidade vazia'); else if (unidade.length > 20) erros.push('unidade com mais de 20 caracteres')
      if (subdivisao.length > 100) erros.push('subdivisão com mais de 100 caracteres')
      const tipo = tiposCsv[normalizar(valor('tipo'))]
      if (!tipo) erros.push(`tipo inválido “${valor('tipo')}”`)
      const conservacao = valor('conservacao') ? conservacoesCsv[normalizar(valor('conservacao'))] : 'SECO'
      if (!conservacao) erros.push(`conservação inválida “${valor('conservacao')}”`)
      const obrigatoria = normalizar(valor('validade_obrigatoria'))
      if (!simCsv.has(obrigatoria) && !naoCsv.has(obrigatoria)) erros.push(`validade obrigatória inválida “${valor('validade_obrigatoria')}”`)
      const dias = valor('validade_padrao_dias')
      if (dias && !/^\d+$/.test(dias)) erros.push(`validade padrão inválida “${dias}”`)
      return { linha, erros, dados: { nome, tipo, unidade_medida: unidade, subdivisao: subdivisao || null, conservacao, validade_obrigatoria: simCsv.has(obrigatoria) ? 1 : 0, validade_padrao_dias: /^\d+$/.test(dias) ? Number(dias) : null } }
    })
  if (!linhas.length) return { linhas, erro: 'Nenhum produto encontrado no arquivo.' }
  if (linhas.length > 500) return { linhas: [], erro: 'Limite de 500 produtos por importação.' }
  return { linhas }
}

export function ProductImportModal({ onClose, onSaved }: { onClose: () => void; onSaved: (total: number) => void }) {
  const [arquivo, setArquivo] = useState('')
  const [linhas, setLinhas] = useState<LinhaCsv[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const comErro = linhas.filter((item) => item.erros.length)

  async function selecionar(file: File | undefined) {
    setError(''); setLinhas([]); setArquivo(file?.name ?? '')
    if (!file) return
    const resultado = converterCsv(await file.text())
    setLinhas(resultado.linhas); if (resultado.erro) setError(resultado.erro)
  }
  function baixarModelo() {
    const url = URL.createObjectURL(new Blob(['﻿' + csvModelo], { type: 'text/csv;charset=utf-8' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: 'modelo-produtos.csv' })
    link.click(); URL.revokeObjectURL(url)
  }
  async function importar() {
    setSaving(true); setError('')
    try {
      await api('/api/produtos/lote', { method: 'POST', body: JSON.stringify({ produtos: linhas.map((item) => item.dados) }) })
      onSaved(linhas.length)
    } catch (reason) {
      const mensagem = reason instanceof Error ? reason.message : 'Não foi possível importar os produtos.'
      setError(mensagem.replace(/^produto (\d+):/, (_, n: string) => `Linha ${linhas[Number(n) - 1]?.linha ?? n}:`))
    } finally { setSaving(false) }
  }
  return <Modal eyebrow="CATÁLOGO" title="Importar produtos (CSV)" wide onClose={onClose} footer={<><button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" type="button" onClick={() => void importar()} disabled={saving || !linhas.length || comErro.length > 0}>{saving ? 'Importando…' : `Importar ${linhas.length || ''} produto(s)`}</button></>}>
    <div className="dialog-body">
      {error && <p className="form-error">{error}</p>}
      <p>Colunas: <code>{csvColunas.join(';')}</code>. Obrigatórias: nome, tipo (INSUMO, INTERMEDIARIO ou FINAL) e unidade_medida. Conservação padrão: SECO. A importação é feita por completo ou não é feita.</p>
      <button className="text-button" type="button" onClick={baixarModelo}>Baixar modelo CSV →</button>
      <label>Arquivo CSV<input type="file" accept=".csv,text/csv" onChange={(event) => void selecionar(event.target.files?.[0])} /></label>
      {arquivo && linhas.length > 0 && <>
        <p>{linhas.length} produto(s) em {arquivo}{comErro.length ? ` · ${comErro.length} linha(s) com erro` : ''}.</p>
        <div className="table-wrap"><table><thead><tr><th>Linha</th><th>Nome</th><th>Tipo</th><th>Unidade</th><th>Subdivisão</th><th>Conservação</th><th>Validade</th><th>Status</th></tr></thead>
          <tbody>{linhas.map(({ linha, dados, erros }) => <tr key={linha}>
            <td>{linha}</td><td><strong>{String(dados.nome || '—')}</strong></td><td>{String(dados.tipo ?? '—')}</td><td>{String(dados.unidade_medida || '—')}</td><td>{String(dados.subdivisao ?? '—')}</td><td>{String(dados.conservacao ?? '—')}</td>
            <td>{dados.validade_padrao_dias == null ? '—' : `${dados.validade_padrao_dias} dias`}{dados.validade_obrigatoria ? ' (obrigatória)' : ''}</td>
            <td>{erros.length ? <span className="form-error">{erros.join('; ')}</span> : 'OK'}</td>
          </tr>)}</tbody></table></div>
      </>}
    </div>
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
