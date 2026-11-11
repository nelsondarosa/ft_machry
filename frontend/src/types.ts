export type TipoProduto = 'INSUMO' | 'INTERMEDIARIO' | 'FINAL'
export type Conservacao = 'SECO' | 'RESFRIADO' | 'CONGELADO'
export type PapelUsuario = 'OWNER' | 'ADMIN' | 'USER'

export interface Usuario {
  id: number
  nome: string
  username: string
  papel: PapelUsuario
  ativo: number
}

export interface Produto {
  id: number
  nome: string
  tipo: TipoProduto
  unidade_medida: string
  grupo_id: number | null
  subdivisao: string | null
  conservacao: Conservacao
  validade_obrigatoria: number
  validade_padrao_dias: number | null
  foto_url: string | null
  ativo: number
  criado_em: string
}

export interface FaseCatalogo {
  id: number
  nome: string
}

export interface FichaFase {
  id: number
  fase_id: number
  fase: string
  ordem: number
  tempo_previsto_min: number
}

export interface FichaComponente {
  id: number
  produto_id: number
  produto: string
  unidade_medida: string
  quantidade: number
  ficha_tecnica_fase_id: number | null
  fase_ordem: number | null
}

export interface FichaTecnica {
  id: number
  produto_id: number
  produto: string
  unidade_rendimento: string
  rendimento: number
  observacao: string | null
  fases: FichaFase[]
  componentes: FichaComponente[]
}

export interface ItemInventario {
  produto_id: number
  produto: string
  tipo_produto: TipoProduto
  unidade_medida: string
  lote_id: number
  quantidade: number
  data_validade: string | null
  localizacao: string
}

export interface Localizacao {
  id: number
  nome: string
  tipo: Conservacao
  parent_id: number | null
  foto_url: string | null
}

export interface Lote {
  id: number
  produto_id: number
  produto: string
  localizacao_id: number
  localizacao: string
  quantidade: number
  data_producao: string | null
  data_validade: string | null
  custo_unitario: number | null
  fornecedor: string | null
  nota_fiscal: string | null
  criado_em: string
  itens_total: number
  itens_disponiveis: number
  itens_reservados: number
  itens_em_uso: number
  itens_consumidos: number
}

export type StatusItem = 'DISPONIVEL' | 'RESERVADA' | 'EM_USO' | 'CONSUMIDA'

export interface ItemLote {
  id: number
  lote_id: number
  lote_origem_id: number
  sequencia: number
  codigo: string
  quantidade: number
  saldo: number
  fabricante: string | null
  data_fabricacao: string | null
  data_validade: string | null
  status: StatusItem
  solicitacao_producao_id: number | null
  aberto_em: string | null
  criado_em: string
}

export interface SolicitacaoProducao {
  id: number
  ficha_tecnica_id: number
  usuario_id: number
  status: string
  criado_em: string
  concluido_em: string | null
}

export type View =
  | 'inicio'
  | 'produtos'
  | 'fichas'
  | 'estoque'
  | 'producao'
  | 'historico'
  | 'locais'
  | 'usuarios'
