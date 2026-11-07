# 03 治理与投票权模块 (`governance`) 数据采集说明大纲

## 一、数据内容与数据源说明

### 1.1 数据业务含义与构成
如果把亚投行比作一家跨国金融机构，前面两个模块（`projects` 和 `procurement`）记录的是它的业务放贷与工程招标；而**治理与投票权模块（`governance`）记录的是这家银行的“股权结构、最高权力机构（理事会）与常设决策机构（董事会）”**。

亚投行官网将这部分信息放在顶部菜单 `WHO WE ARE` -> `GOVERNANCE` 栏目下，由以下三大部分（共 6 个数据源、本地生成 7 个 JSON 文件 + 8 份年会纪要 PDF）组成：

1. **成员国认缴股本与投票权表（`Members and Prospective Members of the Bank`）**
   - **业务含义**：记录亚投行全部 **106 个正式成员经济体**（以及 4 个准成员）各自认缴了多少股本（百万美元）、占全行总股本的百分比，以及由此折算出的**投票权票数与投票权占比**。
   - **数据表现（以印度为例）**：全行认缴总股本为 `97,632.2` 百万美元，总投票权为 `1,136,676` 票。其中：
     - 第 1 大股东为**中国**：认缴 `29,780.4` 百万美元（占 `30.5026%`），投票权 `299,691` 票（占 **`26.3656%`**）；
     - 第 2 大股东为**印度**：2016 年 1 月 11 日加入，属域内成员（`Regional`），认缴 `8,367.3` 百万美元（占 `8.5702%`），投票权 `85,560` 票（占 **`7.5272%`**）；
     - 第 3 至 5 大股东依次为俄罗斯（投票权 `5.9163%`）、德国（`4.111%`）、韩国（`3.4552%`）。

2. **理事会（`Board of Governors`）——最高权力机构**
   - **业务含义**：每个成员国委派 1 名理事（`Governor`，通常由各国财政部长或央行行长兼任）和 1 名副理事（`Alternate Governor`）。理事会每年召开一次年会，决定接纳新成员、增资、修改章程、选举行长等最高级别事项。
   - **包含的 3 类数据**：
     - **各国理事与副理事名单（共 105 条）**：例如印度的理事为印度财政部长 `Mrs. Nirmala Sitharaman`，副理事为印度财政部经济事务秘书 `Ms. Anuradha Thakur`。
     - **理事会历年正式决议（`Resolutions`，共 154 条）**：2016–2026 年间理事会表决通过的所有决议编号、日期、标题、决议正文及附件 PDF 链接（例如第 63 号决议记录了 2018 年孟买年会的致谢决议）。
     - **理事会历届年会正式纪要（`Annual Meeting Proceedings`，共 8 份 PDF）**：第 1 届至第 9 届理事会年会的完整会议纪要 PDF（其中 2018 年第 3 届年会由印度在孟买主办，纪要中包含 61 处涉印记录）。

3. **董事会（`Board of Directors`）——日常审批贷款项目的核心决策机构**
   - **业务含义**：各国财政部长（理事）平时在本国上班，不负责亚投行的日常运转；真正负责审批每一笔贷款项目、监督银行日常运营的是由 **12 名执行董事** 组成的董事会。106 个成员国被划分为 **12 个选区（`Constituencies`）**，每个选区推选 1 名董事（`Director`）和 1–2 名副董事（`Alternate`）。
   - **包含的 2 类数据**：
     - **12 个董事选区构成表（共 12 条）**：记录每个选区由哪些国家组成、现任董事是谁、国籍是哪里。**在全行 12 个选区中，第 10 选区（`Constituency 10`）是唯一一个仅由单一主权国家（`India`）独占的选区**（中国所在的第 5 选区包含中国大陆与中国香港 2 个成员，其余选区均由 5 至 22 个国家联合组成）。第 10 选区现任董事为印度籍 `Anu P MATHAI`，副董事为印度籍 `Tulsipriya RAJKUMARI`。
     - **董事会历次会议纪要列表（`Minutes of Board of Directors Meetings`，共 127 条）**：2016–2026 年间董事会历次开会审理项目与政策的会议日期及会议纪要 PDF 链接。

---

### 1.2 官网原始数据接口与页面地址

