import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDashboard, seedDemoData } from '../api';
import type { DashboardStats } from '../types';

function fmt(v: string | number) {
  const n = parseFloat(String(v));
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Dashboard() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  });

  const seed = useMutation({
    mutationFn: seedDemoData,
    onSuccess: () => qc.invalidateQueries(),
  });

  if (isLoading) return <div className="loading">加载中...</div>;

  return (
    <div>
      <div className="toolbar">
        <div className="toolbar-spacer" />
        <button className="btn btn-secondary" onClick={() => seed.mutate()}>
          📋 初始化演示数据
        </button>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">客户总数</div>
          <div className="stat-value">{data?.total_customers}</div>
          <div className="stat-sub">活跃 {data?.active_customers} 家</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">本月订单数</div>
          <div className="stat-value primary">{data?.total_orders_this_month}</div>
          <div className="stat-sub">当月全部状态</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">本月订单金额</div>
          <div className="stat-value primary">¥{fmt(data?.total_amount_this_month ?? 0)}</div>
          <div className="stat-sub">排除已取消订单</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">待处理账单</div>
          <div className="stat-value warning">{data?.pending_statements}</div>
          <div className="stat-sub">待出账 + 已出账未付款</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">逾期账单</div>
          <div className="stat-value danger">{data?.overdue_statements}</div>
          <div className="stat-sub">逾期金额 ¥{fmt(data?.overdue_amount ?? 0)}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">系统说明</h2>
        </div>
        <div className="card-body">
          <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '2' }}>
            <li>本系统专为 DSO 大客户月结场景设计，无需对接支付</li>
            <li>创建<strong>客户</strong>后，即可创建<strong>订单</strong>并添加产品明细</li>
            <li>每月底可为每个客户生成<strong>月结账单</strong>，汇总当月已确认/发货/收货的订单</li>
            <li>账单状态流转：待出账 → 已出账 → 已结清（或 逾期）</li>
            <li>订单状态流转：草稿 → 已确认 → 已发货 → 已收货</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
