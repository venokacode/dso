import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getOrders, getOrder, getCustomers, getProducts, createOrder, updateOrder, deleteOrder } from '../api';
import type { OrderListItem, Order, Customer, Product } from '../types';
import { OrderStatusBadge } from '../components/StatusBadge';

const ORDER_STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'draft',     label: '草稿' },
  { value: 'confirmed', label: '已确认' },
  { value: 'shipped',   label: '已发货' },
  { value: 'delivered', label: '已收货' },
  { value: 'cancelled', label: '已取消' },
];

function fmtMoney(v: string | number) {
  return '¥' + parseFloat(String(v)).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface ItemRow {
  product_id: string;
  quantity: string;
  unit_price: string;
  discount_rate: string;
  notes: string;
}

const EMPTY_ITEM: ItemRow = { product_id: '', quantity: '1', unit_price: '', discount_rate: '0', notes: '' };

interface OrderFormData {
  customer_id: string;
  order_date: string;
  delivery_date: string;
  delivery_address: string;
  discount_amount: string;
  notes: string;
  items: ItemRow[];
}

const today = new Date().toISOString().slice(0, 10);

const EMPTY_FORM: OrderFormData = {
  customer_id: '', order_date: today, delivery_date: '',
  delivery_address: '', discount_amount: '0', notes: '',
  items: [{ ...EMPTY_ITEM }],
};

export default function Orders() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [form, setForm] = useState<OrderFormData>(EMPTY_FORM);
  const [error, setError] = useState('');

  const { data: orders = [], isLoading } = useQuery<OrderListItem[]>({
    queryKey: ['orders', statusFilter],
    queryFn: () => getOrders(statusFilter ? { status: statusFilter } : {}),
  });

  const { data: customers = [] } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: () => getCustomers(),
  });

  const { data: products = [] } = useQuery<Product[]>({
    queryKey: ['products'],
    queryFn: () => getProducts({ is_active: true }),
  });

  const { data: detail } = useQuery<Order>({
    queryKey: ['order', detailId],
    queryFn: () => getOrder(detailId!),
    enabled: !!detailId,
  });

  const saveOrder = useMutation({
    mutationFn: (d: object) => createOrder(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      setShowModal(false);
    },
    onError: (e: any) => setError(e.response?.data?.detail || '保存失败'),
  });

  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      updateOrder(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      qc.invalidateQueries({ queryKey: ['order', detailId] });
    },
  });

  const removeOrder = useMutation({
    mutationFn: (id: number) => deleteOrder(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] });
      setDetailId(null);
    },
  });

  function setItemField(idx: number, key: keyof ItemRow, val: string) {
    setForm(f => {
      const items = [...f.items];
      items[idx] = { ...items[idx], [key]: val };
      if (key === 'product_id' && val) {
        const prod = products.find(p => String(p.id) === val);
        if (prod) items[idx].unit_price = prod.unit_price;
      }
      return { ...f, items };
    });
  }

  function addItem() {
    setForm(f => ({ ...f, items: [...f.items, { ...EMPTY_ITEM }] }));
  }

  function removeItem(idx: number) {
    setForm(f => ({ ...f, items: f.items.filter((_, i) => i !== idx) }));
  }

  function calcSubtotal() {
    return form.items.reduce((sum, item) => {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.unit_price) || 0;
      const disc = parseFloat(item.discount_rate) || 0;
      return sum + qty * price * (1 - disc);
    }, 0);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const validItems = form.items.filter(i => i.product_id && parseFloat(i.quantity) > 0);
    if (!validItems.length) {
      setError('请至少添加一个有效产品明细');
      return;
    }
    saveOrder.mutate({
      customer_id: parseInt(form.customer_id),
      order_date: form.order_date,
      delivery_date: form.delivery_date || undefined,
      delivery_address: form.delivery_address || undefined,
      discount_amount: parseFloat(form.discount_amount) || 0,
      notes: form.notes || undefined,
      items: validItems.map(i => ({
        product_id: parseInt(i.product_id),
        quantity: parseFloat(i.quantity),
        unit_price: parseFloat(i.unit_price),
        discount_rate: parseFloat(i.discount_rate) || 0,
        notes: i.notes || undefined,
      })),
    });
  }

  const subtotal = calcSubtotal();
  const discount = parseFloat(form.discount_amount) || 0;
  const total = subtotal - discount;

  return (
    <div>
      <div className="toolbar">
        <select className="select-control" value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}>
          {ORDER_STATUS_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <div className="toolbar-spacer" />
        <button className="btn btn-primary" onClick={() => {
          setForm({ ...EMPTY_FORM, order_date: today });
          setError('');
          setShowModal(true);
        }}>+ 新建订单</button>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading ? (
            <div className="loading">加载中...</div>
          ) : orders.length === 0 ? (
            <div className="empty-state">
              <h3>暂无订单</h3>
              <p>点击「新建订单」创建第一笔订单</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>订单号</th>
                  <th>客户</th>
                  <th>下单日期</th>
                  <th>状态</th>
                  <th>订单金额</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id}>
                    <td className="font-mono fw-600 text-primary"
                      style={{ cursor: 'pointer' }}
                      onClick={() => setDetailId(o.id)}>
                      {o.order_no}
                    </td>
                    <td>{o.customer.name}</td>
                    <td>{o.order_date}</td>
                    <td><OrderStatusBadge status={o.status} /></td>
                    <td className="text-right fw-600">{fmtMoney(o.total_amount)}</td>
                    <td>
                      <button className="btn btn-sm btn-ghost" onClick={() => setDetailId(o.id)}>详情</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">新建订单</span>
              <button className="btn-icon" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}

                <div className="form-grid">
                  <div className="form-group">
                    <label>客户 *</label>
                    <select className="form-control" required value={form.customer_id}
                      onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))}>
                      <option value="">请选择客户</option>
                      {customers.map(c => (
                        <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>下单日期 *</label>
                    <input className="form-control" type="date" required value={form.order_date}
                      onChange={e => setForm(f => ({ ...f, order_date: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>预计送货日期</label>
                    <input className="form-control" type="date" value={form.delivery_date}
                      onChange={e => setForm(f => ({ ...f, delivery_date: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>整单折扣金额（元）</label>
                    <input className="form-control" type="number" min="0" step="0.01"
                      value={form.discount_amount}
                      onChange={e => setForm(f => ({ ...f, discount_amount: e.target.value }))} />
                  </div>
                  <div className="form-group full">
                    <label>送货地址</label>
                    <input className="form-control" value={form.delivery_address}
                      onChange={e => setForm(f => ({ ...f, delivery_address: e.target.value }))} />
                  </div>
                  <div className="form-group full">
                    <label>备注</label>
                    <textarea className="form-control" value={form.notes}
                      onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                  </div>
                </div>

                <div className="divider" />
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
                  <strong>产品明细</strong>
                  <div style={{ flex: 1 }} />
                  <button type="button" className="btn btn-sm btn-secondary" onClick={addItem}>+ 添加行</button>
                </div>

                <div className="table-wrap">
                  <table className="order-items-table">
                    <thead>
                      <tr>
                        <th style={{ width: '30%' }}>产品</th>
                        <th style={{ width: '12%' }}>数量</th>
                        <th style={{ width: '15%' }}>单价</th>
                        <th style={{ width: '12%' }}>折扣率</th>
                        <th style={{ width: '15%' }}>小计</th>
                        <th style={{ width: '16%' }}>备注</th>
                        <th style={{ width: '4%' }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {form.items.map((item, idx) => {
                        const qty = parseFloat(item.quantity) || 0;
                        const price = parseFloat(item.unit_price) || 0;
                        const disc = parseFloat(item.discount_rate) || 0;
                        const lineTotal = qty * price * (1 - disc);
                        return (
                          <tr key={idx}>
                            <td>
                              <select value={item.product_id}
                                onChange={e => setItemField(idx, 'product_id', e.target.value)}>
                                <option value="">请选择</option>
                                {products.map(p => (
                                  <option key={p.id} value={p.id}>
                                    {p.sku} - {p.name}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td>
                              <input type="number" min="0.001" step="0.001"
                                value={item.quantity}
                                onChange={e => setItemField(idx, 'quantity', e.target.value)} />
                            </td>
                            <td>
                              <input type="number" min="0" step="0.01"
                                value={item.unit_price}
                                onChange={e => setItemField(idx, 'unit_price', e.target.value)} />
                            </td>
                            <td>
                              <input type="number" min="0" max="1" step="0.01"
                                placeholder="0=无折扣"
                                value={item.discount_rate}
                                onChange={e => setItemField(idx, 'discount_rate', e.target.value)} />
                            </td>
                            <td style={{ fontWeight: 600 }}>
                              {fmtMoney(lineTotal)}
                            </td>
                            <td>
                              <input type="text" value={item.notes}
                                onChange={e => setItemField(idx, 'notes', e.target.value)} />
                            </td>
                            <td>
                              {form.items.length > 1 && (
                                <button type="button" className="btn-icon"
                                  onClick={() => removeItem(idx)}>✕</button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div style={{ textAlign: 'right', marginTop: '12px' }}>
                  <div style={{ fontSize: '13px', color: 'var(--gray-500)' }}>
                    小计：{fmtMoney(subtotal)}
                    {discount > 0 && <span style={{ marginLeft: 12 }}>折扣：-{fmtMoney(discount)}</span>}
                  </div>
                  <div style={{ fontSize: '18px', fontWeight: 700, marginTop: 4 }}>
                    订单合计：{fmtMoney(total)}
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>取消</button>
                <button type="submit" className="btn btn-primary" disabled={saveOrder.isPending}>
                  {saveOrder.isPending ? '提交中...' : '提交订单'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {detailId && detail && (
        <div className="modal-overlay" onClick={() => setDetailId(null)}>
          <div className="modal modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">订单详情 — {detail.order_no}</span>
              <OrderStatusBadge status={detail.status} />
              <div style={{ flex: 1 }} />
              <button className="btn-icon" onClick={() => setDetailId(null)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-grid">
                <div>
                  <div className="text-sm text-muted">客户</div>
                  <div className="fw-600">{detail.customer.name}</div>
                </div>
                <div>
                  <div className="text-sm text-muted">下单日期</div>
                  <div>{detail.order_date}</div>
                </div>
                <div>
                  <div className="text-sm text-muted">送货日期</div>
                  <div>{detail.delivery_date || '—'}</div>
                </div>
                <div>
                  <div className="text-sm text-muted">送货地址</div>
                  <div>{detail.delivery_address || '—'}</div>
                </div>
                {detail.notes && (
                  <div className="full">
                    <div className="text-sm text-muted">备注</div>
                    <div>{detail.notes}</div>
                  </div>
                )}
              </div>

              <div className="divider" />
              <table className="order-items-table">
                <thead>
                  <tr>
                    <th>产品</th>
                    <th>SKU</th>
                    <th>数量</th>
                    <th>单价</th>
                    <th>折扣率</th>
                    <th>小计</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.items.map(item => (
                    <tr key={item.id}>
                      <td className="fw-600">{item.product.name}</td>
                      <td className="font-mono text-muted">{item.product.sku}</td>
                      <td>{parseFloat(item.quantity)} {item.product.unit}</td>
                      <td>{fmtMoney(item.unit_price)}</td>
                      <td>{parseFloat(item.discount_rate) > 0
                        ? `${(parseFloat(item.discount_rate) * 100).toFixed(0)}%`
                        : '—'}</td>
                      <td className="fw-600">{fmtMoney(item.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div style={{ textAlign: 'right', marginTop: '12px' }}>
                <div className="text-sm text-muted">小计：{fmtMoney(detail.subtotal)}</div>
                {parseFloat(detail.discount_amount) > 0 && (
                  <div className="text-sm text-muted">折扣：-{fmtMoney(detail.discount_amount)}</div>
                )}
                <div style={{ fontSize: '20px', fontWeight: 700, marginTop: 4 }}>
                  合计：{fmtMoney(detail.total_amount)}
                </div>
              </div>

              <div className="divider" />
              <div>
                <div className="text-sm text-muted mb-8">更新订单状态</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {['confirmed', 'shipped', 'delivered', 'cancelled'].map(s => (
                    <button key={s} className="btn btn-sm btn-secondary"
                      disabled={detail.status === s || changeStatus.isPending}
                      onClick={() => changeStatus.mutate({ id: detail.id, status: s })}>
                      {s === 'confirmed' ? '确认' : s === 'shipped' ? '发货' : s === 'delivered' ? '收货' : '取消'}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              {detail.status === 'draft' && (
                <button className="btn btn-danger btn-sm"
                  onClick={() => {
                    if (confirm('确定删除此订单？')) removeOrder.mutate(detail.id);
                  }}>
                  删除订单
                </button>
              )}
              <div style={{ flex: 1 }} />
              <button className="btn btn-secondary" onClick={() => setDetailId(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
