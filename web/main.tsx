import { createRoot } from 'react-dom/client'
import '@xyflow/react/dist/style.css'
import 'katex/dist/katex.min.css'
import './styles.css'
import App from './App'

const el = document.getElementById('root')
if (!el) throw new Error('missing #root')

createRoot(el).render(<App />)
