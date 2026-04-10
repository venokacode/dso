import { useEffect, useState } from "react";
import {
  Table, Button, Modal, Form, Input, InputNumber, Select, DatePicker, Space,
  Tag, message, Popconfirm, Divider,
} from "antd";
import { PlusOutlined, DeleteOutlined, EyeOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { orderApi, customerApi, productApi, fen2yuan } from "../services/api";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: "待确认", color: "default" },
  confirmed: { label: "已确认", color: "blue" },
  shipped: { label: "已发货", color: "orange" },
  completed: { label: "已完成", color: "green" },
  cancelled: { label: "已取消", color: "red" },
};

const NEXT_ACTIONS: Record<string, { label: string; status: string }[]> = {
  pending: [
    { label: "确认订单", status: "confirmed" },
    { label: "取消订单", status: "cancelled" },
  ],
  confirmed: [
    { label: "标记发货", status: "shipped" },
    { label: "取消订单", status: "cancelled" },
  ],
  shipped: [{ label: "标记完成", status: "completed" }],
  completed: [],
  cancelled: [],
};

export default function Orders() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<any>(null);
  const [customers, setCustomers] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [form] = Form.useForm();
  const [filters, setFilters] = useState<Record<string, any>>({});

  const load = () => {
    setLoading(true);
    orderApi.list(filters).then((r) => {
      setData(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [filters]);

  useEffect(() => {
    customerApi.listAll().then((r) => setCustomers(r.data));
    productApi.listAll().then((r) => setProducts(r.data));
  }, []);

  const openCreate = () => {
    form.resetFields();
    form.setFieldsValue({ order_date: dayjs(), items: [{}] });
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    const values = await form.validateFields();
    const payload = {
      customer_id: values.customer_id,
      order_date: values.order_date.format("YYYY-MM-DD"),
      notes: values.notes,
      items: (values.items || []).map((it: any) => ({
        product_id: it.product_id,
        quantity: it.quantity,
      })),
    };
    await orderApi.create(payload);
    message.success("订单创建成功");
    setCreateOpen(false);
    load();
  };

  const showDetail = async (id: number) => {
    const r = await orderApi.get(id);
    setDetail(r.data);
    setDetailOpen(true);
  };

  const changeStatus = async (id: number, status: string) => {
    await orderApi.update(id, { status });
    message.success("状态已更新");
    load();
    if (detail?.id === id) {
      const r = await orderApi.get(id);
      setDetail(r.data);
    }
  };

  const handleDeleteOrder = async (id: number) => {
    await orderApi.delete(id);
    message.success("订单已删除");
    load();
  };

  const columns = [
    { title: "订单编号", dataIndex: "order_no", width: 200 },
    { title: "客户", dataIndex: "customer_name", width: 160 },
    { title: "日期", dataIndex: "order_date", width: 120 },
    {
      title: "金额（元）",
      dataIndex: "total_amount",
      width: 120,
      render: (v: number) => fen2yuan(v),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 100,
      render: (s: string) => {
        const m = STATUS_MAP[s];
        return <Tag color={m?.color}>{m?.label || s}</Tag>;
      },
    },
    {
      title: "操作",
      width: 260,
      render: (_: any, record: any) => (
        <Space size="small" wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => showDetail(record.id)}>
            详情
          </Button>
          {NEXT_ACTIONS[record.status]?.map((a) => (
            <Popconfirm key={a.status} title={`确认${a.label}？`} onConfirm={() => changeStatus(record.id, a.status)}>
              <Button size="small">{a.label}</Button>
            </Popconfirm>
          ))}
          {(record.status === "pending" || record.status === "cancelled") && (
            <Popconfirm title="确认删除？" onConfirm={() => handleDeleteOrder(record.id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 8 }}>
        <Space wrap>
          <Select
            placeholder="筛选客户"
            allowClear
            style={{ width: 180 }}
            onChange={(v) => setFilters((f) => ({ ...f, customer_id: v }))}
            options={customers.map((c: any) => ({ label: c.name, value: c.id }))}
          />
          <Select
            placeholder="筛选状态"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setFilters((f) => ({ ...f, status: v }))}
            options={Object.entries(STATUS_MAP).map(([k, v]) => ({ label: v.label, value: k }))}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建订单
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{ pageSize: 20 }}
        size="middle"
      />

      {/* Create order modal */}
      <Modal
        title="新建订单"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
        width={700}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="customer_id" label="客户" rules={[{ required: true, message: "请选择客户" }]}>
            <Select
              showSearch
              placeholder="选择客户"
              optionFilterProp="label"
              options={customers.map((c: any) => ({ label: `${c.name} (${c.code})`, value: c.id }))}
            />
          </Form.Item>
          <Form.Item name="order_date" label="订单日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Divider>订单明细</Divider>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name }) => (
                  <Space key={key} align="start" style={{ display: "flex", marginBottom: 8 }}>
                    <Form.Item name={[name, "product_id"]} rules={[{ required: true, message: "选择产品" }]}>
                      <Select
                        showSearch
                        placeholder="选择产品"
                        optionFilterProp="label"
                        style={{ width: 300 }}
                        options={products.map((p: any) => ({
                          label: `${p.name} (${p.code}) - ¥${fen2yuan(p.unit_price)}/${p.unit}`,
                          value: p.id,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item name={[name, "quantity"]} rules={[{ required: true, message: "输入数量" }]}>
                      <InputNumber min={1} placeholder="数量" style={{ width: 120 }} />
                    </Form.Item>
                    <Button danger onClick={() => remove(name)} icon={<DeleteOutlined />} />
                  </Space>
                ))}
                <Button type="dashed" block onClick={() => add()} icon={<PlusOutlined />}>
                  添加明细
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>

      {/* Order detail modal */}
      <Modal
        title={`订单详情 - ${detail?.order_no || ""}`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={700}
      >
        {detail && (
          <div>
            <p><strong>客户：</strong>{detail.customer_name}</p>
            <p><strong>日期：</strong>{detail.order_date}</p>
            <p><strong>状态：</strong><Tag color={STATUS_MAP[detail.status]?.color}>{STATUS_MAP[detail.status]?.label}</Tag></p>
            <p><strong>总金额：</strong>¥{fen2yuan(detail.total_amount)}</p>
            {detail.notes && <p><strong>备注：</strong>{detail.notes}</p>}
            <Table
              rowKey="id"
              size="small"
              pagination={false}
              dataSource={detail.items}
              columns={[
                { title: "产品", dataIndex: "product_name" },
                { title: "编码", dataIndex: "product_code" },
                { title: "单位", dataIndex: "unit" },
                { title: "单价（元）", dataIndex: "unit_price", render: (v: number) => fen2yuan(v) },
                { title: "数量", dataIndex: "quantity" },
                { title: "小计（元）", dataIndex: "amount", render: (v: number) => fen2yuan(v) },
              ]}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
