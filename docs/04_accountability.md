# 04 问责、独立评估与制裁模块 (`accountability`) 数据采集说明大纲

## 一、数据内容与数据源说明

### 1.1 数据业务含义与构成
前面三个模块记录了“批贷款（`projects`）”、“招投标签合同（`procurement`）”以及“股东投票权与董事会决策（`governance`）”；而第四个模块——**问责、独立评估与制裁模块（`accountability`）**，记录的是**“项目施工运营过程中引发的民众环境社会投诉、项目完工后的独立复盘评估，以及对违规企业的招投标拉黑制裁”**。

这部分数据归口在亚投行内部独立于管理层的监督部门——**投诉解决、评估与廉洁局（`CEIU`）**下，包含以下三大块内容（共生成 5 个 JSON 文件 + 评估报告 PDF 原件）：

1. **受影响民众机制申诉案件库（`Project-Affected People's Mechanism`，简称 `PPM`）**
   - **业务含义**：当亚投行贷款修建地铁、公路、水渠或电网时，如果当地居民认为工程存在征地拆迁补偿不到位、破坏生态环境、施工噪音粉尘扰民等问题，可以直接向亚投行的 `PPM` 机制提交正式申诉（`Submissions`）。该数据记录了亚投行成立以来收到的每一宗民众投诉案件及处理结果。
   - **包含的 2 类表单**：
     - **表 1：直接向亚投行 PPM 提交的申诉案件总表（`ppm_submissions_all.json` 共 45 件，其中印度案件 `india_ppm_submissions.json` 共 14 件，占全行 31.11%，居全行首位）**
       - **样本实例 1（`PPM-2026-40`，印度大阿尼卡特运河现代化改造项目）**：2026 年 4 月收到当地民众投诉，反对在运河底部铺设混凝土衬砌（担忧阻断地下水补给、破坏沿岸树木与农田灌溉）；处理状态显示该项目最终从亚投行备选项目库中撤回取消（`dropped from AIIB's pipeline of proposed projects`）。
       - **样本实例 2（`PPM-2026-37`，印度科钦地铁二期项目）**：当地商铺业主投诉地铁站出入口选址导致商铺被拆迁及生计受损。
       - **样本实例 3（`PPM-2026-36`，印度金奈地铁二期项目）**：当地居民投诉地铁施工造成房屋结构裂缝、粉尘与噪音污染。
     - **表 2：由联合融资伙伴（世行、亚开行、欧投行等）问责机制受理的案件统计表（`ppm_cofinancier_iam_cases.json`，共 12 个联合融资项目、累计 80 宗投诉）**
       - 当某个项目是由亚投行与亚开行（`ADB`）、世行（`World Bank`）或欧洲投资银行（`EIB`）联合出资时，按协议通常直接适用牵头行的环境社会政策，民众投诉也由牵头行的独立问责机制（`IAM`）直接受理。该表记录了这 12 个联合融资项目在伙伴银行收到的 80 宗投诉（其中包含 2 个印度项目：`India: Delhi-Meerut Regional Rapid Transit System` 在亚开行 `ADB AM` 收到 3 宗投诉；`India: Bangalore Metro Rail Project – Line R6` 在欧洲投资银行 `EIB CM` 收到 3 宗投诉）。

2. **项目独立评估与学习报告（`CEIU Evaluation & Learning Reports`）**
   - **业务含义**：项目推进或完工后，由独立的评估局（`CEIU`）对项目是否达到预期目标、遇到哪些实施困难进行独立复盘，发布《项目学习报告》（`Project Learning Report`，简称 `PLR`）及管理层回应。
   - **数据表现（`ceiu_evaluation_reports.json`）**：包含全行已发布的 **6 份项目学习评估报告（`PLR`）** 和 **20 期实践者对话（`Practitioner Dialogues`）**。其中第 6 份 `PLR` 专门针对印度的**古吉拉特邦农村公路项目（`Gujarat Rural Roads Project`，报告全文 PDF 共 1.3 MB，已下载至本地）**。

