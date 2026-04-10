import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProducts, createProduct, updateProduct } from '../api';
import type { Product } from '../types';

interface FormData {
  sku: string;
  name: string;
  description: string;
  unit: string;
  unit_price: string;
  is_active: boolean;
}

const EMPTY: FormData = {
  sku: '', name: '', description: '', unit: '件', unit_price: '', is_active: true,
};

export default function Products() {
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY);
  const [error, setError] = useState('');

  const { data: products = [], isLoading } = useQuery<Product[]>({
    queryKey: ['products'],
    queryFn: () => getProducts(),
  });

  const save = useMutation({
    mutationFn: (d: object) => editing
      ? updateProduct(editing.id, d)
      : createProduct(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] });
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

  function openEdit(p: Product) {
    setEditing(p);
    setForm({
      sku: p.sku,
      name: p.name,
      description: p.description ?? '',
      unit: p.unit,
      unit_price: p.unit_price,
      is_active: p.is_active,
    });
    setError('');
    setShowModal(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    save.mutate({
      ...form,
      unit_price: parseFloat(form.unit_price),
    });
  }

  const filtered = products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.sku.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="toolbar">
        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            placeholder="搜索产品名称或SKU..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="toolbar-spacer" />
        <button className="btn btn-primary" onClick={openCreate}>+ 新增产品</button>
      </div>

      <div className="card">
        <div className="table-wrap">
          {isLoading ? (
            <div className="loading">加载中...</div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <h3>暂无产品</h3>
              <p>点击右上角「新增产品」添加产品</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>产品名称</th>
                  <th>单位</th>
                  <th>单价</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id}>
                    <td className="font-mono fw-600">{p.sku}</td>
                    <td className="fw-600">{p.name}</td>
                    <td>{p.unit}</td>
                    <td className="text-right fw-600">
                      ¥{parseFloat(p.unit_price).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span className={`badge ${p.is_active ? 'badge-green' : 'badge-gray'}`}>
                        {p.is_active ? '在售' : '停售'}
                      </span>
                    </td>
                    <td>
                      <button className="btn btn-sm btn-ghost" onClick={() => openEdit(p)}>编辑</button>
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
              <span className="modal-title">{editing ? '编辑产品' : '新增产品'}</span>
              <button className="btn-icon" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {error && <div className="alert alert-danger">{error}</div>}
                <div className="form-grid">
                  <div className="form-group">
                    <label>SKU *</label>
                    <input className="form-control" required value={form.sku}
                      onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                      disabled={!!editing} placeholder="如 PRD001" />
                  </div>
                  <div className="form-group">
                    <label>产品名称 *</label>
                    <input className="form-control" required value={form.name}
                      onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>单价（元）*</label>
                    <input className="form-control" type="number" min="0" step="0.01" required
                      value={form.unit_price}
                      onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>单位</label>
                    <input className="form-control" value={form.unit}
                      onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} />
                  </div>
                  <div className="form-group full">
                    <label>描述</label>
                    <textarea className="form-control" value={form.description}
                      onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                  </div>
                  <div className="form-group">
                    <label>状态</label>
                    <select className="form-control" value={form.is_active ? 'true' : 'false'}
                      onChange={e => setForm(f => ({ ...f, is_active: e.target.value === 'true' }))}>
                      <option value="true">在售</option>
                      <option value="false">停售</option>
                    </select>
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