| 子数据项 | 前端展示页面 | 后台数据接口 / 数据源格式 |
| :--- | :--- | :--- |
| **1. 成员国股本与投票权** | `https://www.aiib.org/en/about-aiib/governance/members-of-bank/index.html` | `https://www.aiib.org/en/about-aiib/governance/members-of-bank/_common/js/voting-power.js`（JS 变量赋值文本，含 `regionalData`、`nonRegionalData`、`prospectiveRegionalData`、`prospectiveNonRegionalData` 四个数组） |
| **2. 理事会成员名单** | `https://www.aiib.org/en/about-aiib/governance/board-governors/index.html` | 直接内嵌于该页面 HTML 的 `<div class="table-row">` 节点中 |
| **3. 理事会历年决议** | `https://www.aiib.org/en/about-aiib/governance/board-governors/resolutions/index.html` | `https://www.aiib.org/en/about-aiib/governance/board-governors/_common/resData.js`（JS 数组 `var resData = [...]`，其中正文 `text_copy` 使用反引号 `` `...` `` 模板字符串包裹） |
| **4. 理事会历届年会纪要** | `https://www.aiib.org/en/about-aiib/governance/board-governors/annual-meeting-proceedings/index.html` | 直接内嵌于该页面 HTML 的 PDF 下载链接（共 8 份 PDF） |
| **5. 董事会 12 个选区构成** | `https://www.aiib.org/en/about-aiib/governance/board-directors/board-members/index.html` | 直接内嵌于该页面 HTML 的 `table.scratch-table` 表格中 |
| **6. 董事会会议纪要列表** | `https://www.aiib.org/en/about-aiib/governance/board-directors/More-Meeting-Minutes/index.html` | 直接内嵌于该页面 HTML 的 `.Custom_list` 列表节点中 |

---

### 1.3 采集与落盘流程
- **步骤 1（股本与投票权）**：请求 `voting-power.js`，使用 `json.JSONDecoder().raw_decode()` 依次提取域内成员、域外成员及准成员数组；将 `Total Regional`、`Total Non-Regional`、`Grand Total` 三行汇总行分离至 `totals` 字典，其余 106 个正式成员存入 `members` 数组，并将认缴金额与投票权占比转换为浮点数。
- **步骤 2（理事会名单、决议与年会纪要）**：
  1. 请求 `board-governors/index.html`，解析每个成员经济体的理事（`Governor`）与副理事（`Alternate`）姓名及职务头衔；
  2. 请求 `resData.js`，解析包含反引号多行文本的 154 条理事会决议，提取决议编号、日期、标题、正文与 PDF 链接；
  3. 请求 `annual-meeting-proceedings/index.html`，提取第 1 至第 9 届年会纪要 PDF 链接；当 `--download-pdfs` 为 `india` 或 `all` 时，下载这 8 份 PDF 至 `data/governance/pdfs/annual_proceedings/`，并逐页检索提取包含 `India`、`Indian`、`Mumbai`、`New Delhi`、`Sitharaman` 等关键词的段落与页码，生成 `india_governor_proceedings_mentions.json`。
- **步骤 3（董事会 12 个选区与会议纪要）**：
  1. 请求 `board-directors/board-members/index.html`，解析 12 个选区的董事姓名、董事国籍、副董事列表、选区覆盖成员国列表，并计算 `constituency_members_count` 与 `is_single_country_constituency` 布尔标识；
  2. 请求 `board-directors/More-Meeting-Minutes/index.html`，提取全部 127 份董事会会议纪要的会议日期、年份与 PDF 链接；当 `--download-pdfs` 为 `india` 或 `all` 时，下载这 127 份董事会会议纪要 PDF 至 `data/governance/pdfs/board_minutes/` 目录。

---

### 1.4 采集命令与参数说明

```bash
# 1. 断点续爬并下载全部治理模块 PDF（含 8 份理事会年会纪要 PDF + 127 份董事会会议纪要 PDF）
uv run python main.py --types governance --download-pdfs india --mode resume

# 2. 从头完整复现采集：自动备份已有的 governance 旧数据并重新抓取
uv run python main.py --types governance --download-pdfs india --mode reset

# 3. 仅采集治理模块结构化 JSON（不下载 PDF 附件）
uv run python main.py --types governance --download-pdfs none --mode reset
```

---

## 二、本地输出文件清单

| 文件路径 | 对应数据源 | 内容说明 | 当前记录条数 / 文件大小 |
| :--- | :--- | :--- | :--- |
| `data/governance/members_voting_power.json` | `voting-power.js` | 106 个正式成员与 4 个准成员的认缴股本、投票权票数与占比，以及域内/域外/全行汇总值 | 106 个正式成员 + 4 个准成员 |
| `data/governance/board_of_governors.json` | `board-governors/index.html` | 各成员国现任理事（Governor）与副理事（Alternate）姓名及官职 | 105 条 |
| `data/governance/governors_resolutions.json` | `resData.js` | 2016–2026 年理事会历次通过的正式决议及正文 | 154 条 |
| `data/governance/governors_annual_proceedings.json` | `annual-meeting-proceedings/index.html` | 历届理事会年会正式纪要 PDF 索引 | 8 条 |
| `data/governance/pdfs/annual_proceedings/*.pdf` | 年会纪要附件 | 2016–2024 历届理事会年会完整纪要 PDF 原件 | 8 个 PDF 文件 |
| `data/governance/india_governor_proceedings_mentions.json` | 年会纪要 PDF 解析 | 从 8 份年会纪要 PDF 中提取的所有涉印段落、页码与上下文 | 8 份文档（共 111 处涉印段落） |
| `data/governance/board_of_directors_constituencies.json` | `board-members/index.html` | 董事会 12 个选区的董事、副董事、国籍与所代表成员国列表 | 12 条（对应 12 个选区） |
| `data/governance/board_of_directors_meeting_minutes.json` | `More-Meeting-Minutes/index.html` | 2016–2026 年董事会历次会议纪要日期、PDF 链接与本地文件路径 | 127 条 |
| `data/governance/pdfs/board_minutes/*.pdf` | 董事会会议纪要附件 | 2016–2026 年董事会历次常规会议纪要 PDF 原件 | 127 个 PDF 文件 |
| `data/governance.json` | 模块汇总 | 汇总上述全部治理子表的主 JSON 文件 | 1 个汇总对象 |