3. **廉洁制裁与交叉封禁黑名单（`Debarment List`）**
   - **业务含义**：在亚投行及各多边开发银行（世界银行 `WBG`、亚洲开发银行 `ADB`、欧洲复兴开发银行 `EBRD`、非洲开发银行 `AfDB`、泛美开发银行 `IADB`）招投标过程中，因串通围标（`Collusion`）、欺诈（`Fraud`）、腐败行贿（`Corruption`）等违规行为被禁止参与投标的企业与个人黑名单。
   - **数据表现（`debarment_list.json`）**：全表共 **1,465 条**被制裁实体记录，其中所属国家为**印度的被制裁企业/个人共 51 条**（例如印度的 `VENUS IT SOLUTIONS PRIVATE LIMITED` 因围标被世行与亚投行联合封禁）。

---

### 1.2 官网原始数据接口与页面地址

| 子数据项 | 前端展示页面 | 后台数据接口 / 数据源格式 |
| :--- | :--- | :--- |
| **1. PPM 申诉案件总表** | `https://www.aiib.org/en/about-aiib/who-we-are/project-affected-peoples-mechanism/submission/track-all-submission.html` | `https://www.aiib.org/en/about-aiib/who-we-are/project-affected-peoples-mechanism/submission/_common/main.js`（JS 数组 `var baseData = [...]`，属性使用单引号与反引号 `` `...` `` 模板字符串） |
| **2. 联合融资伙伴 IAM 案件统计表** | 同上（`track-all-submission.html` 下方第 2 张表） | 直接内嵌于 `track-all-submission.html` 的 `.table-2 .table-body ul.table-row` 节点中 |
| **3. CEIU 独立评估报告** | `https://www.aiib.org/en/about-aiib/who-we-are/complaints-resolution-evaluation-integrity-unit/evaluation/index.html` | 直接内嵌于该页面 HTML 的 `#table-1`（PLR 报告）与 `#table-2`（实践者对话）表格中 |
| **4. 廉洁制裁黑名单** | `https://www.aiib.org/en/about-aiib/who-we-are/debarment-list/index.html` | `https://www.aiib.org/en/about-aiib/who-we-are/debarment-list/_common/js/debarment-list.js`（标准 JSON 格式的 JS 数组 `var data = [...]`） |

---

### 1.3 采集与落盘流程
- **步骤 1（PPM 申诉案件）**：请求 `submission/_common/main.js`，解析 `var baseData` 数组中的 45 条申诉记录；清理内嵌 HTML 标签，提取案件编号、年份、成员国、关联项目名称与链接、PPM 处理阶段、案件状态、申诉内容摘要与处理备注，并自动识别是否移交联合融资伙伴问责机制（`delegated_to_cofinancier_iam`）以及项目是否已从亚投行管道撤回（`is_project_dropped_from_pipeline`）。同时筛选出 `economy == "India"` 的 14 条涉印案件存为独立文件。
- **步骤 2（联合融资 IAM 统计表）**：请求 `track-all-submission.html`，解析 `.table-2` 中的 12 个联合融资项目在 `ADB AM`、`EBRD IPAM`、`EIB CM`、`IFC CAO`、`World Bank AM` 五家机构收到的投诉件数及小计行（`subtotal`）。
- **步骤 3（CEIU 独立评估报告）**：请求 `evaluation/index.html`，解析 `#table-1` 中的 6 份项目学习报告（PLR）及 `#table-2` 中的 20 期实践者对话；当 `--download-pdfs` 为 `india` 时，自动下载涉印评估报告 PDF（`Gujarat Rural Roads Project` PLR）；当 `--download-pdfs` 为 `all` 时，下载全部 6 份 PLR 评估报告 PDF 至 `data/accountability/pdfs/`。
- **步骤 4（制裁黑名单）**：请求 `debarment-list.js`，解析全部 1,465 条被制裁企业与个人的名称、地址、所属经济体、发起制裁机构、违规行为类型及封禁起止日期。

