<template>
  <el-card>
    <div style="margin-bottom:12px; display:flex; gap:10px">
      <el-button type="primary" @click="openAdd">＋ 添加商品</el-button>
      <el-button @click="load">刷新</el-button>
      <span style="color:#909399; font-size:13px; line-height:32px">
        闲鱼商品ID获取：网页版打开你的商品详情页，地址栏 goofish.com/item/ 后的数字串
      </span>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="商品名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="xianyu_item_id" label="闲鱼商品ID" width="150" />
      <el-table-column prop="price" label="价格" width="90" />
      <el-table-column label="自动发货" width="90">
        <template #default="{ row }">
          <el-tag :type="row.auto_delivery ? 'success' : 'info'">{{ row.auto_delivery ? '开' : '关' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="库存" width="100">
        <template #default="{ row }">
          <el-tag :type="row.stock > 5 ? 'success' : 'danger'">{{ row.stock }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="sold_count" label="已售" width="80" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="openCards(row)">卡密</el-button>
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除该商品？" @confirm="del(row)">
            <template #reference><el-button link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 商品编辑 -->
  <el-dialog v-model="dlg" :title="form.id ? '编辑商品' : '添加商品'" width="560">
    <el-form label-width="110px">
      <el-form-item label="鱼店账号">
        <el-select v-model="form.account_id" placeholder="选择账号" style="width:100%">
          <el-option v-for="a in accounts" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品名称"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="闲鱼商品ID"><el-input v-model="form.xianyu_item_id" placeholder="商品详情页地址里的数字串" /></el-form-item>
      <el-form-item label="价格"><el-input-number v-model="form.price" :min="0" :precision="2" /></el-form-item>
      <el-form-item label="自动发货"><el-switch v-model="form.auto_delivery" /></el-form-item>
      <el-form-item label="发货内容模板">
        <el-input v-model="form.delivery_template" type="textarea" :rows="4" />
        <div style="color:#909399; font-size:12px">用 {card} 占位符代表卡密内容，发货时自动替换</div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dlg = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>

  <!-- 卡密管理 -->
  <el-drawer v-model="cardDlg" :title="`卡密管理 - ${current?.name || ''}`" size="55%">
    <div style="margin-bottom:12px; display:flex; gap:10px">
      <el-button type="primary" @click="importDlg = true">＋ 批量导入</el-button>
      <el-button :disabled="!selected.length" type="danger" @click="delCards">删除选中</el-button>
      <el-radio-group v-model="cardStatus" @change="loadCards">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="unused">未售</el-radio-button>
        <el-radio-button value="sold">已售</el-radio-button>
      </el-radio-group>
    </div>
    <el-table :data="cards" @selection-change="s => selected = s" size="small" max-height="600">
      <el-table-column type="selection" width="40" :selectable="r => r.status !== 'sold'" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="content" label="卡密内容" show-overflow-tooltip />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'sold' ? 'danger' : 'success'" size="small">{{ row.status === 'sold' ? '已售' : '未售' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="order_id" label="售出订单" width="170" show-overflow-tooltip />
      <el-table-column prop="sold_at" label="售出时间" width="160" />
    </el-table>
    <el-pagination style="margin-top:12px" layout="total, prev, pager, next" :total="cardTotal"
      :page-size="cardSize" v-model:current-page="cardPage" @current-change="loadCards" />
  </el-drawer>

  <!-- 导入卡密 -->
  <el-dialog v-model="importDlg" title="批量导入卡密（每行一个）" width="520">
    <el-input v-model="importText" type="textarea" :rows="10" placeholder="卡密1&#10;卡密2&#10;卡密3" />
    <template #footer>
      <el-button @click="importDlg = false">取消</el-button>
      <el-button type="primary" @click="doImport">导入</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const list = ref([]), accounts = ref([]), loading = ref(false), dlg = ref(false)
const cardDlg = ref(false), importDlg = ref(false), importText = ref('')
const current = ref(null), cards = ref([]), cardTotal = ref(0)
const cardPage = ref(1), cardSize = 50, cardStatus = ref(''), selected = ref([])
const empty = { id: 0, account_id: null, name: '', xianyu_item_id: '', price: 0, auto_delivery: true, delivery_template: '感谢购买！您的卡密：{card}\n如有问题请随时联系我~', enabled: true, remark: '' }
const form = reactive({ ...empty })

const load = async () => {
  loading.value = true
  try {
    list.value = await api.get('/products')
    accounts.value = await api.get('/accounts')
  } finally { loading.value = false }
}
const openAdd = () => { Object.assign(form, empty); dlg.value = true }
const openEdit = row => { Object.assign(form, row); dlg.value = true }
const save = async () => {
  if (!form.account_id || !form.name || !form.xianyu_item_id)
    return ElMessage.warning('请完整填写账号、名称和闲鱼商品ID')
  const body = { ...form }
  delete body.id; delete body.stock; delete body.sold_count; delete body.created_at
  if (form.id) await api.put(`/products/${form.id}`, body)
  else await api.post('/products', body)
  ElMessage.success('已保存'); dlg.value = false; load()
}
const del = async row => { await api.delete(`/products/${row.id}`); ElMessage.success('已删除'); load() }

const openCards = row => { current.value = row; cardPage.value = 1; cardStatus.value = ''; cardDlg.value = true; loadCards() }
const loadCards = async () => {
  const res = await api.get('/cards', { params: { product_id: current.value.id, status: cardStatus.value, page: cardPage.value, size: cardSize } })
  cards.value = res.items; cardTotal.value = res.total
}
const doImport = async () => {
  const res = await api.post('/cards/import', { product_id: current.value.id, contents: importText.value })
  ElMessage.success(res.msg); importDlg.value = false; importText.value = ''; loadCards(); load()
}
const delCards = async () => {
  const res = await api.post('/cards/delete', { ids: selected.value.map(c => c.id) })
  ElMessage.success(res.msg); loadCards(); load()
}

onMounted(load)
</script>
