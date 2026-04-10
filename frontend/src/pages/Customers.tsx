import { useEffect, useState } from "react";
import {
  Table, Button, Modal, Form, Input, InputNumber, Space, Tag, message, Popconfirm,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined } from "@ant-design/icons";
import { customerApi, fen2yuan } from "../services/api";

export default function Customers() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();
  const [keyword, setKeyword] = useState("");

  const load = () => {
    setLoading(true);
    customerApi.list({ keyword }).then((r) => {
      setData(r.data);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, [keyword]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ payment_terms: 30, credit_limit: 0 });
    setModalOpen(true);
  };

  const openEdit = (record: any) => {
    setEditing(record);
    form.setFieldsValue({
      ...record,
      credit_limit: record.credit_limit / 100,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = { ...values, credit_limit: Math.round((values.credit_limit || 0) * 100) };
    if (editing) {
      await customerApi.update(editing.id, payload);
      message.success("更新成功");
    } else {
      await customerApi.create(payload);
      message.success("创建成功");
    }
    setModalOpen(false);
    load();
  };

  const handleDelete = async (id: number) => {
    await customerApi.delete(id);
    message.success("已停用");
    load();
  };

  const columns = [
    { title: "编码", dataIndex: "code", width: 120 },
    { title: "客户名称", dataIndex: "name" },
    { title: "联系人", dataIndex: "contact_person", width: 120 },
    { title: "电话", dataIndex: "phone", width: 140 },
    { title: "账期（天）", dataIndex: "payment_terms", width: 100 },
    {
      title: "信用额度（元）",
      dataIndex: "credit_limit",
      width: 130,
      render: (v: number) => fen2yuan(v),
    },
    {
      title: "状态",
      dataIndex: "is_active",
      width: 80,
      render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="red">停用</Tag>,
    },
    {
      title: "操作",
      width: 140,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Popconfirm title="确认停用？" onConfirm={() => handleDelete(record.id)}>
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
          placeholder="搜索客户名称/编码"
          style={{ width: 300 }}
          onSearch={setKeyword}
          allowClear
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增客户
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
        title={editing ? "编辑客户" : "新增客户"}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          {!editing && (
            <Form.Item name="code" label="客户编码" rules={[{ required: true }]}>
              <Input placeholder="如 DSO-001" />
            </Form.Item>
          )}
          <Form.Item name="name" label="客户名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_person" label="联系人">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="电话">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="address" label="地址">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="payment_terms" label="账期（天）">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="credit_limit" label="信用额度（元）">
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