---

### 1.4 采集命令与参数说明

```bash
# 1. 断点续爬模式：抓取全部问责/评估/制裁 JSON 并下载涉印 CEIU 评估报告 PDF
uv run python main.py --types accountability --download-pdfs india --mode resume

# 2. 下载全部 6 份 CEIU 项目学习评估报告 PDF（不限于印度）
uv run python main.py --types accountability --download-pdfs all --mode resume

# 3. 从头完整复现采集：自动备份已有的 accountability 旧数据并重新抓取
uv run python main.py --types accountability --download-pdfs india --mode reset
```

---

## 二、本地输出文件清单

| 文件路径 | 对应数据源 | 内容说明 | 当前记录条数 / 文件大小 |
| :--- | :--- | :--- | :--- |
| `data/accountability/ppm_submissions_all.json` | `submission/_common/main.js` | 全行所有向 PPM 直接提交的民众环境社会申诉案件 | 45 条 |
| `data/accountability/india_ppm_submissions.json` | `submission/_common/main.js` | 从全量申诉中筛选出的印度项目申诉案件子集 | 14 条 |
| `data/accountability/ppm_cofinancier_iam_cases.json` | `track-all-submission.html` | 联合融资项目在伙伴银行（ADB/EIB/WB 等）收到的投诉统计表 | 12 个项目（累计 80 宗投诉，含 2 个印度项目） |
| `data/accountability/ceiu_evaluation_reports.json` | `evaluation/index.html` | CEIU 发布的项目学习评估报告（PLR）与实践者对话列表 | 6 份 PLR + 20 期对话 |
| `data/accountability/pdfs/*.pdf` | 评估页与 PPM 附件 | 涉印 CEIU 评估报告 PDF（古吉拉特邦农村公路项目，`1.3 MB`）与因投诉撤回的印度大阿尼卡特运河项目 PSI 文件（`138 KB`） | 2 个 PDF 文件（`india` 模式）/ 7 个 PDF 文件（`all` 模式） |
| `data/accountability/debarment_list.json` | `debarment-list.js` | 全行廉洁制裁与多边开发银行交叉封禁黑名单（含 51 家印度实体） | 1,465 条 |
| `data/accountability.json` | 模块汇总 | 汇总 PPM 申诉、CEIU 评估与制裁名单的主 JSON 文件 | 1,516 条 |

---

## 三、数据表字段说明

### 3.1 PPM 申诉案件表 (`ppm_submissions_all.json` 与 `india_ppm_submissions.json`)
- `record_id`：内部唯一键（如 `"ppm:PPM-2026-40"`）。
- `case_no`：案件官方编号（原始键 `no`，如 `"PPM-2026-40"`）。
- `year`：申诉年份整数（原始键 `year`）。
- `economy`：项目所属成员国名称（原始键 `member`，如 `"India"`）。
- `project_name`：被投诉的项目名称（从原始键 `pname` 提取纯文本；若投诉时尚未立项或未指明具体项目则为 `"—"` 或空字符串）。
- `project_urls`：从 `pname` 超链接提取的关联项目详情页或文档 URL 数组。
- `ppm_function`：PPM 介入处理阶段（原始键 `ppm`，如 `"Problem-Solving"`、`"Compliance Review"`，未进入实质阶段前为 `"N/A"`）。
- `status`：案件当前状态（原始键 `status`，如 `"Ineligible"`、`"Under eligibility screening"`、`"Closed during eligibility screening..."`）。
- `submission_summary`：申诉人身份与投诉核心问题摘要（从原始键 `submission` 清理 HTML 后提取）。
- `remarks`：收件日期、立案审查结论及后续跟进说明全文（从原始键 `remarks` 清理 HTML 后提取）。
- `delegated_to_cofinancier_iam`：字符串数组，识别 `remarks` 中提及负责受理该项目的联合融资伙伴机构（如 `["ADB"]`、`["World Bank"]`）。
- `is_project_dropped_from_pipeline`：布尔值，标识 `remarks` 中是否注明该项目已从亚投行备选管道中撤回取消。

