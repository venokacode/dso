import { useEffect, useState } from "react";
import {
  Table, Button, Modal, Select, DatePicker, Space, Tag, message, Popconfirm, InputNumber, Form,
} from "antd";
import { DownloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { invoiceApi, customerApi, fen2yuan } from "../services/api";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "default" },
  confirmed: { label: "已确认", color: "blue" },
  paid: { label: "已付款", color: "green" },
};

export default function Invoices() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState<any[]>([]);
  const [genOpen, setGenOpen] = useState(false);
  const [genForm] = Form.useForm();
  const [filters, setFilters] = useState<Record<string, any>>({});

  const load = () => {
    setLoading(true);
    invoiceApi.list(filters).then((r) => {
      setData(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [filters]);
  useEffect(() => { customerApi.listAll().then((r) => setCustomers(r.data)); }, []);

  const handleGenerate = async () => {
    const values = await genForm.validateFields();
    const r = await invoiceApi.generate(values.year, values.month);
    message.success(`生成完成：新建 ${r.data.created}，更新 ${r.data.updated}`);
    setGenOpen(false);
    load();
  };

  const handleConfirm = async (id: number) => {
    await invoiceApi.update(id, { status: "confirmed" });
    message.success("已确认");
    load();
  };

  const handlePaid = async (id: number) => {
    await invoiceApi.update(id, { status: "paid" });
    message.success("已标记付款");
    load();
  };

  const columns = [
    { title: "账单编号", dataIndex: "invoice_no", width: 180 },
    { title: "客户", dataIndex: "customer_name", width: 160 },
    { title: "年", dataIndex: "year", width: 80 },
    { title: "月", dataIndex: "month", width: 60 },
    { title: "订单数", dataIndex: "order_count", width: 80 },
    {
      title: "总金额（元）",
      dataIndex: "total_amount",
      width: 130,
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
      width: 280,
      render: (_: any, record: any) => (
        <Space size="small" wrap>
          {record.status === "draft" && (
            <Popconfirm title="确认此账单？" onConfirm={() => handleConfirm(record.id)}>
              <Button size="small">确认</Button>
            </Popconfirm>
          )}
          {record.status === "confirmed" && (
            <Popconfirm title="标记为已付款？" onConfirm={() => handlePaid(record.id)}>
              <Button size="small" type="primary">标记付款</Button>
            </Popconfirm>
          )}
          <Button
            size="small"
            icon={<DownloadOutlined />}
            href={invoiceApi.exportUrl(record.id)}
          >
            导出 Excel
          </Button>
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
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={() => {
          genForm.setFieldsValue({ year: dayjs().year(), month: dayjs().month() + 1 });
          setGenOpen(true);
        }}>
          生成月结账单
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

      <Modal
        title="生成月结账单"
        open={genOpen}
        onOk={handleGenerate}
        onCancel={() => setGenOpen(false)}
        destroyOnClose
      >
        <Form form={genForm} layout="vertical">
          <Form.Item name="year" label="年份" rules={[{ required: true }]}>
            <InputNumber min={2020} max={2099} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="month" label="月份" rules={[{ required: true }]}>
            <InputNumber min={1} max={12} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
        <p style={{ color: "#888" }}>
          将汇总该月所有已确认/已发货/已完成的订单，按客户生成月结账单。
        </p>
      </Modal>
    </div>
  );
}
