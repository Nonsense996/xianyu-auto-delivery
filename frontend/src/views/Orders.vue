<template>
  <el-card>
    <div style="margin-bottom:12px; display:flex; gap:10px; align-items:center">
      <el-select v-model="filter.status" placeholder="状态" clearable style="width:140px" @change="load">
        <el-option label="已发货" value="delivered" />
        <el-option label="失败" value="failed" />
        <el-option label="待处理" value="pending" />
        <el-option label="人工" value="manual" />
      </el-select>
      <el-select v-model="filter.account_id" placeholder="账号" clearable style="width:140px" @change="load">
        <el-option v-for="a in accounts" :key="a.id" :label="a.name" :value="a.id" />
      </el-select>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="order_id" label="订单号" width="230" show-overflow-tooltip />
      <el-table-column prop="buyer_id" label="买家" width="130" />
      <el-table-column label="金额" width="90"><template #default="{ row }">¥{{ row.amount }}</template></el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="tagType(row.status)">{{ tagText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="delivered_content" label="发货内容" show-overflow-tooltip />
      <el-table-column prop="error_msg" label="错误信息" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="170" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'delivered'" link type="primary" @click="openResend(row)">补发</el-button>
          <el-button link @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination style="margin-top:12px" layout="total, prev, pager, next" :total="total"
      :page-size="size" v-model:current-page="page" @current-change="load" />
  </el-card>

  <el-dialog v-model="resendDlg" title="手动补发" width="520">
    <el-form label-width="110px">
      <el-form-item label="会话ID">
        <el-input v-model="resendForm.conversation_id" placeholder="买家会话 conversationId（从聊天页/日志获取）" />
      </el-form-item>
      <el-form-item label="发货内容">
        <el-input v-model="resendForm.text" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="resendDlg = false">取消</el-button>
      <el-button type="primary" @click="doResend">发送</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="detailDlg" title="订单详情" width="560">
    <el-descriptions v-if="detail" :column="1" border>
      <el-descriptions-item label="订单号">{{ detail.order_id }}</el-descriptions-item>
      <el-descriptions-item label="买家">{{ detail.buyer_id }}</el-descriptions-item>
      <el-descriptions-item label="买家消息">{{ detail.buyer_message || '—' }}</el-descriptions-item>
      <el-descriptions-item label="发货内容">{{ detail.delivered_content || '—' }}</el-descriptions-item>
      <el-descriptions-item label="错误信息">{{ detail.error_msg || '—' }}</el-descriptions-item>
    </el-descriptions>
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const list = ref([]), accounts = ref([]), total = ref(0), page = ref(1), size = 20
const loading = ref(false), resendDlg = ref(false), detailDlg = ref(false), detail = ref(null)
const filter = reactive({ status: '', account_id: null })
const resendForm = reactive({ order_id: '', conversation_id: '', text: '' })

const tagType = s => ({ delivered: 'success', failed: 'danger', pending: 'warning', manual: 'info' }[s] || 'info')
const tagText = s => ({ delivered: '已发货', failed: '失败', pending: '待处理', manual: '人工' }[s] || s)

const load = async () => {
  loading.value = true
  try {
    const res = await api.get('/orders', { params: { ...filter, page: page.value, size } })
    list.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
const openResend = row => {
  Object.assign(resendForm, { order_id: row.order_id, conversation_id: '', text: row.delivered_content })
  resendDlg.value = true
}
const openDetail = row => { detail.value = row; detailDlg.value = true }
const doResend = async () => {
  await api.post(`/orders/${resendForm.order_id}/resend`, null, {
    params: { conversation_id: resendForm.conversation_id, text: resendForm.text }
  })
  ElMessage.success('补发成功'); resendDlg.value = false; load()
}

onMounted(async () => {
  load()
  accounts.value = await api.get('/accounts')
})
setInterval(load, 15000)
</script>
