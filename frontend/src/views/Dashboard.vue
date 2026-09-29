<template>
  <div v-if="data">
    <el-row :gutter="16">
      <el-col :span="6" v-for="c in cards" :key="c.label">
        <el-card shadow="hover"><div class="num" :style="{color: c.color}">{{ c.value }}</div><div class="label">{{ c.label }}</div></el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="14">
        <el-card header="近 7 日发货趋势">
          <div class="bars">
            <div v-for="t in data.trend" :key="t.date" class="bar-item">
              <div class="bar" :style="{height: barH(t.count) + 'px'}">{{ t.count || '' }}</div>
              <div class="bar-date">{{ t.date }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="⚠️ 低库存商品（少于 5 张卡密）">
          <el-empty v-if="!data.low_stock.length" description="库存充足" :image-size="60" />
          <div v-for="p in data.low_stock" :key="p.id" class="low-item">
            <span>{{ p.name }}</span><el-tag type="danger">剩 {{ p.stock }} 张</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-card header="最近日志" style="margin-top:16px">
      <el-table :data="data.logs" size="small">
        <el-table-column prop="created_at" label="时间" width="180" />
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column label="级别" width="80">
          <template #default="{ row }"><el-tag :type="row.level === 'error' ? 'danger' : 'info'" size="small">{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="message" label="内容" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../api'

const data = ref(null)
let timer

const cards = computed(() => data.value ? [
  { label: '累计发货', value: data.value.cards.total_delivered, color: '#409eff' },
  { label: '今日发货', value: data.value.cards.today_delivered, color: '#67c23a' },
  { label: '卡密库存', value: data.value.cards.stock, color: '#e6a23c' },
  { label: '待处理/失败', value: data.value.cards.failed, color: '#f56c6c' },
] : [])

const barH = c => Math.max(8, c * 20)
const load = async () => { data.value = await api.get('/dashboard') }

onMounted(() => { load(); timer = setInterval(load, 15000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.num { font-size: 28px; font-weight: bold; }
.label { color: #909399; margin-top: 4px; }
.bars { display: flex; align-items: flex-end; gap: 18px; height: 140px; padding-top: 10px; }
.bar-item { text-align: center; }
.bar { width: 36px; background: #409eff; border-radius: 4px 4px 0 0; color: #fff; font-size: 12px; }
.bar-date { color: #909399; font-size: 12px; margin-top: 6px; }
.low-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
</style>
