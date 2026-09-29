<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">🐟 闲鱼自动发货</div>
      <el-menu router :default-active="$route.path" background-color="#1d2935" text-color="#a7b1c2" active-text-color="#fff">
        <el-menu-item index="/dashboard">📊 工作台</el-menu-item>
        <el-menu-item index="/accounts">🛒 鱼店管理</el-menu-item>
        <el-menu-item index="/products">📦 商品与卡密</el-menu-item>
        <el-menu-item index="/orders">🧾 订单/发货记录</el-menu-item>
        <el-menu-item index="/rules">💬 自动回复</el-menu-item>
        <el-menu-item index="/logs">📄 运行日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="title">{{ $route.meta.title }}</span>
        <el-dropdown @command="onCmd">
          <span class="user">👤 {{ username }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
const username = localStorage.getItem('username') || 'admin'
const onCmd = cmd => {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #1d2935; }
.logo { color: #fff; font-size: 16px; font-weight: bold; padding: 20px 16px; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.title { font-size: 16px; font-weight: 600; }
.user { cursor: pointer; }
.el-menu { border-right: none; }
</style>
