const STORAGE_KEY = "dso-order-system-state-v1";
const EMPTY_OPTION = '<option value="">请先创建客户</option>';

const elements = {
  dashboardMonth: document.querySelector("#dashboard-month"),
  dashboardCards: document.querySelector("#dashboard-cards"),
  dashboardHighlights: document.querySelector("#dashboard-highlights"),
  customerForm: document.querySelector("#customer-form"),
  customerTableBody: document.querySelector("#customer-table-body"),
  orderForm: document.querySelector("#order-form"),
  orderCustomerSelect: document.querySelector("#order-customer-select"),
  orderItemsBody: document.querySelector("#order-items-body"),
  orderItemTemplate: document.querySelector("#order-item-row-template"),
  addItemButton: document.querySelector("#add-item-button"),
  orderTotalHint: document.querySelector("#order-total-hint"),
  orderFilterCustomer: document.querySelector("#order-filter-customer"),
  orderFilterStatus: document.querySelector("#order-filter-status"),
  orderFilterMonth: document.querySelector("#order-filter-month"),
  orderTableBody: document.querySelector("#order-table-body"),
  settlementFilterMonth: document.querySelector("#settlement-filter-month"),
  settlementTableBody: document.querySelector("#settlement-table-body"),
  settlementForm: document.querySelector("#settlement-form"),
  settlementKey: document.querySelector("#settlement-key"),
  settlementStatus: document.querySelector("#settlement-status"),
  settlementInvoiceNo: document.querySelector("#settlement-invoice-no"),
  settlementDueDate: document.querySelector("#settlement-due-date"),
  settlementRemark: document.querySelector("#settlement-remark"),
  statementTitle: document.querySelector("#statement-title"),
  statementEmpty: document.querySelector("#statement-empty"),
  statementContent: document.querySelector("#statement-content"),
  statementMetrics: document.querySelector("#statement-metrics"),
  statementOrderBody: document.querySelector("#statement-order-body"),
  seedDemoButton: document.querySelector("#seed-demo-button"),
  clearDataButton: document.querySelector("#clear-data-button")
};

let selectedSettlementKey = "";
let state = loadState();

initialize();

function initialize() {
  const month = currentMonth();
  elements.dashboardMonth.value = month;
  elements.orderFilterMonth.value = month;
  elements.settlementFilterMonth.value = month;

  bindEvents();
  ensureAtLeastOneOrderRow();
  populateOrderDefaults();
  renderAll();
}

function bindEvents() {
  elements.customerForm.addEventListener("submit", handleCustomerSubmit);
  elements.orderForm.addEventListener("submit", handleOrderSubmit);
  elements.addItemButton.addEventListener("click", () => addOrderItemRow());
  elements.orderItemsBody.addEventListener("click", handleOrderItemActions);
  elements.orderItemsBody.addEventListener("input", updateOrderTotalHint);
  elements.orderFilterCustomer.addEventListener("change", renderOrders);
  elements.orderFilterStatus.addEventListener("change", renderOrders);
  elements.orderFilterMonth.addEventListener("change", renderOrders);
  elements.dashboardMonth.addEventListener("change", renderDashboard);
  elements.settlementFilterMonth.addEventListener("change", renderSettlements);
  elements.orderTableBody.addEventListener("change", handleOrderStatusChange);
  elements.settlementTableBody.addEventListener("click", handleSettlementSelection);
  elements.settlementForm.addEventListener("submit", handleSettlementSave);
  elements.seedDemoButton.addEventListener("click", handleSeedDemo);
  elements.clearDataButton.addEventListener("click", handleClearData);
}

function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return seedDemoState();
  }

  try {
    return normalizeState(JSON.parse(raw));
  } catch (error) {
    console.warn("Failed to parse local state, using demo data.", error);
    return seedDemoState();
  }
}

