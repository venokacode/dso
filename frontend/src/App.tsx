import { useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { ConfigProvider, Layout, Menu, theme } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  AppstoreOutlined,
  ShoppingCartOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import zhCN from "antd/locale/zh_CN";

import Dashboard from "./pages/Dashboard";
import Customers from "./pages/Customers";
import Products from "./pages/Products";
import Orders from "./pages/Orders";
import Invoices from "./pages/Invoices";

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "工作台" },
  { key: "/customers", icon: <TeamOutlined />, label: "客户管理" },
  { key: "/products", icon: <AppstoreOutlined />, label: "产品管理" },
  { key: "/orders", icon: <ShoppingCartOutlined />, label: "订单管理" },
  { key: "/invoices", icon: <FileTextOutlined />, label: "月结账单" },
];

function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{ borderRight: "1px solid #f0f0f0" }}
      >
        <div style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 700,
          fontSize: collapsed ? 16 : 20,
          color: "#1677ff",
          borderBottom: "1px solid #f0f0f0",
        }}>
          {collapsed ? "DSO" : "DSO 订单系统"}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: "#fff",
          padding: "0 24px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          fontSize: 16,
          fontWeight: 600,
        }}>
          {menuItems.find((m) => m.key === location.pathname)?.label || "DSO 订单系统"}
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 8, minHeight: 360 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/products" element={<Products />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/invoices" element={<Invoices />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ConfigProvider>
  );
}
