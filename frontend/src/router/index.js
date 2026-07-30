import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    {
        path: '/',
        redirect: '/chat'          // 根路径默认跳转到全局问答
    },
    {
        path: '/chat',
        name: 'Chat',
        component: () => import('../views/ChatView.vue')
    },
    {
        path: '/chat/:docId',
        name: 'ChatSingle',
        component: () => import('../views/ChatView.vue'),   // 同一个视图，通过路由参数区分
        props: true
    },
    {
        path: '/documents',
        name: 'Documents',
        component: () => import('../views/DocumentsView.vue')
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
