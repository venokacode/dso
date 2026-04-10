import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getStatements, getStatement, getCustomers, createStatement, updateStatement } from '../api';
import type { StatementListItem, MonthlyStatement, Customer } from '../types';
import { StatementStatusBadge, OrderStatusBadge } from '../components/StatusBadge';

function fmtMoney(v: string | number) {
  return '¥' + parseFloat(String(v)).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const STMT_STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'open',    label: '待出账' },
  { value: 'issued',  label: '已出账' },
  { value: 'paid',    label: '已结清' },
  { value: 'overdue', label: '已逾期' },
];

export default function Statements() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [error, setError] = useState('');

  const now = new Date();
  const [genForm, setGenForm] = useState({
    customer_id: '',
    year: String(now.getFullYear()),
    month: String(now.getMonth() + 1),
    notes: '',
  });

  const { data: statements = [], isLoading } = useQuery<StatementListItem[]>({
    queryKey: ['statements', statusFilter],
    queryFn: () => getStatements(statusFilter ? { status: statusFilter } : {}),
  });

  const { data: customers = [] } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: () => getCustomers(),
  });

  const { data: detail } = useQuery<MonthlyStatement>({
    queryKey: ['statement', detailId],
    queryFn: () => getStatement(detailId!),
    enabled: !!detailId,
  });

  const genStatement = useMutation({
    mutationFn: (d: object) => createStatement(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['statements'] });
      setShowCreate(false);
    },
    onError: (e: any) => setError(e.response?.data?.detail || '生成失败'),
  });

  const updateStmt = useMutation({
    mutationFn: ({ id, data }: { id: number; data: object }) => updateStatement(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['statements'] });
      qc.invalidateQueries({ queryKey: ['statement', detailId] });
    },
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    genStatement.mutate({
      customer_id: parseInt(genForm.customer_id),
      year: parseInt(genForm.year),
      month: parseInt(genForm.month),
      notes: genForm.notes || undefined,
    });
  }

  return (
    <div>
      <div className="toolbar">
        <select className="select-control" value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}>
          {STMT_STATUS_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <div className="toolbar-spacer" />
        <button className="btn btn-primary" onClick={() => {
          setGenForm({ customer_id: '', year: String(now.getFullYear()), month: String(now.getMonth() + 1), notes: '' });
          setError('');
          setShowCreate(true);
        }}>
          + 生成月结账单
        </button>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading ? (
            <div className="loading">加载中...</div>
          ) : statements.length === 0 ? (
            <div className="empty-state">
              <h3>暂无月结账单</h3>
              <p>月底时，为每个客户生成当月月结账单</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>账单号</th>
                  <th>客户</th>
                  <th>账单月份</th>
                  <th>状态</th>
                  <th>账单金额</th>
                  <th>出账日期</th>
                  <th>到期日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {statements.map(s => (
                  <tr key={s.id}>
                    <td className="font-mono fw-600 text-primary"
                      style={{ cursor: 'pointer' }}
                      onClick={() => setDetailId(s.id)}>
                      {s.statement_no}
                    </td>
                    <td>{s.customer.name}</td>
                    <td>{s.year}年{s.month}月</td>
                    <td><StatementStatusBadge status={s.status} /></td>
                    <td className="text-right fw-600">{fmtMoney(s.total_amount)}</td>
                    <td>{s.issued_date || '—'}</td>
                    <td className={s.status === 'overdue' ? 'text-danger fw-600' : ''}>
                      {s.due_date || '—'}
                    </td>
                    <td>
                      <button className="btn btn-sm btn-ghost" onClick={() => setDetailId(s.id)}>详情</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Generate Modal */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">生成月结账单</span>
              <button className="btn-icon" onClick={() => setShowCreate(false)}>✕</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}
                <div className="alert alert-info">
                  系统将自动汇总所选客户在该月份中状态为「已确认/已发货/已收货」且尚未出账的订单
                </div>
                <div className="form-grid">
                  <div className="form-group full">
                    <label>客户 *</label>
                    <select className="form-control" required value={genForm.customer_id}
                      onChange={e => setGenForm(f => ({ ...f, customer_id: e.target.value }))}>
                      <option value="">请选择客户</option>
                      {customers.map(c => (
                        <option key={c.id} value={c.id}>{c.code} - {c.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>年份 *</label>
                    <input className="form-control" type="number" required
                      min="2020" max="2099" value={genForm.year}
                      onChange={e => setGenForm(f => ({ ...f, year: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>月份 *</label>
                    <select className="form-control" required value={genForm.month}
                      onChange={e => setGenForm(f => ({ ...f, month: e.target.value }))}>
                      {Array.from({ length: 12 }, (_, i) => (
                        <option key={i + 1} value={i + 1}>{i + 1}月</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group full">
                    <label>备注</label>
                    <textarea className="form-control" value={genForm.notes}
                      onChange={e => setGenForm(f => ({ ...f, notes: e.target.value }))} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>取消</button>
                <button type="submit" className="btn btn-primary" disabled={genStatement.isPending}>
                  {genStatement.isPending ? '生成中...' : '生成账单'}
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
              <span className="modal-title">账单详情 — {detail.statement_no}</span>
              <StatementStatusBadge status={detail.status} />
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
                  <div className="text-sm text-muted">账单月份</div>
                  <div className="fw-600">{detail.year}年{detail.month}月</div>
                </div>
                <div>
                  <div className="text-sm text-muted">出账日期</div>
                  <div>{detail.issued_date || '—'}</div>
                </div>
                <div>
                  <div className="text-sm text-muted">到期日期</div>
                  <div className={detail.status === 'overdue' ? 'text-danger fw-600' : ''}>
                    {detail.due_date || '—'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted">付款日期</div>
                  <div className={detail.paid_date ? 'text-success fw-600' : ''}>
                    {detail.paid_date || '—'}
                  </div>
                </div>
                {detail.notes && (
                  <div className="full">
                    <div className="text-sm text-muted">备注</div>
                    <div>{detail.notes}</div>
                  </div>
                )}
              </div>

              <div className="divider" />
              <div style={{ marginBottom: 8 }}>
                <strong>包含订单</strong>
                <span className="badge badge-gray" style={{ marginLeft: 8 }}>{detail.orders.length} 笔</span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>订单号</th>
                    <th>下单日期</th>
                    <th>状态</th>
                    <th>金额</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.orders.length === 0 ? (
                    <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--gray-400)', padding: '24px' }}>
                      无关联订单
                    </td></tr>
                  ) : detail.orders.map(o => (
                    <tr key={o.id}>
                      <td className="font-mono fw-600">{o.order_no}</td>
                      <td>{o.order_date}</td>
                      <td><OrderStatusBadge status={o.status} /></td>
                      <td className="fw-600">{fmtMoney(o.total_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div style={{ textAlign: 'right', marginTop: 12 }}>
                <div style={{ fontSize: 20, fontWeight: 700 }}>
                  账单合计：{fmtMoney(detail.total_amount)}
                </div>
              </div>

              <div className="divider" />
              <div>
                <div className="text-sm text-muted mb-8">更新账单状态</div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  {detail.status === 'open' && (
                    <button className="btn btn-sm btn-primary"
                      onClick={() => updateStmt.mutate({
                        id: detail.id,
                        data: { status: 'issued', issued_date: new Date().toISOString().slice(0, 10) }
                      })}>
                      发出账单
                    </button>
                  )}
                  {(detail.status === 'issued' || detail.status === 'overdue') && (
                    <button className="btn btn-sm btn-success"
                      onClick={() => updateStmt.mutate({
                        id: detail.id,
                        data: { status: 'paid', paid_date: new Date().toISOString().slice(0, 10) }
                      })}>
                      标记结清
                    </button>
                  )}
                  {detail.status === 'issued' && (
                    <button className="btn btn-sm btn-danger"
                      onClick={() => updateStmt.mutate({ id: detail.id, data: { status: 'overdue' } })}>
                      标记逾期
                    </button>
                  )}
                  {!detail.due_date && (
                    <DueDatePicker stmtId={detail.id} onSet={(d) =>
                      updateStmt.mutate({ id: detail.id, data: { due_date: d } })
                    } />
                  )}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDetailId(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DueDatePicker({ onSet }: { stmtId: number; onSet: (d: string) => void }) {
  const [date, setDate] = useState('');
  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <input type="date" className="form-control" style={{ width: 160, padding: '4px 8px' }}
        value={date} onChange={e => setDate(e.target.value)} />
      <button className="btn btn-sm btn-secondary" disabled={!date}
        onClick={() => onSet(date)}>
        设置到期日
      </button>
    </div>
  );
}
