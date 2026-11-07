"""Parser 纯函数解析器单元测试。"""

from __future__ import annotations

from aiib_crawler.parser import (
    parse_ceiu_evaluation_html,
    parse_debarment_list_js,
    parse_directors_json,
    parse_governors_json,
    parse_governors_resolutions_js,
    parse_meeting_minutes_html,
    parse_ppm_submissions_js,
    parse_ppo_data_js,
    parse_project_detail_html,
    parse_projects_js,
    parse_usd_millions,
    parse_voting_power_js,
)


def test_parse_usd_millions() -> None:
    assert parse_usd_millions("USD140.61 million") == 140.61
    assert parse_usd_millions("USD 1,250.5 million") == 1250.5
    assert parse_usd_millions("USD 1.5 billion") == 1500.0
    assert parse_usd_millions("") is None


def test_parse_projects_js() -> None:
    sample_projects_js = """
    var data=[
      {"date":"2021","pos":"approved","economy":"India","sector":"Urban","financing_type":"Sovereign","project_type":"Cofinanced","name":"Punjab Municipal Services Improvement Project","approved_funding":"USD105.00 million","committed_funding":"","proposed_funding":"","special_funding":"","status":"Approved","path":"/en/projects/details/2021/approved/India-Punjab.html"}
    ];
    """
    rows = parse_projects_js(sample_projects_js)
    assert len(rows) == 1
    assert rows[0]["economy"] == "India"
    assert rows[0]["approval_year"] == 2021
    assert rows[0]["approved_funding_usd_millions"] == 105.0
    assert rows[0]["detail_url"].endswith("/en/projects/details/2021/approved/India-Punjab.html")


