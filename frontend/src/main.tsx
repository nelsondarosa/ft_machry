import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { BrandingProvider, carregarBranding } from './branding'
import './styles.css'

void carregarBranding().then((branding) => createRoot(document.getElementById('app')!).render(
  <StrictMode>
    <BrandingProvider value={branding}>
      <App />
    </BrandingProvider>
  </StrictMode>,
))
