import { useState, type FormEvent } from 'react'
import { api } from './api'
import { Modal, SearchSelect } from './components'
import { BrandMark, useBranding } from './branding'
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
const unidadesPermitidas = new Set<string>(unidadesMedida.map((item) => item.valor))

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
      if (!unidade) erros.push('unidade vazia'); else if (!unidadesPermitidas.has(unidade)) erros.push(`unidade inválida “${unidade}”`)
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

export function ProductImportModal({ onClose, onSaved }: { onClose: () => void; onSaved: (total: number, ignorados: string[]) => void }) {
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
      const resposta = await api<{ total: number; ignorados: string[] }>('/api/produtos/lote', { method: 'POST', body: JSON.stringify({ produtos: linhas.map((item) => item.dados) }) })
      onSaved(resposta.total, resposta.ignorados)
    } catch (reason) {
      const mensagem = reason instanceof Error ? reason.message : 'Não foi possível importar os produtos.'
      setError(mensagem.replace(/^produto (\d+):/, (_, n: string) => `Linha ${linhas[Number(n) - 1]?.linha ?? n}:`))
    } finally { setSaving(false) }
  }
  return <Modal eyebrow="CATÁLOGO" title="Importar produtos (CSV)" wide onClose={onClose} footer={<><button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" type="button" onClick={() => void importar()} disabled={saving || !linhas.length || comErro.length > 0}>{saving ? 'Importando…' : `Importar ${linhas.length || ''} produto(s)`}</button></>}>
    <div className="dialog-body">
      {error && <p className="form-error">{error}</p>}
      <p>Colunas: <code>{csvColunas.join(';')}</code>. Obrigatórias: nome, tipo (INSUMO, INTERMEDIARIO ou FINAL) e unidade_medida. Conservação padrão: SECO. Produtos com o mesmo nome e conservação de um já cadastrado são ignorados. A importação é feita por completo ou não é feita.</p>
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

const fichaColunas = ['ficha', 'rendimento', 'observacao', 'fase_ordem', 'fase', 'tempo_min', 'componente', 'quantidade', 'unidade'] as const
const fichaModelo = 'ficha;rendimento;observacao;fase_ordem;fase;tempo_min;componente;quantidade;unidade\nPurê de batata;0,35;Cozinhe as batatas inteiras com sal.;1;Cozir;25;Batata asterix;300;g\nPurê de batata;;Aqueça a manteiga, a nata e o leite e junte as batatas.;2;Bater/Misturar;15;Nata;60;ml\nPurê de batata;;;2;;;Manteiga sem sal;15;g\nPurê de batata;;;;;;Sal fino;q.b.;\n'
const aGosto = new Set(['', 'QB', 'Q.B', 'Q.B.', 'A GOSTO'])
const numeroCsv = (valor: string) => /^\d+([.,]\d+)?$/.test(valor) ? Number(valor.replace(',', '.')) : NaN

type FaseCsv = { fase: string; ordem: number; tempo_previsto_min: number }
type ComponenteCsv = { produto: string; quantidade: string | null; unidade: string | null; fase_ordem: number | null }
type FichaCsv = { nome: string; linhas: number[]; rendimento: string; observacoes: string[]; fases: Map<number, FaseCsv>; componentes: ComponenteCsv[]; erros: string[] }

function converterFichasCsv(texto: string): { fichas: FichaCsv[]; erro?: string } {
  const [cabecalho, ...corpo] = lerCsv(texto)
  if (!cabecalho) return { fichas: [], erro: 'Arquivo vazio.' }
  const indices = cabecalho.map((coluna) => coluna.trim().toLowerCase())
  const faltando = ['ficha', 'rendimento', 'fase_ordem', 'fase', 'tempo_min', 'componente', 'quantidade'].filter((coluna) => !indices.includes(coluna))
  if (faltando.length) return { fichas: [], erro: `Colunas obrigatórias ausentes: ${faltando.join(', ')}.` }
  const desconhecidas = indices.filter((coluna) => coluna && !(fichaColunas as readonly string[]).includes(coluna))
  if (desconhecidas.length) return { fichas: [], erro: `Colunas desconhecidas: ${desconhecidas.join(', ')}.` }

  const porNome = new Map<string, FichaCsv>()
  corpo.forEach((valores, posicao) => {
    if (!valores.some((valor) => valor.trim())) return
    const linha = posicao + 2
    const valor = (coluna: string) => (valores[indices.indexOf(coluna)] ?? '').trim()
    const nome = valor('ficha')
    if (!nome) { porNome.set(`#${linha}`, { nome: `(linha ${linha})`, linhas: [linha], rendimento: '', observacoes: [], fases: new Map(), componentes: [], erros: ['nome da ficha vazio'] }); return }
    const chave = normalizar(nome)
    const ficha = porNome.get(chave) ?? { nome, linhas: [], rendimento: '', observacoes: [], fases: new Map(), componentes: [], erros: [] }
    porNome.set(chave, ficha)
    ficha.linhas.push(linha)
    const erro = (texto: string) => ficha.erros.push(`linha ${linha}: ${texto}`)

    const rendimento = valor('rendimento')
    if (rendimento) {
      if (!(numeroCsv(rendimento) > 0)) erro(`rendimento inválido “${rendimento}”`)
      else if (ficha.rendimento && ficha.rendimento !== rendimento) erro(`rendimento diferente do informado antes (${ficha.rendimento})`)
      else ficha.rendimento = rendimento
    }
    if (valor('observacao')) ficha.observacoes.push(valor('observacao'))

    const ordemTexto = valor('fase_ordem')
    const ordem = ordemTexto ? Number(ordemTexto) : null
    if (ordemTexto && !(Number.isInteger(ordem) && ordem! > 0)) erro(`ordem da fase inválida “${ordemTexto}”`)
    else if (ordem) {
      const existente = ficha.fases.get(ordem)
      const fase = valor('fase'), tempoTexto = valor('tempo_min'), tempo = Number(tempoTexto)
      if (tempoTexto && !(Number.isInteger(tempo) && tempo > 0)) erro(`tempo inválido “${tempoTexto}”`)
      if (existente) {
        if (fase && normalizar(fase) !== normalizar(existente.fase)) erro(`fase ${ordem} já definida como “${existente.fase}”`)
        if (tempoTexto && tempo !== existente.tempo_previsto_min) erro(`tempo da fase ${ordem} diferente do informado antes`)
      } else if (!fase || !tempoTexto) erro(`fase ${ordem} precisa de nome e tempo na primeira linha em que aparece`)
      else ficha.fases.set(ordem, { fase, ordem, tempo_previsto_min: tempo })
    } else if (valor('fase') || valor('tempo_min')) erro('fase sem fase_ordem')

    const componente = valor('componente'), quantidade = valor('quantidade')
    if (componente) {
      const qb = aGosto.has(normalizar(quantidade))
      if (!qb && !(numeroCsv(quantidade) > 0)) erro(`quantidade inválida “${quantidade}” para ${componente}`)
      else ficha.componentes.push({ produto: componente, quantidade: qb ? null : String(numeroCsv(quantidade)), unidade: valor('unidade') || null, fase_ordem: ordem })
    } else if (quantidade) erro('quantidade sem componente')
  })
  const fichas = [...porNome.values()]
  for (const ficha of fichas) {
    if (!ficha.rendimento) ficha.erros.push('rendimento não informado')
    if (!ficha.fases.size) ficha.erros.push('nenhuma fase informada')
    if (!ficha.componentes.some((item) => item.quantidade)) ficha.erros.push('nenhum componente com quantidade')
  }
  if (!fichas.length) return { fichas, erro: 'Nenhuma ficha encontrada no arquivo.' }
  if (fichas.length > 200) return { fichas: [], erro: 'Limite de 200 fichas por importação.' }
  return { fichas }
}

export function SheetImportModal({ onClose, onSaved }: { onClose: () => void; onSaved: (total: number, fasesCriadas: string[], ignoradas: string[]) => void }) {
  const [arquivo, setArquivo] = useState('')
  const [fichas, setFichas] = useState<FichaCsv[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const comErro = fichas.filter((item) => item.erros.length)

  async function selecionar(file: File | undefined) {
    setError(''); setFichas([]); setArquivo(file?.name ?? '')
    if (!file) return
    const resultado = converterFichasCsv(await file.text())
    setFichas(resultado.fichas); if (resultado.erro) setError(resultado.erro)
  }
  function baixarModelo() {
    const url = URL.createObjectURL(new Blob(['﻿' + fichaModelo], { type: 'text/csv;charset=utf-8' }))
    const link = Object.assign(document.createElement('a'), { href: url, download: 'modelo-fichas-tecnicas.csv' })
    link.click(); URL.revokeObjectURL(url)
  }
  async function importar() {
    setSaving(true); setError('')
    try {
      const corpo = fichas.map((ficha) => ({
        produto: ficha.nome, rendimento: String(numeroCsv(ficha.rendimento)), observacao: ficha.observacoes.join('\n') || null,
        fases: [...ficha.fases.values()].sort((a, b) => a.ordem - b.ordem), componentes: ficha.componentes,
      }))
      const resposta = await api<{ total: number; fases_criadas: string[]; ignoradas: string[] }>('/api/fichas-tecnicas/lote', { method: 'POST', body: JSON.stringify({ fichas: corpo }) })
      onSaved(resposta.total, resposta.fases_criadas, resposta.ignoradas)
    } catch (reason) {
      const mensagem = reason instanceof Error ? reason.message : 'Não foi possível importar as fichas.'
      setError(mensagem.replace(/^ficha (\d+) \(/, (_, n: string) => `Linha ${fichas[Number(n) - 1]?.linhas[0] ?? n} (`))
    } finally { setSaving(false) }
  }
  return <Modal eyebrow="PADRONIZAÇÃO" title="Importar fichas técnicas (CSV)" wide onClose={onClose} footer={<><button className="secondary" onClick={onClose} type="button">Cancelar</button><button className="primary" type="button" onClick={() => void importar()} disabled={saving || !fichas.length || comErro.length > 0}>{saving ? 'Importando…' : `Importar ${fichas.length || ''} ficha(s)`}</button></>}>
    <div className="dialog-body">
      {error && <p className="form-error">{error}</p>}
      <p>Uma linha por componente; as linhas com o mesmo nome em <code>ficha</code> formam uma receita. Colunas: <code>{fichaColunas.join(';')}</code>.</p>
      <p>Produtos e fases são buscados pelo nome (sem diferenciar maiúsculas e acentos). A ficha precisa ser de um produto intermediário ou final já cadastrado; fases que não existem são criadas e produtos que já têm ficha são ignorados. Em <code>unidade</code>, g/mg/kg e ml/L são convertidos para a unidade do produto. Quantidade <code>q.b.</code> vira “a gosto” na observação. A importação é feita por completo ou não é feita.</p>
      <button className="text-button" type="button" onClick={baixarModelo}>Baixar modelo CSV →</button>
      <label>Arquivo CSV<input type="file" accept=".csv,text/csv" onChange={(event) => void selecionar(event.target.files?.[0])} /></label>
      {arquivo && fichas.length > 0 && <>
        <p>{fichas.length} ficha(s) em {arquivo}{comErro.length ? ` · ${comErro.length} com erro` : ''}.</p>
        <div className="table-wrap"><table><thead><tr><th>Linhas</th><th>Ficha</th><th>Rendimento</th><th>Fases</th><th>Componentes</th><th>A gosto</th><th>Status</th></tr></thead>
          <tbody>{fichas.map((ficha) => <tr key={ficha.linhas[0]}>
            <td>{ficha.linhas[0]}–{ficha.linhas[ficha.linhas.length - 1]}</td><td><strong>{ficha.nome}</strong></td><td>{ficha.rendimento || '—'}</td>
            <td>{[...ficha.fases.values()].sort((a, b) => a.ordem - b.ordem).map((fase) => `${fase.ordem}. ${fase.fase}`).join(', ') || '—'}</td>
            <td>{ficha.componentes.filter((item) => item.quantidade).length}</td>
            <td>{ficha.componentes.filter((item) => !item.quantidade).map((item) => item.produto).join(', ') || '—'}</td>
            <td>{ficha.erros.length ? <span className="form-error">{ficha.erros.join('; ')}</span> : 'OK'}</td>
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

const numeroFicha = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 })

function SheetDocument({ ficha }: { ficha: FichaTecnica }) {
  const branding = useBranding()
  const fases = [...ficha.fases].sort((a, b) => a.ordem - b.ordem)
  const semEtapa = ficha.componentes.filter((item) => item.fase_ordem == null)
  return <article className="sheet-document">
    <header className="sheet-document-head">
      <BrandMark className="sheet-brand-mark" variant="print" />
      <div><span>{branding.nome}</span><small>{branding.subtitulo}</small></div>
      <strong>FICHA TÉCNICA #{ficha.id}</strong>
    </header>
    <div className="sheet-title-block">
      <span className="eyebrow">RECEITA PADRONIZADA</span>
      <h1>{ficha.produto}</h1>
      <div className="sheet-summary"><span>Rendimento</span><strong>{numeroFicha.format(ficha.rendimento)} {ficha.unidade_rendimento}</strong><span>Tempo total</span><strong>{fases.reduce((total, fase) => total + fase.tempo_previsto_min, 0)} min</strong></div>
    </div>
    <section className="sheet-section">
      <h2>Componentes</h2>
      <table><thead><tr><th>Ingrediente ou preparo</th><th>Quantidade</th><th>Etapa</th></tr></thead><tbody>
        {ficha.componentes.map((item) => <tr key={item.id}><td>{item.produto}</td><td>{numeroFicha.format(item.quantidade)} {item.unidade_medida}</td><td>{item.fase_ordem == null ? 'Geral' : `Etapa ${item.fase_ordem}`}</td></tr>)}
      </tbody></table>
    </section>
    <section className="sheet-section">
      <h2>Modo de preparo</h2>
      <ol className="sheet-steps">
        {fases.map((fase) => {
          const componentes = ficha.componentes.filter((item) => item.fase_ordem === fase.ordem)
          return <li key={fase.id}><span>{fase.ordem}</span><div><h3>{fase.fase}<small>{fase.tempo_previsto_min} min</small></h3>{componentes.length > 0 && <p>{componentes.map((item) => `${item.produto} (${numeroFicha.format(item.quantidade)} ${item.unidade_medida})`).join(' · ')}</p>}</div></li>
        })}
      </ol>
      {semEtapa.length > 0 && <p className="sheet-general-components"><strong>Componentes gerais:</strong> {semEtapa.map((item) => item.produto).join(', ')}.</p>}
    </section>
    <section className="sheet-section sheet-notes"><h2>Observações</h2><p>{ficha.observacao || 'Sem observações adicionais.'}</p></section>
    <footer className="sheet-document-foot">Documento gerado pelo {branding.nome} · Ficha #{ficha.id}</footer>
  </article>
}

function SheetEditor({ ficha, produtos, catalogoFases, saving, setSaving, onSaved }: { ficha: FichaTecnica | null; produtos: Produto[]; catalogoFases: FaseCatalogo[]; saving: boolean; setSaving: (value: boolean) => void; onSaved: () => void }) {
  const productsForSheet = produtos.filter((produto) => produto.tipo !== 'INSUMO')
  const componentOptions = produtos.map((produto) => ({ value: produto.id, label: `${produto.nome} (${produto.unidade_medida})` }))
  const [produtoId, setProdutoId] = useState(ficha?.produto_id ?? productsForSheet[0]?.id ?? 0)
  const [rendimento, setRendimento] = useState(ficha?.rendimento ?? 1)
  const [observacao, setObservacao] = useState(ficha?.observacao ?? '')
  const [fases, setFases] = useState<DraftPhase[]>(ficha?.fases.map((fase) => ({ key: key(), fase_id: fase.fase_id, ordem: fase.ordem, tempo_previsto_min: fase.tempo_previsto_min })) ?? [{ key: key(), fase_id: catalogoFases[0]?.id ?? 0, ordem: 1, tempo_previsto_min: 10 }])
  const [componentes, setComponentes] = useState<DraftComponent[]>(ficha?.componentes.map((item) => ({ key: key(), produto_id: item.produto_id, quantidade: item.quantidade, fase_ordem: item.fase_ordem })) ?? [{ key: key(), produto_id: produtos[0]?.id ?? 0, quantidade: 1, fase_ordem: 1 }])
  const [error, setError] = useState('')

  const updatePhase = (rowKey: string, change: Partial<DraftPhase>) => setFases((rows) => rows.map((row) => row.key === rowKey ? { ...row, ...change } : row))
  const updateComponent = (rowKey: string, change: Partial<DraftComponent>) => setComponentes((rows) => rows.map((row) => row.key === rowKey ? { ...row, ...change } : row))
  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('')
    try {
      const body = { produto_id: produtoId, rendimento, observacao: observacao.trim() || null, fases: fases.map(({ fase_id, ordem, tempo_previsto_min }) => ({ fase_id, ordem, tempo_previsto_min })), componentes: componentes.map(({ produto_id, quantidade, fase_ordem }) => ({ produto_id, quantidade, fase_ordem })) }
      await api(ficha ? `/api/fichas-tecnicas/${ficha.id}` : '/api/fichas-tecnicas', { method: ficha ? 'PUT' : 'POST', body: JSON.stringify(body) }); onSaved()
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Não foi possível salvar a ficha.') } finally { setSaving(false) }
  }
  const addPhase = () => setFases((rows) => [...rows, { key: key(), fase_id: catalogoFases[0]?.id ?? 0, ordem: rows.length + 1, tempo_previsto_min: 10 }])
  const addComponent = () => setComponentes((rows) => [...rows, { key: key(), produto_id: produtos[0]?.id ?? 0, quantidade: 1, fase_ordem: fases[0]?.ordem ?? null }])
  const etapaOptions = [{ value: '' as const, label: 'Sem vínculo' }, ...fases.map((fase) => ({ value: fase.ordem, label: `Etapa ${fase.ordem}` }))]

  return <form className="dialog-body sheet-editor" id="sheet-form" onSubmit={save}>
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
}

export function SheetModal({ ficha, produtos, catalogoFases, canEdit, onClose, onSaved, onDeleted }: { ficha: FichaTecnica | null; produtos: Produto[]; catalogoFases: FaseCatalogo[]; canEdit: boolean; onClose: () => void; onSaved: () => void; onDeleted: () => void }) {
  const [editing, setEditing] = useState(ficha === null)
  const [saving, setSaving] = useState(false)

  async function remove() {
    if (!ficha || !window.confirm(`Excluir a ficha de “${ficha.produto}”?`)) return
    setSaving(true)
    try {
      await api(`/api/fichas-tecnicas/${ficha.id}`, { method: 'DELETE' })
      onDeleted()
    } catch (reason) {
      window.alert(reason instanceof Error ? reason.message : 'Não foi possível excluir a ficha técnica.')
    } finally { setSaving(false) }
  }
  function cancel() {
    if (editing && ficha) setEditing(false)
    else onClose()
  }
  function print() {
    if (!ficha || editing) return
    const cleanup = () => document.body.classList.remove('printing-sheet')
    document.body.classList.add('printing-sheet')
    window.addEventListener('afterprint', cleanup, { once: true })
    window.print()
    cleanup()
  }

  const footer = <>
    {ficha && canEdit && <button className="secondary outline" type="button" disabled={editing || saving} onClick={() => setEditing(true)}>Editar</button>}
    {editing && <button className="primary" form="sheet-form" disabled={saving}>{saving ? 'Salvando…' : 'Salvar'}</button>}
    <button className="secondary" onClick={cancel} type="button" disabled={saving}>Cancelar</button>
    {ficha && <button className="primary print-action" type="button" onClick={print} disabled={editing || saving}>Imprimir</button>}
    {ficha && canEdit && editing && <button className="danger-link" type="button" onClick={() => void remove()} disabled={saving}>Excluir ficha</button>}
  </>

  return <Modal className="sheet-dialog" eyebrow="PADRONIZAÇÃO" title={ficha ? (editing ? 'Editar ficha técnica' : 'Ficha técnica') : 'Nova ficha técnica'} wide onClose={cancel} footer={footer}>
    {editing
      ? <SheetEditor key={`${ficha?.id ?? 'new'}-${editing}`} ficha={ficha} produtos={produtos} catalogoFases={catalogoFases} saving={saving} setSaving={setSaving} onSaved={onSaved} />
      : ficha && <SheetDocument ficha={ficha} />}
  </Modal>
}
