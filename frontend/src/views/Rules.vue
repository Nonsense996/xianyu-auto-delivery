<template>
  <el-card header="关键词自动回复规则" style="margin-bottom:16px">
    <div style="margin-bottom:12px">
      <el-button type="primary" @click="openAdd">＋ 添加规则</el-button>
    </div>
    <el-table :data="list">
      <el-table-column prop="keyword" label="触发关键词（逗号分隔）" min-width="160" />
      <el-table-column prop="reply_text" label="回复内容" min-width="220" show-overflow-tooltip />
      <el-table-column prop="priority" label="优先级" width="80" />
      <el-table-column prop="hit_count" label="命中次数" width="90" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @change="toggle(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-popconfirm title="确认删除？" @confirm="del(row)">
            <template #reference><el-button link type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-card header="兜底回复（未命中任何规则时）">
    <el-switch v-model="dr.enabled" active-text="开启" />
    <el-input v-model="dr.reply_text" type="textarea" :rows="3" style="margin-top:12px"
      placeholder="亲，在的！请问有什么可以帮您~" />
    <el-button type="primary" style="margin-top:12px" @click="saveDr">保存兜底回复</el-button>
  </el-card>

  <el-dialog v-model="dlg" :title="form.id ? '编辑规则' : '添加规则'" width="520">
    <el-form label-width="110px">
      <el-form-item label="触发关键词">
        <el-input v-model="form.keyword" placeholder="多个用英文逗号分隔，如：多少钱,价格" />
      </el-form-item>
      <el-form-item label="回复内容">
        <el-input v-model="form.reply_text" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="优先级">
        <el-input-number v-model="form.priority" :min="0" :max="999" />
      </el-form-item>
      <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dlg = false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const list = ref([]), dlg = ref(false)
const dr = reactive({ enabled: false, reply_text: '' })
const form = reactive({ id: 0, keyword: '', reply_text: '', priority: 0, enabled: true })

const load = async () => {
  list.value = await api.get('/rules')
  Object.assign(dr, await api.get('/rules/default-reply'))
}
const openAdd = () => { Object.assign(form, { id: 0, keyword: '', reply_text: '', priority: 0, enabled: true }); dlg.value = true }
const openEdit = row => { Object.assign(form, row); dlg.value = true }
const save = async () => {
  if (!form.keyword || !form.reply_text) return ElMessage.warning('请填写关键词和回复内容')
  const body = { keyword: form.keyword, reply_text: form.reply_text, priority: form.priority, enabled: form.enabled, account_id: null }
  if (form.id) await api.put(`/rules/${form.id}`, body)
  else await api.post('/rules', body)
  ElMessage.success('已保存'); dlg.value = false; load()
}
const toggle = async row => { await api.put(`/rules/${row.id}`, { ...row, enabled: !row.enabled }); load() }
const del = async row => { await api.delete(`/rules/${row.id}`); ElMessage.success('已删除'); load() }
const saveDr = async () => { await api.put('/rules/default-reply', dr); ElMessage.success('已保存') }

onMounted(load)
</script>