function normalizeState(raw) {
  const normalized = {
    customers: Array.isArray(raw.customers) ? raw.customers : [],
    orders: Array.isArray(raw.orders) ? raw.orders : [],
    settlementRecords: raw.settlementRecords && typeof raw.settlementRecords === "object"
      ? raw.settlementRecords
      : {}
  };

  normalized.orders = normalized.orders.map((order, index) => {
    const items = Array.isArray(order.items) ? order.items : [];
    const totals = calculateOrderTotals(items);
    return {
      ...order,
      id: order.id || uid(`order-${index}`),
      orderNo: order.orderNo || createOrderNo(order.orderDate || todayISO(), index + 1),
      items,
      subtotalAmount: totals.subtotalAmount,
      taxAmount: totals.taxAmount,
      totalAmount: totals.totalAmount,
      settlementMonth: order.settlementMonth || toMonth(order.orderDate || todayISO()),
      createdAt: order.createdAt || new Date().toISOString()
    };
  });

  return normalized;
}

function seedDemoState() {
  const customerA = {
    id: uid("customer"),
    name: "华东口腔集团",
    code: "DSO-001",
    contact: "张老师",
    phone: "13800001111",
    creditDays: 30,
    settlementDay: 25,
    creditLimit: 500000,
    invoiceTitle: "华东口腔医疗管理有限公司",
    address: "上海市静安区南京西路 100 号",
    remark: "要求订单必须带客户 PO 号，对账单按院区汇总。"
  };

  const customerB = {
    id: uid("customer"),
    name: "京津齿科连锁",
    code: "DSO-002",
    contact: "王经理",
    phone: "13900002222",
    creditDays: 45,
    settlementDay: 28,
    creditLimit: 320000,
    invoiceTitle: "北京京津齿科管理集团有限公司",
    address: "北京市朝阳区建国路 66 号",
    remark: "需要单独标记耗材批次。"
  };

  const customerC = {
    id: uid("customer"),
    name: "南方儿牙中心",
    code: "DSO-003",
    contact: "林医生",
    phone: "13700003333",
    creditDays: 60,
    settlementDay: 20,
    creditLimit: 180000,
    invoiceTitle: "广州南方儿牙医疗有限公司",
    address: "广州市天河区体育东路 88 号",
    remark: "每月 20 日锁账，月末统一开票。"
  };

  const orders = [
    buildOrder(customerA.id, {
      orderNo: "SO-202604-001",
      poNumber: "PO-HD-240401",
      department: "上海旗舰院",
      orderDate: shiftDate(todayISO(), -5),
      deliveryDate: shiftDate(todayISO(), 2),
      status: "待履约",
      notes: "需分两次送达。",
      items: [
        { sku: "IMPL-1001", name: "种植体套装", spec: "4.1*10mm", quantity: 12, unit: "套", price: 980, taxRate: 13 },
        { sku: "SURG-2002", name: "骨粉", spec: "0.5g", quantity: 20, unit: "盒", price: 320, taxRate: 13 }
      ]
    }),
    buildOrder(customerA.id, {
      orderNo: "SO-202604-002",
      poNumber: "PO-HD-240403",
      department: "杭州院区",
      orderDate: shiftDate(todayISO(), -2),
      deliveryDate: shiftDate(todayISO(), 4),
      status: "待审核",
      notes: "PO 由集团统一结算。",
      items: [
        { sku: "ORTH-3001", name: "矫治附件包", spec: "标准版", quantity: 18, unit: "套", price: 160, taxRate: 13 }
      ]
    }),
    buildOrder(customerB.id, {
      orderNo: "SO-202603-018",
      poNumber: "PO-JJ-240326",
      department: "北京望京院",
      orderDate: shiftDate(todayISO(), -18),
      deliveryDate: shiftDate(todayISO(), -14),
      status: "已完成",
      notes: "附带耗材批次记录。",
      items: [
        { sku: "DISP-8888", name: "一次性口腔包", spec: "成人", quantity: 150, unit: "包", price: 19.5, taxRate: 13 },
        { sku: "STER-1010", name: "灭菌盒", spec: "中号", quantity: 12, unit: "个", price: 86, taxRate: 13 }
      ]
    }),
    buildOrder(customerC.id, {
      orderNo: "SO-202603-021",
      poNumber: "PO-NF-240329",
      department: "广州天河院",
      orderDate: shiftDate(todayISO(), -12),
      deliveryDate: shiftDate(todayISO(), -7),
      status: "履约中",
      notes: "儿牙项目专用耗材。",
      items: [
        { sku: "PED-5001", name: "乳牙冠修复包", spec: "儿童", quantity: 24, unit: "盒", price: 245, taxRate: 13 }
      ]
    })
  ];

  const settlementRecords = {};
  orders.forEach((order) => {
    const customer = [customerA, customerB, customerC].find((item) => item.id === order.customerId);
    const key = settlementKey(order.customerId, order.settlementMonth);
    if (!settlementRecords[key]) {
      settlementRecords[key] = {
        status: order.status === "已完成" ? "已开票" : "待开票",
        invoiceNo: order.status === "已完成" ? `INV-${order.settlementMonth.replace("-", "")}-${order.orderNo.slice(-3)}` : "",
        dueDate: defaultDueDate(order.settlementMonth, customer?.creditDays || 30),
        remark: customer?.remark || ""
      };
    }
  });

  return {
    customers: [customerA, customerB, customerC],
    orders,
    settlementRecords
  };
}

