const BASE_URL = 'http://localhost:8001/api'

/**
 * 普通 JSON 请求
 */
async function request(path, options = {}) {
    const headers = { ...options.headers }

    // DELETE/GET 不带 body，不强行设 Content-Type，避免不必要的预检
    const method = (options.method || 'GET').toUpperCase()
    if (['POST', 'PUT', 'PATCH'].includes(method)) {
        headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        method,
        headers,
    })
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '请求失败' }))
        throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
}

// ===== 文档 =====

/** 获取文档列表 */
export function getDocuments() {
    return request('/documents')
}

/** 删除文档 */
export function deleteDocument(id) {
    return request(`/documents/${id}`, { method: 'DELETE' })
}

/** 上传文档 */
export function uploadDocument(file) {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE_URL}/upload`, { method: 'POST', body: form }).then(r => r.json())
}

// ===== 对话 =====

/** 获取对话历史（可选按 doc_id 过滤） */
export function getConversations(docId) {
    const query = docId ? `?doc_id=${docId}` : ''
    return request(`/conversations${query}`)
}

/** 删除单条对话 */
export function deleteConversation(id) {
    return request(`/conversations/${id}`, { method: 'DELETE' })
}


// ===== 问答（SSE 流式）=====

/**
 * 发送问题，流式接收回答。
 * @param {string} question  用户问题
 * @param {string|null} docId  文档 ID（null 为全局模式）
 * @param {object} callbacks
 *   - onToken(content)    每收到一个 token
 *   - onSources(sources)  收到来源引用
 *   - onDone()            回答结束
 *   - onError(err)        出错
 */
export async function chatStream(question, docId, history, callbacks) {
    const { onToken, onReasoning, onSources, onPipeline, onAbstain, onDone, onError } = callbacks

    const url = docId
        ? `${BASE_URL}/chat/${docId}`
        : `${BASE_URL}/chat`

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, history }),
        })

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: '请求失败' }))
            onError(new Error(err.detail || `HTTP ${response.status}`))
            return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()
            if (done) break

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6).trim()
                    if (!jsonStr) continue
                    try {
                        const data = JSON.parse(jsonStr)
                        if (data.type === 'pipeline') {
                            onPipeline(data.pipeline)
                        } else if (data.type === 'abstain') {
                            callbacks.onAbstain?.(data.message)
                        } else if (data.type === 'token') {
                            onToken(data.content)
                        } else if (data.type === 'reasoning') {
                            onReasoning?.(data.content)
                        } else if (data.type === 'sources') {
                            onSources(data.sources)
                        } else if (data.type === 'done') {
                            onDone()
                        }
                    } catch {
                        // 忽略解析失败的行
                    }
                }
            }
        }
    } catch (err) {
        onError(err)
    }
}

