import { useLocation, useNavigate } from 'react-router-dom';

const nav = [
  { section: '概览', items: [
    { path: '/', icon: '📊', label: '仪表盘' },
  ]},
  { section: '业务', items: [
    { path: '/orders',     icon: '📦', label: '订单管理' },
    { path: '/statements', icon: '📋', label: '月结账单' },
  ]},
  { section: '基础数据', items: [
    { path: '/customers', icon: '🏢', label: '客户管理' },
    { path: '/products',  icon: '🛒', label: '产品管理' },
  ]},
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>DSO 订单系统</h1>
        <p>大客户月结管理</p>
      </div>
      <nav className="sidebar-nav">
        {nav.map(({ section, items }) => (
          <div key={section} className="sidebar-section">
            <div className="sidebar-section-label">{section}</div>
            {items.map(({ path, icon, label }) => (
              <button
                key={path}
                className={`sidebar-link ${location.pathname === path ? 'active' : ''}`}
                onClick={() => navigate(path)}
              >
                <span className="sidebar-icon">{icon}</span>
                {label}
              </button>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