def test_parse_project_detail_html_extracts_derived_metrics() -> None:
    sample_html = """
    <html>
      <head><title>Approved Projects: India: Punjab Municipal Services Improvement Project</title></head>
      <body>
        <h1 class="title-page">India: Punjab Municipal Services Improvement Project</h1>
        <div class="summary-item">
          <div class="summary-item-name">STATUS</div>
          <div class="summary-item-value">Approved</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">MEMBER</div>
          <div class="summary-item-value">India</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">SECTOR</div>
          <div class="summary-item-value">Urban</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">E&S CATEGORY</div>
          <div class="summary-item-value">A</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">PROJECT NUMBER</div>
          <div class="summary-item-value">000379</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">APPROVED FUNDING</div>
          <div class="summary-item-value">USD105 million</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">FINANCING TYPE</div>
          <div class="summary-item-value">Sovereign</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">CONCEPT REVIEW</div>
          <div class="summary-item-value">April 30, 2020</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-name">FINANCING APPROVAL</div>
          <div class="summary-item-value">June 24, 2021</div>
        </div>
        <div class="project-paragraph">
          <div class="paragraph">
            <h2>OBJECTIVE</h2>
            <p>To improve water supply in Amritsar and Ludhiana in Punjab.</p>
          </div>
          <div class="paragraph">
            <h2>ENVIRONMENTAL AND SOCIAL INFORMATION</h2>
            <p>The project will be co-financed with the World Bank (IBRD) and World Bank's Environmental and Social Policy applies.</p>
          </div>
          <div class="paragraph">
            <h2>BORROWER</h2>
            <p>Republic of India</p>
          </div>
        </div>
        <div class="feature-documents">
          <div class="doc">
            <div class="project-sub-title">AIIB DOCUMENTS</div>
            <div class="link">
              <a href="/en/projects/_download/PD-000379.pdf">Project Document</a>
              <span class="date">July 2021</span>
            </div>
            <div class="link">
              <a href="/en/projects/_download/PIMR-000379.pdf">Project Implementation Monitoring Report</a>
              <span class="date">June 2025</span>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    detail = parse_project_detail_html(sample_html, url="https://www.aiib.org/en/projects/000379.html")
    assert detail["project_number"] == "000379"
    assert detail["economy"] == "India"
    assert detail["es_category"] == "A"
    assert detail["approved_funding_usd_millions"] == 105.0
    assert detail["approval_lag_days"] == 420
    assert detail["is_cofinanced"] is True
    assert "World Bank" in detail["cofinanciers"]
    assert "Cofinancier Policy" in detail["applicable_es_policy"]
    assert "Punjab" in detail["indian_states"]
    assert detail["documents_count"] == 2
    assert detail["pimr_count"] == 1


def test_parse_ppo_data_js() -> None:
    sample_js = """
    var ppoData = [
    {id:"Nov 5, 2026",cd:"",mb:"India",pj:"Assam Transmission Project",ds:"Substation",cr:"Lumino Industries",sd:"Aug. 21, 2026",pc:"INR 2,078,489,885.00",st:"Energy",ct:"Contract Awards",tp:"Contract Award Notice",dc:"/en/projects/award.pdf"}
    ];
    """
    rows = parse_ppo_data_js(sample_js)
    assert len(rows) == 1
    assert rows[0]["economy"] == "India"
    assert rows[0]["contract_currency"] == "INR"
    assert rows[0]["contract_amount"] == 2078489885.0
    assert rows[0]["category"] == "Contract Awards"


def test_parse_governance_parsers() -> None:
    voting_js = """
    var update_date = ["March 31, 2026"];
    var regional_members = ["India| Jan 11, 2016| 8,367.3 |8.5702%| 85,560 |7.5272%"];
    var nonregional_members = ["Germany| Jan 11, 2016| 4,484.2 |4.5930%| 46,729 |4.1110%"];
    var prospective_members = ["Kuwait*"];
    """
    vp = parse_voting_power_js(voting_js)
    assert vp["update_date"] == "March 31, 2026"
    assert vp["members_count"] == 2
    assert vp["members"][0]["economy"] == "India"
    assert vp["members"][0]["subscription_amount_usd_millions"] == 8367.3
    assert vp["members"][0]["voting_power_percent"] == 7.5272

    gov_json = """
    {"content":[{"member":[{"country":"<div>India</div>"}],"governor":"<div class='sort-governor'>Ms. Nirmala Sitharaman</div><p class='sub'>Minister of Finance</p>","alertnate":"<div class='sort-alternate'>Mr. Ajay Seth</div><p class='sub'>Secretary</p>"}]}
    """
    govs = parse_governors_json(gov_json)
    assert len(govs) == 1
    assert govs[0]["economy"] == "India"
    assert govs[0]["governor_name"] == "Ms. Nirmala Sitharaman"

    dir_json = """
    {"content":[{"dir":[{"name":"<div class='name'>Anu P MATHAI</div><p class='nationality'>(India)</p><a href='/en/dir/india.html'>MORE</a>"}],"nates":"<div class='font-copy-16-black'>Tulsipriya RAJKUMARI</div><p class='font-copy-14-black'>(India)</p>","members":"<p>India</p>"}]}
    """
    dirs = parse_directors_json(dir_json)
    assert len(dirs) == 1
    assert dirs[0]["director_name"] == "Anu P MATHAI"
    assert dirs[0]["is_single_country_constituency"] is True
    assert dirs[0]["constituency_members"] == ["India"]

    res_js = """
    var resData = {"content":[{"title":"2016-1","text_copy":"<a href='/en/res1.pdf'>Resolution 1</a>","date":"Jan 16, 2016"}]};
    """
    res_list = parse_governors_resolutions_js(res_js)
    assert len(res_list) == 1
    assert res_list[0]["resolution_no"] == "2016-1"
    assert res_list[0]["year"] == 2016

    minutes_html = """
    <div class="members-table"><div class="table-pc"><div class="table-body">
      <ul class="table-row"><li><span>March 12, 2025</span></li><li class="dld-icon"><a href="/en/minutes_2025.pdf">PDF</a></li></ul>
    </div></div></div>
    """
    mins = parse_meeting_minutes_html(minutes_html)
    assert len(mins) == 1
    assert mins[0]["meeting_year"] == 2025


def test_parse_accountability_parsers() -> None:
    ppm_js = """
    var baseData=[{
      'no':'PPM-2026-40',
      'year':'2026',
      'member':'India',
      'pname':'<a href="https://www.aiib.org/en/p1.pdf">Grand Anicut Canal System</a>',
      'ppm':'N/A',
      'submission':`<b>Issues:</b> Concrete lining`,
      'status':'Ineligible',
      'remarks':`The project was dropped from AIIB's pipeline of proposed projects.`,
      'flag':true
    }];
    """
    ppm_cases = parse_ppm_submissions_js(ppm_js)
    assert len(ppm_cases) == 1
    assert ppm_cases[0]["case_no"] == "PPM-2026-40"
    assert ppm_cases[0]["economy"] == "India"
    assert ppm_cases[0]["is_project_dropped_from_pipeline"] is True

    ceiu_html = """
    <table id="table-1"><tbody>
      <tr>
        <td>July 2022</td>
        <td>Transport</td>
        <td><a href="/en/eval/gujarat_plr.pdf">PLR Report</a></td>
        <td><a href="/en/projects/gujarat.html">Gujarat Rural Roads Project</a></td>
      </tr>
    </tbody></table>
    """
    ceiu = parse_ceiu_evaluation_html(ceiu_html)
    assert len(ceiu["plr_reports"]) == 1
    assert ceiu["plr_reports"][0]["project_name"] == "Gujarat Rural Roads Project"

    debar_js = """
    var data=[{"NAME":"Test Corp","ADDRESS":"Delhi","ECONOMY":"India","DEBARRED BY":"ADB","PROHIBITED PRACTICE":"Fraud","FROM":"2024","TO":"2027","DATE ADDED BY AIIB":"2024","OTHER NOTES":""}];
    """
    debar = parse_debarment_list_js(debar_js)
    assert len(debar) == 1
    assert debar[0]["economy"] == "India"
