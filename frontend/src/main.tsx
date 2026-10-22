import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ThemeProvider } from './components/theme/ThemeProvider'
import '@fontsource-variable/inter/wght.css'
import '@fontsource-variable/manrope/wght.css'
import '@fontsource-variable/source-code-pro/wght.css'
import './styles/index.css'
import './styles/developer-platform.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
