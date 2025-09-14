import '@ant-design/v5-patch-for-react-19';
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import '@xyflow/react/dist/style.css';
import 'antd/dist/reset.css';

createRoot(document.getElementById('root')!).render(
  <App />
)
