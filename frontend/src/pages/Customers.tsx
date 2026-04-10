import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCustomers, createCustomer, updateCustomer } from '../api';
import type { Customer } from '../types';
import { CustomerStatusBadge } from '../components/StatusBadge';

interface FormData {
  code: string;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  credit_limit: string;
  payment_terms_days: string;
  status: string;
  notes: string;
}

const EMPTY: FormData = {
  code: '', name: '', contact_person: '', email: '', phone: '',
  address: '', credit_limit: '0', payment_terms_days: '30',
  status: 'active', notes: '',
};

export default function Customers() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY);
  const [error, setError] = useState('');

  const { data: customers = [], isLoading } = useQuery<Customer[]>({
    queryKey: ['customers'],
    queryFn: () => getCustomers(),
  });

  const save = useMutation({
    mutationFn: (d: object) => editing
      ? updateCustomer(editing.id, d)
      : createCustomer(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] });
      setShowModal(false);
    },
    onError: (e: any) => setError(e.response?.data?.detail || '保存失败'),
  });

  function openCreate() {
    setEditing(null);
    setForm(EMPTY);
    setError('');
    setShowModal(true);
  }

  function openEdit(c: Customer) {
    setEditing(c);
    setForm({
      code: c.code,
      name: c.name,
      contact_person: c.contact_person ?? '',
      email: c.email ?? '',
      phone: c.phone ?? '',
      address: c.address ?? '',
      credit_limit: c.credit_limit,
      payment_terms_days: String(c.payment_terms_days),
      status: c.status,
      notes: c.notes ?? '',
    });
    setError('');
    setShowModal(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    save.mutate({
      ...form,
      credit_limit: parseFloat(form.credit_limit) || 0,
      payment_terms_days: parseInt(form.payment_terms_days) || 30,
    });
  }

  const filtered = customers.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="toolbar">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            placeholder="搜索客户名称或编号..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="toolbar-spacer" />
        <button className="btn btn-primary" onClick={openCreate}>+ 新增客户</button>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading ? (
            <div className="loading">加载中...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <h3>暂无客户</h3>
              <p>点击右上角「新增客户」添加第一个大客户</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>客户编号</th>
                  <th>客户名称</th>
                  <th>联系人</th>
                  <th>电话</th>
                  <th>授信额度</th>
                  <th>账期（天）</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => (
                  <tr key={c.id}>
                    <td className="font-mono fw-600">{c.code}</td>
                    <td className="fw-600">{c.name}</td>
                    <td>{c.contact_person || '—'}</td>
                    <td>{c.phone || '—'}</td>
                    <td className="text-right">¥{parseFloat(c.credit_limit).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</td>
                    <td className="text-center">{c.payment_terms_days}</td>
                    <td><CustomerStatusBadge status={c.status} /></td>
                    <td>
                      <button className="btn btn-sm btn-ghost" onClick={() => openEdit(c)}>编辑</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">{editing ? '编辑客户' : '新增客户'}</span>
              <button className="btn-icon" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}
                <div className="form-grid">
                  <div className="form-group">
                    <label>客户编号 *</label>
                    <input className="form-control" required value={form.code}
                      onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                      disabled={!!editing} placeholder="如 DSO001" />
                  </div>
                  <div className="form-group">
                    <label>客户名称 *</label>
                    <input className="form-control" required value={form.name}
                      onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>联系人</label>
                    <input className="form-control" value={form.contact_person}
                      onChange={e => setForm(f => ({ ...f, contact_person: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>电话</label>
                    <input className="form-control" value={form.phone}
                      onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>邮箱</label>
                    <input className="form-control" type="email" value={form.email}
                      onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>状态</label>
                    <select className="form-control" value={form.status}
                      onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
                      <option value="active">正常</option>
                      <option value="inactive">停用</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>授信额度（元）</label>
                    <input className="form-control" type="number" min="0" value={form.credit_limit}
                      onChange={e => setForm(f => ({ ...f, credit_limit: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>账期（天）</label>
                    <input className="form-control" type="number" min="1" value={form.payment_terms_days}
                      onChange={e => setForm(f => ({ ...f, payment_terms_days: e.target.value }))} />
                  </div>
                  <div className="form-group full">
                    <label>地址</label>
                    <input className="form-control" value={form.address}
                      onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
                  </div>
                  <div className="form-group full">
                    <label>备注</label>
                    <textarea className="form-control" value={form.notes}
                      onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>取消</button>
                <button type="submit" className="btn btn-primary" disabled={save.isPending}>
                  {save.isPending ? '保存中...' : '保存'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
