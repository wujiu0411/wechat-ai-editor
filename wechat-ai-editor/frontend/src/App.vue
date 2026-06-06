<template>
  <el-container class="app-container">
    <el-aside width="220px" class="app-aside">
      <div class="logo-area">
        <h2>PUDOW AI Editor</h2>
        <p>公众号内容生成助手</p>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="app-menu"
        background-color="#001529"
        text-color="#ffffffa6"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/create">
          <el-icon><EditPen /></el-icon>
          <span>创建文章</span>
        </el-menu-item>
        <el-menu-item index="/suggestions">
          <el-icon><Opportunity /></el-icon>
          <span>选题建议</span>
        </el-menu-item>
        <el-menu-item index="/assets">
          <el-icon><Picture /></el-icon>
          <span>素材库</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <span>历史记录</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}
.app-container {
  height: 100vh;
}
.app-aside {
  background: #001529;
  overflow-y: auto;
}
.logo-area {
  padding: 20px 16px;
  border-bottom: 1px solid #ffffff1a;
}
.logo-area h2 {
  color: #fff;
  font-size: 18px;
  margin-bottom: 4px;
}
.logo-area p {
  color: #ffffff73;
  font-size: 12px;
}
.app-menu {
  border-right: none;
}
.app-main {
  background: #f0f2f5;
  overflow-y: auto;
  padding: 20px;
}
</style>
