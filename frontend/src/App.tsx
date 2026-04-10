import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import Products from './pages/Products';
import Orders from './pages/Orders';
import Statements from './pages/Statements';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

const PAGE_TITLES: Record<string, string> = {
  '/':           '仪表盘',
  '/orders':     '订单管理',
  '/statements': '月结账单',
  '/customers':  '客户管理',
  '/products':   '产品管理',
};

function AppShell() {
  const path = window.location.pathname;
  const title = PAGE_TITLES[path] ?? 'DSO 订单系统';

  return (
    <div className="layout">
      <Sidebar />
      <div className="main">
        <header className="topbar">
          <span className="topbar-title">{title}</span>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/statements" element={<Statements />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/products" element={<Products />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