function renderAll() {
  renderCustomerOptions();
  renderCustomers();
  renderDashboard();
  renderOrders();
  renderSettlements();
  updateOrderTotalHint();
  saveState();
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function renderCustomerOptions() {
  const currentOrderCustomer = elements.orderCustomerSelect.value;
  const currentOrderFilterCustomer = elements.orderFilterCustomer.value || "全部";
  const options = state.customers.map((customer) => (
    `<option value="${customer.id}">${escapeHtml(customer.name)} (${escapeHtml(customer.code)})</option>`
  )).join("");

  elements.orderCustomerSelect.innerHTML = options || EMPTY_OPTION;
  elements.orderFilterCustomer.innerHTML = `<option value="全部">全部客户</option>${options}`;

  if (state.customers.length === 0) {
    elements.orderCustomerSelect.innerHTML = EMPTY_OPTION;
    elements.orderFilterCustomer.value = "全部";
    return;
  }

  const hasSelectedCustomer = state.customers.some((customer) => customer.id === currentOrderCustomer);
  const hasSelectedFilterCustomer = currentOrderFilterCustomer === "全部"
    || state.customers.some((customer) => customer.id === currentOrderFilterCustomer);

  elements.orderCustomerSelect.value = hasSelectedCustomer ? currentOrderCustomer : state.customers[0].id;
  elements.orderFilterCustomer.value = hasSelectedFilterCustomer ? currentOrderFilterCustomer : "全部";
}

function renderCustomers() {
  if (state.customers.length === 0) {
    elements.customerTableBody.innerHTML = '<tr><td colspan="6" class="muted-text">暂无客户，请先创建 DSO 客户档案。</td></tr>';
    return;
  }

  const outstandingByCustomer = aggregateSettlements().reduce((acc, group) => {
    if (group.record.status !== "已回款") {
      acc[group.customerId] = (acc[group.customerId] || 0) + group.totalAmount;
    }
    return acc;
  }, {});

  elements.customerTableBody.innerHTML = state.customers.map((customer) => `
    <tr>
      <td>
        <div class="customer-meta">
          <strong>${escapeHtml(customer.name)}</strong>
          <small>${escapeHtml(customer.code)} / ${escapeHtml(customer.invoiceTitle || "-")}</small>
        </div>
      </td>
      <td>${escapeHtml(customer.contact || "-")}<br><small>${escapeHtml(customer.phone || "-")}</small></td>
      <td>月结 ${customer.creditDays} 天</td>
      <td>
        ${formatCurrency(Number(customer.creditLimit || 0))}
        <br>
        <small>在途应收 ${formatCurrency(outstandingByCustomer[customer.id] || 0)}</small>
      </td>
      <td>每月 ${customer.settlementDay} 日</td>
      <td>${escapeHtml(customer.remark || "-")}</td>
    </tr>
  `).join("");
}

function renderDashboard() {
  const month = elements.dashboardMonth.value || currentMonth();
  const orders = state.orders.filter((order) => order.settlementMonth === month);
  const activeSettlements = aggregateSettlements().filter((group) => group.month === month);
  const unpaidAmount = activeSettlements
    .filter((group) => group.record.status !== "已回款")
    .reduce((sum, group) => sum + group.totalAmount, 0);
  const pendingFulfillment = state.orders.filter((order) => order.status !== "已完成").length;
  const averageOrder = orders.length
    ? orders.reduce((sum, order) => sum + order.totalAmount, 0) / orders.length
    : 0;

  const cards = [
    { label: "大客户数", value: state.customers.length, hint: "已建档 DSO 客户" },
    { label: `${month} 订单数`, value: orders.length, hint: "按结算月份统计" },
    { label: `${month} 含税订单额`, value: formatCurrency(orders.reduce((sum, order) => sum + order.totalAmount, 0)), hint: `客单价 ${formatCurrency(averageOrder)}` },
    { label: "待履约订单", value: pendingFulfillment, hint: "未完成的订单条数" },
    { label: `${month} 待回款`, value: formatCurrency(unpaidAmount), hint: "未标记为已回款的月结记录" }
  ];

  elements.dashboardCards.innerHTML = cards.map((card) => `
    <article class="stat-card">
      <p>${escapeHtml(card.label)}</p>
      <strong>${card.value}</strong>
      <span class="muted-text">${escapeHtml(card.hint)}</span>
    </article>
  `).join("");

  const topCustomer = rankCustomerByMonth(month);
  const highlights = [
    topCustomer
      ? `${month} 订单额最高客户：${topCustomer.name}，累计 ${formatCurrency(topCustomer.total)}。`
      : `${month} 还没有订单，可以先为客户创建 PO 订单。`,
    pendingFulfillment > 0
      ? `当前仍有 ${pendingFulfillment} 张订单未完成，适合在履约节点后更新状态，便于月末对账。`
      : "当前订单均已履约完成，可直接进入月结与开票阶段。",
    unpaidAmount > 0
      ? `本月尚有 ${formatCurrency(unpaidAmount)} 待回款，可在右侧月结中心维护发票号和回款日期。`
      : "本月月结记录均已回款，账期风险较低。"
  ];

  elements.dashboardHighlights.innerHTML = highlights.map((item) => `
    <div class="highlight-item">${escapeHtml(item)}</div>
  `).join("");
}

function renderOrders() {
  const customerFilter = elements.orderFilterCustomer.value || "全部";
  const statusFilter = elements.orderFilterStatus.value || "全部";
  const monthFilter = elements.orderFilterMonth.value || "";

  const filtered = state.orders.filter((order) => {
    const matchesCustomer = customerFilter === "全部" || order.customerId === customerFilter;
    const matchesStatus = statusFilter === "全部" || order.status === statusFilter;
    const matchesMonth = !monthFilter || order.settlementMonth === monthFilter;
    return matchesCustomer && matchesStatus && matchesMonth;
  }).sort((left, right) => right.orderDate.localeCompare(left.orderDate));

  if (filtered.length === 0) {
    elements.orderTableBody.innerHTML = '<tr><td colspan="8" class="muted-text">当前筛选条件下没有订单。</td></tr>';
    return;
  }

  elements.orderTableBody.innerHTML = filtered.map((order) => {
    const customer = getCustomer(order.customerId);
    return `
      <tr>
        <td>
          <strong>${escapeHtml(order.orderNo)}</strong>
          <br>
          <small>${escapeHtml(order.settlementMonth)}</small>
        </td>
        <td>${escapeHtml(customer?.name || "未知客户")}</td>
        <td>${escapeHtml(order.poNumber)}</td>
        <td>${escapeHtml(order.department || "-")}</td>
        <td>${formatDate(order.orderDate)}</td>
        <td>${formatDate(order.deliveryDate)}</td>
        <td>
          ${formatCurrency(order.totalAmount)}
          <br>
          <small>共 ${order.items.length} 项</small>
        </td>
        <td>
          <select data-order-id="${order.id}">
            ${["待审核", "待履约", "履约中", "已完成"].map((status) => `
              <option value="${status}" ${order.status === status ? "selected" : ""}>${status}</option>
            `).join("")}
          </select>
        </td>
      </tr>
    `;
  }).join("");
}

function renderSettlements() {
  const monthFilter = elements.settlementFilterMonth.value || "";
  const groups = aggregateSettlements().filter((group) => !monthFilter || group.month === monthFilter);

  if (groups.length === 0) {
    elements.settlementTableBody.innerHTML = '<tr><td colspan="6" class="muted-text">当前月份没有月结记录，创建订单后会自动生成。</td></tr>';
    clearSettlementPreview();
    return;
  }

  if (!groups.some((group) => group.key === selectedSettlementKey)) {
    selectedSettlementKey = "";
  }

  elements.settlementTableBody.innerHTML = groups.map((group) => `
    <tr>
      <td>${escapeHtml(group.customerName)}</td>
      <td>${escapeHtml(group.month)}</td>
      <td>${group.orders.length}</td>
      <td>${formatCurrency(group.totalAmount)}</td>
      <td><span class="status-chip ${statusClass(group.record.status)}">${escapeHtml(group.record.status)}</span></td>
      <td>
        <button class="secondary-button table-action-button" type="button" data-settlement-key="${group.key}">
          查看对账单
        </button>
      </td>
    </tr>
  `).join("");

  if (selectedSettlementKey) {
    renderSettlementPreview(selectedSettlementKey);
  } else {
    clearSettlementPreview();
  }
}

function renderSettlementPreview(key) {
  const group = aggregateSettlements().find((item) => item.key === key);
  if (!group) {
    clearSettlementPreview();
    return;
  }

  const record = group.record;
  selectedSettlementKey = key;

  elements.statementTitle.textContent = `${group.customerName} / ${group.month}`;
  elements.statementEmpty.classList.add("hidden");
  elements.statementContent.classList.remove("hidden");
  elements.statementMetrics.innerHTML = [
    { label: "月结订单数", value: `${group.orders.length} 笔` },
    { label: "应收金额", value: formatCurrency(group.totalAmount) },
    { label: "结算状态", value: record.status },
    { label: "回款截止日", value: record.dueDate || "-" }
  ].map((metric) => `
    <div class="metric">
      <p>${escapeHtml(metric.label)}</p>
      <strong>${escapeHtml(metric.value)}</strong>
    </div>
  `).join("");

  elements.settlementKey.value = key;
  elements.settlementStatus.value = record.status;
  elements.settlementInvoiceNo.value = record.invoiceNo || "";
  elements.settlementDueDate.value = record.dueDate || "";
  elements.settlementRemark.value = record.remark || "";

  elements.statementOrderBody.innerHTML = group.orders.map((order) => `
    <tr>
      <td>${escapeHtml(order.orderNo)}</td>
      <td>${escapeHtml(order.poNumber)}</td>
      <td>${formatDate(order.orderDate)}</td>
      <td>${escapeHtml(order.department || "-")}</td>
      <td>${formatCurrency(order.totalAmount)}</td>
      <td><span class="status-chip ${statusClass(order.status)}">${escapeHtml(order.status)}</span></td>
    </tr>
  `).join("");
}

function clearSettlementPreview() {
  selectedSettlementKey = "";
  elements.statementTitle.textContent = "请选择左侧月结记录";
  elements.statementEmpty.classList.remove("hidden");
  elements.statementContent.classList.add("hidden");
  elements.settlementForm.reset();
  elements.settlementKey.value = "";
  elements.statementMetrics.innerHTML = "";
  elements.statementOrderBody.innerHTML = "";
}

function aggregateSettlements() {
  const groups = new Map();

  // Month-end reconciliation is derived from orders so finance can operate without a payment gateway.
  state.orders.forEach((order) => {
    const key = settlementKey(order.customerId, order.settlementMonth);
    const customer = getCustomer(order.customerId);
    const existing = groups.get(key);

    if (existing) {
      existing.orders.push(order);
      existing.totalAmount += order.totalAmount;
      return;
    }

    groups.set(key, {
      key,
      customerId: order.customerId,
      customerName: customer?.name || "未知客户",
      month: order.settlementMonth,
      orders: [order],
      totalAmount: order.totalAmount,
      record: ensureSettlementRecord(order.customerId, order.settlementMonth)
    });
  });

  return [...groups.values()].sort((left, right) => {
    if (left.month === right.month) {
      return left.customerName.localeCompare(right.customerName, "zh-CN");
    }
    return right.month.localeCompare(left.month);
  });
}

function ensureSettlementRecord(customerId, month) {
  const key = settlementKey(customerId, month);
  if (!state.settlementRecords[key]) {
    const customer = getCustomer(customerId);
    state.settlementRecords[key] = {
      status: "待开票",
      invoiceNo: "",
      dueDate: defaultDueDate(month, customer?.creditDays || 30),
      remark: customer?.remark || ""
    };
  }

  return state.settlementRecords[key];
}

function handleCustomerSubmit(event) {
  event.preventDefault();
  const formData = new FormData(elements.customerForm);
  const customer = {
    id: uid("customer"),
    name: formData.get("name").toString().trim(),
    code: formData.get("code").toString().trim(),
    contact: formData.get("contact").toString().trim(),
    phone: formData.get("phone").toString().trim(),
    creditDays: Number(formData.get("creditDays")),
    settlementDay: Number(formData.get("settlementDay")),
    creditLimit: Number(formData.get("creditLimit") || 0),
    invoiceTitle: formData.get("invoiceTitle").toString().trim(),
    address: formData.get("address").toString().trim(),
    remark: formData.get("remark").toString().trim()
  };

  state.customers.unshift(customer);
  elements.customerForm.reset();
  renderAll();
  elements.orderCustomerSelect.value = customer.id;
}

function handleOrderSubmit(event) {
  event.preventDefault();

  if (state.customers.length === 0) {
    window.alert("请先创建至少一个 DSO 客户。");
    return;
  }

  const formData = new FormData(elements.orderForm);
  const items = collectOrderItems();
  if (items.length === 0) {
    window.alert("请至少填写一行订单明细。");
    return;
  }

  const customerId = formData.get("customerId").toString();
  const orderDate = formData.get("orderDate").toString();
  const totals = calculateOrderTotals(items);
  const sameMonthCount = state.orders.filter((order) => order.settlementMonth === toMonth(orderDate)).length;

  state.orders.unshift({
    id: uid("order"),
    orderNo: createOrderNo(orderDate, sameMonthCount + 1),
    customerId,
    poNumber: formData.get("poNumber").toString().trim(),
    orderDate,
    deliveryDate: formData.get("deliveryDate").toString(),
    department: formData.get("department").toString().trim(),
    status: formData.get("status").toString(),
    notes: formData.get("notes").toString().trim(),
    settlementMonth: toMonth(orderDate),
    items,
    subtotalAmount: totals.subtotalAmount,
    taxAmount: totals.taxAmount,
    totalAmount: totals.totalAmount,
    createdAt: new Date().toISOString()
  });

  ensureSettlementRecord(customerId, toMonth(orderDate));
  elements.orderForm.reset();
  elements.orderItemsBody.innerHTML = "";
  addOrderItemRow();
  populateOrderDefaults();
  renderAll();
}

function handleOrderItemActions(event) {
  const removeButton = event.target.closest(".remove-item-button");
  if (!removeButton) {
    return;
  }

  removeButton.closest("tr")?.remove();
  ensureAtLeastOneOrderRow();
  updateOrderTotalHint();
}

function handleOrderStatusChange(event) {
  const select = event.target.closest("select[data-order-id]");
  if (!select) {
    return;
  }

  const order = state.orders.find((item) => item.id === select.dataset.orderId);
  if (!order) {
    return;
  }

  order.status = select.value;
  renderAll();
}

function handleSettlementSelection(event) {
  const button = event.target.closest("[data-settlement-key]");
  if (!button) {
    return;
  }

  renderSettlementPreview(button.dataset.settlementKey);
}

function handleSettlementSave(event) {
  event.preventDefault();
  const key = elements.settlementKey.value;
  if (!key) {
    return;
  }

  state.settlementRecords[key] = {
    status: elements.settlementStatus.value,
    invoiceNo: elements.settlementInvoiceNo.value.trim(),
    dueDate: elements.settlementDueDate.value,
    remark: elements.settlementRemark.value.trim()
  };

  renderAll();
  renderSettlementPreview(key);
}

function handleSeedDemo() {
  if (!window.confirm("这会用示例数据覆盖当前本地数据，确定继续吗？")) {
    return;
  }

  state = seedDemoState();
  elements.orderItemsBody.innerHTML = "";
  addOrderItemRow();
  populateOrderDefaults();
  renderAll();
}

function handleClearData() {
  if (!window.confirm("确定清空当前浏览器中的订单与客户数据吗？")) {
    return;
  }

  state = {
    customers: [],
    orders: [],
    settlementRecords: {}
  };

  selectedSettlementKey = "";
  elements.customerForm.reset();
  elements.orderForm.reset();
  elements.orderItemsBody.innerHTML = "";
  addOrderItemRow();
  populateOrderDefaults();
  renderAll();
}

function addOrderItemRow(item = {}) {
  const fragment = elements.orderItemTemplate.content.cloneNode(true);
  const row = fragment.querySelector("tr");
  row.querySelector('[name="sku"]').value = item.sku || "";
  row.querySelector('[name="name"]').value = item.name || "";
  row.querySelector('[name="spec"]').value = item.spec || "";
  row.querySelector('[name="quantity"]').value = item.quantity || 1;
  row.querySelector('[name="unit"]').value = item.unit || "盒";
  row.querySelector('[name="price"]').value = item.price || 0;
  row.querySelector('[name="taxRate"]').value = item.taxRate ?? 13;
  elements.orderItemsBody.appendChild(fragment);
  updateOrderTotalHint();
}

function ensureAtLeastOneOrderRow() {
  if (elements.orderItemsBody.children.length === 0) {
    addOrderItemRow();
  }
}

function populateOrderDefaults() {
  const orderDateInput = elements.orderForm.querySelector('[name="orderDate"]');
  const deliveryDateInput = elements.orderForm.querySelector('[name="deliveryDate"]');
  if (!orderDateInput.value) {
    orderDateInput.value = todayISO();
  }
  if (!deliveryDateInput.value) {
    deliveryDateInput.value = shiftDate(todayISO(), 3);
  }
}

function updateOrderTotalHint() {
  const items = collectOrderItems({ strict: false });
  const totals = calculateOrderTotals(items);
  if (items.length === 0) {
    elements.orderTotalHint.textContent = "请至少填写一行有效订单明细。";
    return;
  }

  elements.orderTotalHint.textContent = `未税 ${formatCurrency(totals.subtotalAmount)} / 税额 ${formatCurrency(totals.taxAmount)} / 含税合计 ${formatCurrency(totals.totalAmount)}`;
}

function collectOrderItems(options = { strict: true }) {
  const rows = [...elements.orderItemsBody.querySelectorAll("tr")];
  return rows.map((row) => {
    const name = row.querySelector('[name="name"]').value.trim();
    const quantity = Number(row.querySelector('[name="quantity"]').value || 0);
    const price = Number(row.querySelector('[name="price"]').value || 0);

    if (!name || quantity <= 0 || price < 0) {
      return null;
    }

    return {
      sku: row.querySelector('[name="sku"]').value.trim(),
      name,
      spec: row.querySelector('[name="spec"]').value.trim(),
      quantity,
      unit: row.querySelector('[name="unit"]').value.trim() || "件",
      price,
      taxRate: Number(row.querySelector('[name="taxRate"]').value || 0)
    };
  }).filter((item) => {
    if (options.strict) {
      return Boolean(item);
    }
    return Boolean(item);
  });
}

function calculateOrderTotals(items) {
  return items.reduce((accumulator, item) => {
    const lineSubtotal = Number(item.quantity) * Number(item.price);
    const lineTax = lineSubtotal * (Number(item.taxRate || 0) / 100);
    accumulator.subtotalAmount += lineSubtotal;
    accumulator.taxAmount += lineTax;
    accumulator.totalAmount += lineSubtotal + lineTax;
    return accumulator;
  }, {
    subtotalAmount: 0,
    taxAmount: 0,
    totalAmount: 0
  });
}

function buildOrder(customerId, data) {
  const totals = calculateOrderTotals(data.items);
  return {
    id: uid("order"),
    customerId,
    orderNo: data.orderNo,
    poNumber: data.poNumber,
    orderDate: data.orderDate,
    deliveryDate: data.deliveryDate,
    department: data.department,
    status: data.status,
    notes: data.notes,
    settlementMonth: toMonth(data.orderDate),
    items: data.items,
    subtotalAmount: totals.subtotalAmount,
    taxAmount: totals.taxAmount,
    totalAmount: totals.totalAmount,
    createdAt: new Date().toISOString()
  };
}

function getCustomer(customerId) {
  return state.customers.find((customer) => customer.id === customerId);
}

function rankCustomerByMonth(month) {
  const rank = new Map();
  state.orders.filter((order) => order.settlementMonth === month).forEach((order) => {
    rank.set(order.customerId, (rank.get(order.customerId) || 0) + order.totalAmount);
  });

  const [bestEntry] = [...rank.entries()].sort((left, right) => right[1] - left[1]);
  if (!bestEntry) {
    return null;
  }

  const customer = getCustomer(bestEntry[0]);
  return {
    name: customer?.name || "未知客户",
    total: bestEntry[1]
  };
}

function settlementKey(customerId, month) {
  return `${customerId}__${month}`;
}

function defaultDueDate(month, creditDays) {
  const [year, monthValue] = month.split("-").map(Number);
  const lastDay = new Date(year, monthValue, 0);
  lastDay.setDate(lastDay.getDate() + Number(creditDays || 30));
  return formatLocalDate(lastDay);
}

function createOrderNo(orderDate, serial) {
  const month = toMonth(orderDate).replace("-", "");
  return `SO-${month}-${String(serial).padStart(3, "0")}`;
}

function currentMonth() {
  return formatLocalDate(new Date()).slice(0, 7);
}

function todayISO() {
  return formatLocalDate(new Date());
}

function toMonth(dateString) {
  return dateString.slice(0, 7);
}

function shiftDate(dateString, offset) {
  const date = new Date(`${dateString}T00:00:00`);
  date.setDate(date.getDate() + offset);
  return formatLocalDate(date);
}

function uid(prefix) {
  if (window.crypto?.randomUUID) {
    return `${prefix}-${window.crypto.randomUUID().slice(0, 8)}`;
  }
  return `${prefix}-${Math.random().toString(16).slice(2, 10)}`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  return value;
}

function formatLocalDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusClass(status) {
  if (status === "已完成" || status === "已回款") {
    return "success";
  }
  if (status === "待审核" || status === "待履约" || status === "待开票") {
    return "pending";
  }
  return "progress";
}
