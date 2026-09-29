<template>
  <div class="login-page">
    <el-card class="login-card">
      <h2>🐟 闲鱼自动发货管理系统</h2>
      <el-form @keyup.enter="login">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="login">登 录</el-button>
      </el-form>
      <p class="tip">默认账号 admin / admin123，部署后请立即修改</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

const login = async () => {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    const res = await api.post('/auth/login', form)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', form.username)
    router.push('/')
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-page { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1d2935, #3a5169); }
.login-card { width: 380px; padding: 10px 20px; }
h2 { text-align: center; color: #303133; }
.tip { color: #909399; font-size: 12px; text-align: center; }
</style>
