<template>
  <el-card>
    <div style="margin-bottom:12px; display:flex; gap:10px">
      <el-button type="primary" @click="openAdd">＋ 添加鱼店账号</el-button>
      <el-button @click="load">刷新</el-button>
      <span style="color:#909399; font-size:13px; line-height:32px">
        状态说明：online=在线监听中；error 需查看状态说明，常见为 Cookie 失效
      </span>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="备注名" width="160" />
      <el-table-column prop="user_id" label="用户ID" width="140" />
      <el-table-column label="连接状态" width="140">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status_msg" label="状态说明" show-overflow-tooltip />
      <el-table-column prop="product_count" label="绑定商品" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="toggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" @click="reconnect(row)">重连</el-button>
          <el-popconfirm title="确认删除该账号？" @confirm="del(row)">
            <template #reference><el-button link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="dlg" :title="form.id ? '编辑账号' : '添加账号'" width="560">
    <el-alert type="info" :closable="false" style="margin-bottom:12px"
      title="如何获取 Cookie：电脑浏览器登录 goofish.com（闲鱼网页版）→ F12 打开开发者工具 → Network → 刷新页面 → 任意请求的 Request Headers 里复制完整 Cookie（或从 Application → Cookies 导出）。保存时系统会自动校验 Cookie 有效性。" />
    <el-form label-width="80px">
      <el-form-item label="备注名"><el-input v-model="form.name" placeholder="如：我的主店" /></el-form-item>
      <el-form-item label="Cookie">
        <el-input v-model="form.cookie" type="textarea" :rows="5" placeholder="粘贴完整 Cookie 字符串" />
      </el-form-item>
      <el-form-item label="启用监听"><el-switch v-model="form.enabled" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dlg = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存并校验</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const list = ref([]), loading = ref(false), dlg = ref(false), saving = ref(false)
const form = reactive({ id: 0, name: '', cookie: '', enabled: true })

const statusType = s => ({ online: 'success', connecting: 'warning', error: 'danger', offline: 'info' }[s] || 'info')

const load = async () => { loading.value = true; try { list.value = await api.get('/accounts') } finally { loading.value = false } }
const openAdd = () => { Object.assign(form, { id: 0, name: '', cookie: '', enabled: true }); dlg.value = true }
const openEdit = row => {
  Object.assign(form, { id: row.id, name: row.name, cookie: '', enabled: row.enabled })
  form._old = row
  dlg.value = true
}
const save = async () => {
  if (!form.name) return ElMessage.warning('请填写备注名')
  saving.value = true
  try {
    const body = { name: form.name, enabled: form.enabled }
    if (form.id) {
      body.cookie = form.cookie || form._old.cookie  // 不填则沿用原 Cookie
      await api.put(`/accounts/${form.id}`, body)
    } else {
      body.cookie = form.cookie
      await api.post('/accounts', body)
    }
    ElMessage.success('已保存')
    dlg.value = false
    load()
  } finally { saving.value = false }
}
const toggle = async row => { await api.post(`/accounts/${row.id}/toggle`); load() }
const del = async row => { await api.delete(`/accounts/${row.id}`); ElMessage.success('已删除'); load() }
const reconnect = async row => { await api.post(`/accounts/${row.id}/reconnect`); ElMessage.success('已发起重连'); setTimeout(load, 2000) }

onMounted(load)
setInterval(load, 10000)
</script>
