# 1.0 分发备忘（短文素材）

> 可改写成小红书 / 掘金 / 朋友圈。勿承诺 offer。

## 标题备选

- 开源本地 AI 求职助手 1.0：简历不上传，默认不海投  
- 用 Claude/Cursor 投国内岗：从 JD 到 PDF 到看板一条龙  
- 受够群发简历？这个开源仓库按岗位改材料还本地打分  

## 三点差异

1. **本地优先**：匹配、追踪、材料都在你电脑；敏感数据 gitignore  
2. **默认手动投**：工具准备 PDF/话术，发送按钮你自己点（可半自动复制）  
3. **可量化**：关键词命中/真缺口、期望薪资对照、今日计划与投递漏斗  

## 三步试跑

```bash
git clone https://github.com/LuckTerence/cn-job-assistant.git
cd cn-job-assistant && make check
# Agent：/setup-zh → /apply-zh 粘贴 JD
```

## 链接

- 仓库：https://github.com/LuckTerence/cn-job-assistant  
- Tag：`v1.0.0`  
- 发版正文草稿：`docs/github-release-v1.0.0.md`  
- 我在用：Issue 模板 `using.yml`  

## 合规一句

不教你封号海投；auto 有门禁，默认关。