---

## 三、数据表字段说明

### 3.1 成员国股本与投票权表 (`members_voting_power.json`)
顶层字段包含 `update_date`（统计截止日期，如 `"March 31, 2026"`）、`members_count`（`106`）、`regional_count`（`53`）、`non_regional_count`（`53`）、`totals`（域内/域外/总计汇总对象）、`prospective_members`（4 个准成员数组）以及 `members`（106 个正式成员数组）。`members` 数组中每条记录包含以下 8 个字段：
- `record_id`：内部唯一键（如 `"member:India"`）。
- `economy`：成员经济体英文名称（如 `"India"`）。
- `member_group`：成员分组（域内成员 `"Regional"` 或域外成员 `"Non-Regional"`）。
- `join_date`：正式加入亚投行的日期字符串（如 `"Jan 11, 2016"`）。
- `subscription_amount_usd_millions`：认缴股本金额（百万美元浮点数，如印度为 `8367.3`）。
- `subscription_percent`：认缴股本占全行总股本的百分比（浮点数，如印度为 `8.5702`）。
- `voting_power_votes`：拥有的投票权总票数（整数，如印度为 `85560`）。
- `voting_power_percent`：投票权占全行总票数的百分比（浮点数，如印度为 `7.5272`）。

### 3.2 理事会成员名单 (`board_of_governors.json`)
- `record_id`：内部唯一键（如 `"governor:India"`）。
- `economy`：成员经济体名称。
- `governor_name`：理事姓名（如 `"Mrs. Nirmala Sitharaman"`）。
- `governor_title`：理事在本国担任的职务（如 `"Minister of Finance"`）。
- `alternate_name`：副理事姓名（如 `"Ms. Anuradha Thakur"`）。
- `alternate_title`：副理事在本国担任的职务（如 `"Secretary (Economic Affairs)"`）。

### 3.3 理事会决议 (`governors_resolutions.json`)
- `record_id`：内部唯一键。
- `resolution_no`：决议编号与简称（如 `"63. Appreciation"`）。
- `date`：决议通过日期字符串（如 `"June 26, 2018"`）。
- `year`：决议年份整数。
- `title`：决议标题。
- `resolution_text`：从 HTML 清理后的纯文本决议正文。
- `pdf_url`：决议官方签字版 PDF 链接（部分页面内直接展示全文的决议无独立 PDF 链接，该字段为空字符串 `""`）。

### 3.4 董事会 12 个选区表 (`board_of_directors_constituencies.json`)
- `record_id`：内部唯一键（如 `"constituency:10:India"`）。
- `constituency_index`：选区序号（整数 `1` 至 `12`）。
- `director_name`：现任执行董事姓名（如 `"Anu P MATHAI"`）。
- `director_nationality`：现任执行董事所属国籍（如 `"India"`）。
- `constituency_url`：该执行董事个人履历详情页链接。
- `alternates`：副董事对象数组，每个元素含 `name`（副董事姓名）与 `nationality`（副董事国籍）。
- `constituency_members`：该选区所代表的成员国/地区名称字符串数组（如第 10 选区为 `["India"]`）。
- `constituency_members_count`：该选区包含的成员数量整数（如第 10 选区为 `1`）。
- `is_single_country_constituency`：布尔值，标识该选区是否仅由单一成员独占（全行仅第 10 选区印度为 `true`）。

### 3.5 董事会会议纪要列表 (`board_of_directors_meeting_minutes.json`)
- `record_id`：内部唯一键。
- `meeting_date`：会议召开日期字符串（如 `"March 26, 2026"`）。
- `meeting_year`：会议年份整数。
- `pdf_url`：会议纪要完整 PDF 下载链接。
- `local_path`：当启用 `--download-pdfs india` 或 `all` 下载后，记录本地 PDF 相对路径（如 `"governance/pdfs/board_minutes/..."`）。

---

## 四、数据缺失情况与已知边界
- 在 `board_of_governors.json`（共 105 条）中，部分成员国某时期若理事或副理事职位处于换届空缺状态，官网表格显示为 `"Vacant"`，采集结果原样保留 `"Vacant"` 字符串。
- 在 `governors_annual_proceedings.json` 中，官网将首届年会（2016 年）纪要文件命名为 `Summary-of-Proceedings.pdf`，其文件名与链接文本中均未包含四位年份数字，因此 `year` 字段解析值为 `null`。
