# mimo-proxy

让GPU节点（无法上网）通过CPU节点（可以上网）访问mimo API的反向代理。

## 架构

```
GPU节点 (无法上网)                    CPU节点 (可以上网)
┌─────────────────┐                  ┌─────────────────┐
│  meta-harness   │  SSH端口转发      │   mimo-proxy    │
│  proposer.py    │ ───────────────> │   (FastAPI)     │ ────> mimo API
│  localhost:8080 │                  │   0.0.0.0:8080  │
└─────────────────┘                  └─────────────────┘
```

## 使用方法

### 1. 在CPU节点上启动mimo-proxy

```bash
cd harness-sii/mimo-proxy
bash run.sh
```

代理将在 `0.0.0.0:8080` 上监听。

### 2. 在GPU节点上设置SSH端口转发

```bash
# 在GPU节点上执行
ssh -L 8080:localhost:8080 cpu-node
```

或者在VS Code中配置端口转发。

### 3. 测试连接

```bash
# 在GPU节点上测试
curl http://localhost:8080/health
```

应该返回：
```json
{"status": "ok", "mimo_configured": true, "mimo_base_url": "https://token-plan-cn.xiaomimimo.com/v1"}
```

### 4. 运行Meta-Harness

Meta-Harness的config.py已经配置为使用mimo-proxy：

```python
proposer_base_url: str = "http://localhost:8080/v1"  # mimo-proxy地址
```

直接运行即可：
```bash
cd meta-harness-sii
python meta_loop.py
```

## 配置

通过环境变量配置：

```bash
# 修改监听端口（默认8080）
export MIMO_PROXY_PORT=9090

# 修改监听地址（默认0.0.0.0）
export MIMO_PROXY_HOST=127.0.0.1

# 启用认证（可选）
export MIMO_PROXY_API_TOKEN=your-secret-token
```

## 与search-proxy的关系

mimo-proxy的设计与search-proxy完全一致：
- 都是FastAPI应用
- 都运行在CPU节点上
- 都通过SSH端口转发被GPU节点访问
- 都是反向代理，转发请求到外部API