### 3.2 联合融资伙伴 IAM 案件统计表 (`ppm_cofinancier_iam_cases.json`)
顶层包含 `subtotal`（各机构投诉件数合计对象，总计 `80` 件）与 `cofinancier_iam_cases`（12 个联合融资项目数组）。每条项目记录包含：
- `no`：序号整数（`1` 至 `12`）。
- `economy`：项目所属国家（如 `"India"`）。
- `project_name`：项目名称（如 `"Delhi-Meerut Regional Rapid Transit System"`）。
- `project_url`：亚投行项目详情页链接。
- `adb_am_count`：亚洲开发银行问责机制（`ADB AM`）收到的投诉件数整数。
- `ebrd_ipam_count`：欧洲复兴开发银行问责机制（`EBRD IPAM`）收到的投诉件数整数。
- `eib_cm_count`：欧洲投资银行投诉机制（`EIB CM`）收到的投诉件数整数。
- `ifc_cao_count`：国际金融公司合规顾问/申诉专员（`IFC CAO`）收到的投诉件数整数。
- `world_bank_am_count`：世界银行问责机制（`World Bank AM`）收到的投诉件数整数。
- `total_count`：该项目在上述伙伴机构收到的投诉总件数整数。

### 3.3 CEIU 独立评估报告表 (`ceiu_evaluation_reports.json`)
- `plr_reports` 数组（6 条）：
  - `record_id`：内部唯一键（如 `"ceiu_plr:6"`）。
  - `date`：报告发布年月（如 `"December 2024"`）。
  - `sector`：行业分类字符串。
  - `project_name`：被评估项目名称（如 `"Gujarat Roads Project"`）。
  - `project_url`：关联链接。
  - `evaluation_documents`：报告附件数组，每个元素含 `title`、`url` 及下载后的 `local_path`。
- `practitioner_dialogues` 数组（20 条）：包含 `record_id`、`date`、`topic`、`links`。

### 3.4 廉洁制裁黑名单 (`debarment_list.json`)
- `record_id`：内部唯一键。
- `entity_name`：被制裁企业或个人名称（原始键 `NAME`）。
- `address`：注册地址或所在地（原始键 `ADDRESS`）。
- `economy`：所属国家/经济体（原始键 `ECONOMY`，如 `"India"`）。
- `debarred_by`：作出制裁决定的多边开发银行缩写（原始键 `DEBARRED BY`，如 `"AIIB"`、`"WBG"`、`"ADB"`、`"AfDB"`、`"EBRD"`、`"IADB"`）。
- `prohibited_practice`：违规行为类别（原始键 `PROHIBITED PRACTICE`，如 `"Fraud"`、`"Collusion"`、`"Corruption"`、`"Obstruction"`）。
- `from_date`：封禁生效起始日期（原始键 `FROM`）。
- `to_date`：封禁解除日期或状态（原始键 `TO`，如 `"Ongoing"`、`"Permanent"` 或具体日期）。
- `date_added_by_aiib`：亚投行列入名单日期（原始键 `DATE ADDED BY AIIB`）。
- `other_notes`：补充说明（原始键 `OTHER NOTES`）。

---

## 四、数据缺失情况与已知边界
- 在 `ppm_submissions_all.json` 中，部分申诉案件因投诉人针对的是尚未立项的潜在项目或未指明具体项目名称，官网数据源 `pname` 字段为 `"—"` 或空字符串 `""`。
- 在 `ceiu_evaluation_reports.json` 中，官网 `#table-1` 表格仅设 2 列（报告链接列与发布日期列），未单独设置行业（`sector`）列，因此 `sector` 字段为空字符串 `""`。
