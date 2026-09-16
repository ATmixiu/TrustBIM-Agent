# TrustBIM Agent — 课堂演示脚本（中文）

## 启动
```
cd /d D:\TrustBIM_Agent
.venv\Scripts\activate
streamlit run app.py
```
浏览器自动打开 http://localhost:8501。

## 开场（30 秒）
> "这是 TrustBIM Agent，一个能直接读取老师提供的 BIM（IFC）和施工图纸（PDF）的 AI Agent。
> 用户用自然语言提问，Agent 自己判断任务类型、选择 IFC 还是 PDF 工具、读取真实数据，
> 然后返回答案，并附上 Source / Evidence / Method。"

指着顶部四个 Ready 状态卡。

---

## Demo 1 — BIM 数量查询（约 1 分钟）
切到 **AI Assistant** Tab，输入：

```
How many doors are in the architectural model?
```

点击 Run。强调：
- **Answer**: There are 16 doors.
- **Source**: Architectural IFC
- **Evidence**: IfcDoor × 16
- **Method**: Structured IFC Query
- 下方 Agent Trace 显示：Intent detected → Tool selected → Data queried → Answer generated。
> "这个数字不是 LLM 猜的，是 IfcOpenShell 直接对 IFC 文件执行 by_type 查出来的。"

可补一句：再问 `How many beams are in the structural model?` → 370 beams。

---

## Demo 2 — 自动切换到 PDF（约 1.5 分钟）
输入：

```
Which rooms are located on Level 2?
```

强调：
- Agent 先查 IFC，发现 **IfcSpace = 0**（建筑模型里没有房间语义）。
- 于是自动切换到 PDF 图纸，定位到 **A102 Plans** 第 3 页。
- 界面显示 **Selected Source: Architectural Drawing**，**Reason: Room semantics are unavailable in the IFC model.**
- Answer 列出 Level 2 房间：201 Entry Hall、202 Bedroom、204 Bedroom、206 Master Bedroom、Master Bath、Bath、Linen。

> "这就是 Agent 自动选工具的核心演示——IFC 答不了，就去 PDF 里找。"

---

## Demo 3 — BIM Health Check（约 1 分钟）
切到 **BIM Health** Tab，点 **Run BIM Health Check**。

讲表格：
- IfcProject / IfcSite / IfcBuilding / IfcBuildingStorey = PASS
- **IfcSpace = 0 → WARNING: Room semantics unavailable**（正好引出 Demo 2）
- 结构模型的 IfcBeam / IfcColumn / IfcPile / IfcFooting / IfcReinforcingBar 都 PASS
- 结构模型 **IfcBuildingStorey = 0 → WARNING**（结构模型没有楼层层级，引出 Demo 4 为什么要用 PDF 补）

> "状态只有三种：PASS / WARNING / REVIEW，不做复杂合规检测。"

---

## Demo 4 — 建筑-结构协同检查（约 1.5 分钟）
切到 **Coordination** Tab，点 **Run Coordination Check**。

表格：
| Item | Architecture | Structure | Status |
|---|---|---|---|
| Level 1 | 0 | 0 | MATCH |
| Level 2 | 3000 | 3000 | MATCH |
| Ceiling | 2700 | 2700 | MATCH |
| Foundation | -800 | -1200 | REVIEW |
| Roof / Top of Parapet | 6000 | 6000 | MATCH |

强调：
- Architecture 标高来自 IFC BuildingStorey.Elevation；
- Structure 标高来自结构 PDF Wall Section（S202）；
- Foundation 差 400 mm，状态 **REVIEW**，备注 "Potential coordination issue — manual review recommended"。
> "我们不喊 ERROR，不做设计错误的断言，只标 REVIEW 并建议人工复核。"

---

## 收尾（30 秒）
> "四个核心场景全部用真实文件数据跑通，没有 mock。
> 下一步（Future Work）：接 LLM 润色、向量 RAG、Revit 插件、自动碰撞检测、3D 高亮。"

## 录屏前检查清单
- [ ] 浏览器只开一个标签页
- [ ] 终端停在 `streamlit run app.py` 界面
- [ ] 网络断开也能用（本地工具，不依赖 API）
- [ ] 依次跑完 4 个问题，全程无报错
