<template>
  <el-card>
    <div style="margin-bottom:12px; display:flex; gap:10px">
      <el-select v-model="level" placeholder="级别" clearable style="width:140px" @change="load">
        <el-option label="错误" value="error" />
        <el-option label="警告" value="warn" />
        <el-option label="信息" value="info" />
      </el-select>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" size="small" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="级别" width="80">
        <template #default="{ row }">
          <el-tag :type="row.level === 'error' ? 'danger' : row.level === 'warn' ? 'warning' : 'info'" size="small">
            {{ row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="module" label="模块" width="100" />
      <el-table-column prop="account_id" label="账号" width="80" />
      <el-table-column prop="message" label="内容" show-overflow-tooltip />
    </el-table>
    <el-pagination style="margin-top:12px" layout="total, prev, pager, next" :total="total"
      :page-size="size" v-model:current-page="page" @current-change="load" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'

const list = ref([]), total = ref(0), page = ref(1), size = 50, level = ref(''), loading = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res = await api.get('/logs', { params: { level: level.value, page: page.value, size } })
    list.value = res.items; total.value = res.total
  } finally { loading.value = false }
}

onMounted(load)
</script>
