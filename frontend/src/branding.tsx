import { createContext, useContext } from 'react'

/** Identidade visual. Os valores padrão valem quando a API não fornece outros. */
export interface Branding {
  nome: string
  subtitulo: string
  sigla: string
  titulo: string
  logo?: string
  logo_horizontal?: string
  logo_impressao?: string
  favicon?: string
  apple_touch_icon?: string
  css?: string
}

export const brandingPadrao: Branding = {
  nome: 'Cozinha+',
  subtitulo: 'GESTÃO DE COZINHA',
  sigla: 'C+',
  titulo: 'Cozinha+ · Operação de cozinha',
}

const BrandingContext = createContext<Branding>(brandingPadrao)
export const BrandingProvider = BrandingContext.Provider
export const useBranding = () => useContext(BrandingContext)

/** Busca a identidade na API e aplica título, ícones e CSS custom. Falhas mantêm o padrão. */
export async function carregarBranding(): Promise<Branding> {
  let custom: Partial<Branding> = {}
  try {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 3000)
    const response = await fetch('/api/branding', { signal: controller.signal })
    window.clearTimeout(timeout)
    if (response.ok) custom = await response.json()
  } catch { /* API indisponível: mantém o padrão */ }
  const branding = { ...brandingPadrao, ...custom }

  document.title = branding.titulo
  document.documentElement.style.setProperty('--brand-sigla', JSON.stringify(branding.sigla))
  if (branding.favicon) {
    document.querySelectorAll('link[rel="icon"]').forEach((link) => link.remove())
    document.head.append(Object.assign(document.createElement('link'), { rel: 'icon', href: branding.favicon }))
  }
  if (branding.apple_touch_icon) document.querySelector<HTMLLinkElement>('link[rel="apple-touch-icon"]')?.setAttribute('href', branding.apple_touch_icon)
  if (branding.css) document.head.append(Object.assign(document.createElement('link'), { rel: 'stylesheet', href: branding.css }))
  return branding
}

/** Escolhe a aplicação adequada da marca para fundos escuros ou impressão. */
export function BrandMark({ className, variant = 'symbol' }: { className: string; variant?: 'symbol' | 'horizontal' | 'print' }) {
  const { logo, logo_horizontal, logo_impressao, sigla, nome } = useBranding()
  const source = variant === 'horizontal' ? logo_horizontal ?? logo : variant === 'print' ? logo_impressao ?? logo : logo
  return <div className={`${className}${source ? ' has-logo' : ''}`}>{source ? <img src={source} alt={nome} /> : sigla}</div>
}
