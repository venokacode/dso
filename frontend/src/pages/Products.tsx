import { useEffect, useState } from "react";
import {
  Table, Button, Modal, Form, Input, InputNumber, Space, Tag, message, Popconfirm,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { productApi, fen2yuan } from "../services/api";

export default function Products() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();
  const [keyword, setKeyword] = useState("");

  const load = () => {
    setLoading(true);
    productApi.list({ keyword }).then((r) => {
      setData(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [keyword]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ unit: "件" });
    setModalOpen(true);
  };

  const openEdit = (record: any) => {
    setEditing(record);
    form.setFieldsValue({ ...record, unit_price: record.unit_price / 100 });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = { ...values, unit_price: Math.round((values.unit_price || 0) * 100) };
    if (editing) {
      await productApi.update(editing.id, payload);
      message.success("更新成功");
    } else {
      await productApi.create(payload);
      message.success("创建成功");
    }
    setModalOpen(false);
    load();
  };

  const handleDelete = async (id: number) => {
    await productApi.delete(id);
    message.success("已停用");
    load();
  };

  const columns = [
    { title: "编码", dataIndex: "code", width: 120 },
    { title: "产品名称", dataIndex: "name" },
    { title: "单位", dataIndex: "unit", width: 80 },
    {
      title: "单价（元）",
      dataIndex: "unit_price",
      width: 120,
      render: (v: number) => fen2yuan(v),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (v: boolean) => v ? <Tag color="green">在售</Tag> : <Tag color="red">停售</Tag>,
    },
    {
      title: "操作",
      width: 140,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确认停售？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Input.Search
          placeholder="搜索产品名称/编码"
          style={{ width: 300 }}
          onSearch={setKeyword}
          allowClear
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增产品
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
        title={editing ? "编辑产品" : "新增产品"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={500}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <Form.Item name="code" label="产品编码" rules={[{ required: true }]}>
              <Input placeholder="如 PRD-001" />
            </Form.Item>
          )}
          <Form.Item name="name" label="产品名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Input />
          </Form.Item>
          <Form.Item name="unit_price" label="单价（元）" rules={[{ required: true }]}>
            <InputNumber min={0} step={0.01} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
