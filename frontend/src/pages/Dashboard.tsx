import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Spin } from "antd";
import {
  TeamOutlined,
  ShoppingOutlined,
  FileTextOutlined,
  DollarOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { dashboardApi, fen2yuan } from "../services/api";

interface Stats {
  total_customers: number;
  total_products: number;
  total_orders: number;
  orders_this_month: number;
  revenue_this_month: number;
  pending_invoices: number;
  unpaid_amount: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboardApi.get().then((r) => {
      setStats(r.data);
      setLoading(false);
    });
  }, []);

  if (loading) return <Spin size="large" style={{ marginTop: 100, display: "block" }} />;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>工作台</h2>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="活跃客户"
              value={stats?.total_customers}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="在售产品"
              value={stats?.total_products}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="总订单数"
              value={stats?.total_orders}
              prefix={<ShoppingOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable>
            <Statistic
              title="本月订单"
              value={stats?.orders_this_month}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card hoverable>
            <Statistic
              title="本月营收（元）"
              value={fen2yuan(stats?.revenue_this_month ?? 0)}
              prefix={<DollarOutlined />}
              precision={2}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card hoverable>
            <Statistic
              title="待处理账单"
              value={stats?.pending_invoices}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card hoverable>
            <Statistic
              title="应收账款（元）"
              value={fen2yuan(stats?.unpaid_amount ?? 0)}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: (stats?.unpaid_amount ?? 0) > 0 ? "#cf1322" : undefined }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
