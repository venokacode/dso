import type { OrderStatus, StatementStatus, CustomerStatus } from '../types';

const ORDER_STATUS_MAP: Record<OrderStatus, { label: string; cls: string }> = {
  draft:     { label: '草稿',   cls: 'badge-gray' },
  confirmed: { label: '已确认', cls: 'badge-blue' },
  shipped:   { label: '已发货', cls: 'badge-yellow' },
  delivered: { label: '已收货', cls: 'badge-green' },
  cancelled: { label: '已取消', cls: 'badge-gray' },
};

const STMT_STATUS_MAP: Record<StatementStatus, { label: string; cls: string }> = {
  open:    { label: '待出账', cls: 'badge-gray' },
  issued:  { label: '已出账', cls: 'badge-blue' },
  paid:    { label: '已结清', cls: 'badge-green' },
  overdue: { label: '已逾期', cls: 'badge-red' },
};

const CUST_STATUS_MAP: Record<CustomerStatus, { label: string; cls: string }> = {
  active:   { label: '正常', cls: 'badge-green' },
  inactive: { label: '停用', cls: 'badge-gray' },
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const m = ORDER_STATUS_MAP[status] ?? { label: status, cls: 'badge-gray' };
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}

export function StatementStatusBadge({ status }: { status: StatementStatus }) {
  const m = STMT_STATUS_MAP[status] ?? { label: status, cls: 'badge-gray' };
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}

export function CustomerStatusBadge({ status }: { status: CustomerStatus }) {
  const m = CUST_STATUS_MAP[status] ?? { label: status, cls: 'badge-gray' };
  return <span className={`badge ${m.cls}`}>{m.label}</span>;
}
