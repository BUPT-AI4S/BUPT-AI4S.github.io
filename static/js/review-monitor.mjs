import {loadMonitorSnapshot} from './review-monitor-live.mjs?v=20261116-owner-scope-cache-1';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (n) => n == null ? '未知' : typeof n === 'string' ? n : Number(n).toLocaleString('zh-CN');
const ratio = s => Number.isFinite(s.final_included) && s.final_included >= 0 && Number.isFinite(s.papers) && s.papers > 0 ? s.final_included / s.papers : null;
const percent = n => n == null ? '未知' : `${(n * 100).toFixed(1)}%`;
const compareDescending = (a,b) => a == null ? (b == null ? 0 : 1) : b == null ? -1 : b - a;
const requiredAbstracts = s => s.abstract_supplement_required ?? s.missing_abstract;
const safeUrl = (u) => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol) ? x.href : ''; } catch { return ''; } };
let data, selected = [];
const year = $('#year'), owner = $('#owner'), search = $('#search'), status = $('#status'), sort = $('#sort');
function options(select, values, label) { select.innerHTML = `<option value="">${label}</option>` + values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join(''); }
function render() {
  const y = data.years.find(x => String(x.year) === year.value); if (!y) return;
  const old = owner.value; const owners = [...new Set(y.sources.map(s => s.owner).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN')); options(owner, owners, '全部负责人'); owner.value = owners.includes(old) ? old : '';
  const query = search.value.trim().toLowerCase();
  selected = y.sources.map(s => y.year === 2024 ? {...s, papers_missing_abstract:0, missing_abstract:0, abstract_supplement_required:0, final_missing_abstract:0, unsynced_missing_abstract:0, abstract_recovered:0, abstract_not_required:0, abstract_full_text_reviewed:0, abstract_closed_by_owner:0, issues:s.issues.filter(x=>!x.startsWith('AI4S候选缺少摘要：') && !x.startsWith('个人审核已纳入但尚未同步候选总集：')), actions:s.actions.filter(x=>x!=='为缺摘要的AI4S候选补充可核实的摘要或证据，无法判断的论文标为待定。' && x!=='核对已纳入论文身份和范围，补充缺失的原摘要后同步候选总集。')} : s).filter(s => (!owner.value || s.owner === owner.value) && (!query || `${s.title} ${s.code}`.toLowerCase().includes(query)) && (status.value === 'all' || (status.value === 'issues' && s.issues.length) || (status.value === 'missing' && s.official_total == null && !s.reference_check) || (status.value === 'pending' && s.decisions && (s.decisions.pending || s.decisions.unreviewed))));
  if (sort?.value === 'included') selected.sort((a,b)=>compareDescending(a.final_included,b.final_included));
  if (sort?.value === 'ratio') selected.sort((a,b)=>compareDescending(ratio(a),ratio(b)));
  const ownerActions = $('#owner-actions'); if (ownerActions) { ownerActions.hidden = !owner.value; if (owner.value) ownerActions.href = `https://github.com/BUPT-AI4S/ai4s-crawler/blob/main/reviews/${y.year}/actions/${encodeURIComponent(owner.value)}.md`; }
  $('#view-title').textContent = owner.value ? `${owner.value} · 工作分屏` : '工作总览';
  $('#scope').textContent = `统计当前筛选的 ${selected.length} 个来源；采集快照 ${y.captured_at || '未提供'}。${lastUpdateText(y)}`;
  const sum = key => selected.reduce((n,s)=>n+(s[key] ?? 0),0);
  const knownMetric = (name,key) => [name, selected.some(s=>s[key]!=null)?sum(key):null];
  const ratioSources = selected.filter(s=>ratio(s) != null);
  const overallRatio = ratioSources.length ? ratioSources.reduce((n,s)=>n+s.final_included,0) / ratioSources.reduce((n,s)=>n+s.papers,0) : null;
  const ratioLabel = 'AI4S占比';
  const metrics = [['来源条目',selected.length],['快照采集论文',selected.some(s=>s.papers!=null)?sum('papers'):null],knownMetric('全量缺摘要','papers_missing_abstract'),['初筛候选',sum('candidates')],knownMetric('精筛纳入','final_included'),[ratioLabel,percent(overallRatio)],knownMetric('纳入缺摘要','final_missing_abstract'),['候选待补摘要',selected.some(s=>requiredAbstracts(s)!=null)?selected.reduce((n,s)=>n+(requiredAbstracts(s) ?? 0),0):null],['已纳入待同步',selected.some(s=>s.unsynced_included!=null)?sum('unsynced_included'):null],['待同步缺摘要',selected.some(s=>s.unsynced_missing_abstract!=null)?sum('unsynced_missing_abstract'):null],['总量待核对',selected.filter(s=>s.official_total==null && !s.reference_check).length]];
  $('#metrics').innerHTML=metrics.map(([name,value])=>`<div class="metric"><strong>${fmt(value)}</strong><span>${name}</span></div>`).join('');
  $('#count').textContent=`${selected.length} 个来源`; const empty=$('#empty'); if (empty) empty.hidden=selected.length>0;
  $('#list').innerHTML=selected.map(s=>{
    const decisions=s.decisions ? `纳入 ${s.decisions.include} · 排除 ${s.decisions.exclude} · 待定 ${s.decisions.pending} · 未审 ${s.decisions.unreviewed}` : '暂无逐篇交付';
    const ref=s.files.map((file,i)=>`<a href="${esc(data.repository + file.split('/').map(encodeURIComponent).join('/'))}" target="_blank" rel="noopener">交付文件 ${i+1}</a>`).join('');
    const history=(s.historical_review_files || []).map((file,i)=>`<a href="${esc(data.repository + file.split('/').map(encodeURIComponent).join('/'))}" target="_blank" rel="noopener">历史交付 ${i+1}</a>`).join('');
    const evidence=s.evidence_urls.map(safeUrl).filter(Boolean).map((url,i)=>`<a href="${esc(url)}" target="_blank" rel="noopener">核验依据 ${i+1}</a>`).join('');
    const check=s.reference_check ? `<br>替代来源核对完成：${esc(s.reference_check.source)} ${fmt(s.reference_check.total)} 篇（${esc(s.reference_check.scope)}；${esc(s.reference_check.checked_at)}）` : '';
    return `<details><summary><span class="source-name"><strong>${esc(s.title)}</strong><small>${esc(s.code)} · ${esc(s.venue_decision || '刊会结论未填写')}</small></span><span class="summary-owner">${esc(s.owner || '负责人未知')}</span><span class="summary-stats"><span>采集 <strong>${fmt(s.papers)}</strong></span><span>全量缺摘要 <strong>${fmt(s.papers_missing_abstract)}</strong></span><span>初筛 <strong>${fmt(s.candidates)}</strong></span><span>纳入 <strong>${fmt(s.final_included)}</strong></span><span>纳入缺摘要 <strong>${fmt(s.final_missing_abstract)}</strong></span><span>候选待补 <strong>${fmt(requiredAbstracts(s))}</strong></span><span>待同步 <strong>${fmt(s.unsynced_included)}</strong></span><span>同步缺摘要 <strong>${fmt(s.unsynced_missing_abstract)}</strong></span><span>占比 <strong>${percent(ratio(s))}</strong></span></span><span class="tag ${s.issues.length?'':'ok'}">${s.issues.length ? `${s.issues.length} 项待关注` : '暂无自动提示'}</span></summary><div class="detail"><div><h3>采集与总量核验</h3><p>采集状态：${esc(s.state)}<br>全量采集 ${fmt(s.papers)} 篇，缺摘要 ${fmt(s.papers_missing_abstract)} 篇<br>官网 ${fmt(s.official_total)} 篇${s.official_scope ? `（${esc(s.official_scope)}）` : ''}${check}<br>${esc(s.coverage_note || '未提供同口径核验说明')}</p></div><div><h3>元信息与精筛</h3><p>精筛纳入 ${fmt(s.final_included)} 篇，缺摘要 ${fmt(s.final_missing_abstract)} 篇<br>AI4S候选待补摘要 ${fmt(requiredAbstracts(s))} 篇${s.abstract_recovered ? `<br>官网证据已补齐摘要 ${fmt(s.abstract_recovered)} 篇（原始缺摘要 ${fmt(s.missing_abstract)} 篇）` : ''}${s.abstract_not_required ? `<br>官方无独立摘要、无需补摘要 ${fmt(s.abstract_not_required)} 篇（原始缺摘要 ${fmt(s.missing_abstract)} 篇）` : ''}${s.abstract_full_text_reviewed ? `<br>官方无独立摘要、已完成全文审核 ${fmt(s.abstract_full_text_reviewed)} 篇（原始空值保留）` : ''}${s.abstract_closed_by_owner ? `<br>原摘要访问受限、按负责人要求排除并停止补证 ${fmt(s.abstract_closed_by_owner)} 篇（空值保留）` : ''}${s.unsynced_included != null ? `<br>已纳入待同步 ${fmt(s.unsynced_included)} 篇，其中缺摘要 ${fmt(s.unsynced_missing_abstract)} 篇` : ''}<br>当前候选文件 ${fmt(s.candidates)} 篇（快照候选 ${fmt(s.snapshot_candidates)} 篇）<br>${esc(decisions)}${s.catalogue_reference_records ? `<br>目录备查 ${fmt(s.catalogue_reference_records)} 条（尚未核实为当前候选，不计作已完成精筛）` : ''}${s.active_review_file ? `<br>按当前负责人确认的候选批次与已核实补录统计；历史交付另列。` : ''}</p></div><div><h3>当前问题</h3><ul>${s.issues.length?s.issues.map(x=>`<li>${esc(x)}</li>`).join(''):'<li>暂无自动提示，请核对原始材料。</li>'}</ul></div><div><h3>下一步行动</h3><ul>${s.actions.length?s.actions.map(x=>`<li>${esc(x)}</li>`).join(''):'<li>查看原始材料并按需反馈。</li>'}</ul></div><div class="wide links">${ref}${evidence}${history}</div></div></details>`;
  }).join('');
}
function shortTime(iso) {
  if (!iso) return '';
  const d = new Date(iso); if (Number.isNaN(d.getTime())) return '';
  const p = n => String(n).padStart(2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function lastUpdateText(y) {
  const rows = (data.owners || []).filter(o => o.last_update && o.last_update.at);
  if (owner.value) {
    const row = rows.find(o => o.owner === owner.value);
    if (!row) return '上次更新：该负责人暂无审核提交。';
    const v = row.years?.[String(y.year)];
    const done = v ? ` · ${y.year} 交付 ${v.delivered}/${v.sources}` : '';
    return `上次更新 ${shortTime(row.last_update.at)}（${row.last_update.author || '未知'}）${done}。`;
  }
  if (!rows.length) return '';
  const latest = rows.slice().sort((a, b) => b.last_update.at.localeCompare(a.last_update.at))[0];
  return `最近提交 ${shortTime(latest.last_update.at)}（${latest.owner}）。`;
}
$('#download').addEventListener('click',()=>{const y=year.value; const text=`# ${y} 论文审核行动清单\n\n数据快照：${data.years.find(x=>String(x.year)===y)?.captured_at || '未知'}\n来源提交：${data.commit || '未知'}\n负责人筛选：${owner.value || '全部'}\n\n`+selected.map(s=>`## ${s.title}（${s.code}）\n负责人：${s.owner || '未知'}\n问题：${s.issues.join('；') || '暂无自动提示'}\n行动：${s.actions.join('；') || '查看原始材料'}\n证据：${s.files.map(f=>data.repository+f).join(' ; ')}\n`).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));a.download=`ai4s-actions-${y}.md`;a.click();URL.revokeObjectURL(a.href)});
for(const el of [year,owner,search,status,sort].filter(Boolean)) el.addEventListener(el===search?'input':'change',render);
async function refreshSnapshot() {
  try {
    const result = await loadMonitorSnapshot(fetch);
    if (data?.generated_at && result.data.generated_at && Date.parse(result.data.generated_at) < Date.parse(data.generated_at)) {
      $('#error').textContent = '暂时无法读取最新仓库数据，正在显示上次成功读取的结果。';
      return;
    }
    const changed = !data || data.generated_at !== result.data.generated_at || data.commit !== result.data.commit;
    data = result.data;
    $('#error').textContent = '';
    $('#provenance').textContent = `汇总生成：${data.generated_at || '未知'}\n仓库提交：${data.commit?.slice(0,12) || '未知'}\n数据来源：${result.live ? '仓库实时汇总' : result.staleLive ? '网站发布快照（仓库缓存较旧）' : '网站发布快照'}`;
    $('#provenance').style.whiteSpace = 'pre-line';
    if (!changed) return;
    const previousYear = year.value;
    options(year,data.years.map(y=>String(y.year)),'选择年份');
    year.value = data.years.some(y=>String(y.year)===previousYear) ? previousYear : String(data.years.find(y=>y.year===2024)?.year ?? data.years.at(-1).year);
    const content = $('#content'); if (content) content.hidden = false;
    render();
  } catch(e) {
    if (!data) $('#provenance').textContent = '数据加载失败';
    $('#error').textContent = `无法读取监控快照：${e.message}。请稍后重试。`;
  }
}
await refreshSnapshot();
setInterval(refreshSnapshot, 120000);
