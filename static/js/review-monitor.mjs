import {loadMonitorSnapshot} from './review-monitor-live.mjs';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (n) => n == null ? '未知' : Number(n).toLocaleString('zh-CN');
const safeUrl = (u) => { try { const x = new URL(u); return ['https:','http:'].includes(x.protocol) ? x.href : ''; } catch { return ''; } };
let data, selected = [];
const year = $('#year'), owner = $('#owner'), search = $('#search'), status = $('#status');
function options(select, values, label) { select.innerHTML = `<option value="">${label}</option>` + values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join(''); }
function render() {
  const y = data.years.find(x => String(x.year) === year.value); if (!y) return;
  const old = owner.value; const owners = [...new Set(y.sources.map(s => s.owner).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN')); options(owner, owners, '全部负责人'); owner.value = owners.includes(old) ? old : '';
  const query = search.value.trim().toLowerCase();
  selected = y.sources.filter(s => (!owner.value || s.owner === owner.value) && (!query || `${s.title} ${s.code}`.toLowerCase().includes(query)) && (status.value === 'all' || (status.value === 'issues' && s.issues.length) || (status.value === 'missing' && s.official_total == null) || (status.value === 'pending' && s.decisions && (s.decisions.pending || s.decisions.unreviewed))));
  const ownerActions = $('#owner-actions'); ownerActions.hidden = !owner.value; if (owner.value) ownerActions.href = `https://github.com/BUPT-AI4S/ai4s-crawler/blob/main/reviews/${y.year}/actions/${encodeURIComponent(owner.value)}.md`;
  $('#view-title').textContent = owner.value ? `${owner.value} · 工作分屏` : '工作总览';
  $('#scope').textContent = `统计当前筛选的 ${selected.length} 个来源；采集快照 ${y.captured_at || '未提供'}。`;
  const sum = key => selected.reduce((n,s)=>n+(s[key] ?? 0),0);
  const metrics = [['来源条目',selected.length],['快照采集论文',selected.some(s=>s.papers!=null)?sum('papers'):null],['初筛候选',sum('candidates')],['候选缺摘要',selected.some(s=>s.missing_abstract!=null)?sum('missing_abstract'):null],['官网总数未知',selected.filter(s=>s.official_total==null).length]];
  $('#metrics').innerHTML=metrics.map(([name,value])=>`<div class="metric"><strong>${fmt(value)}</strong><span>${name}</span></div>`).join('');
  $('#count').textContent=`${selected.length} 个来源`; $('#empty').hidden=selected.length>0;
  $('#list').innerHTML=selected.map(s=>{
    const decisions=s.decisions ? `纳入 ${s.decisions.include} · 排除 ${s.decisions.exclude} · 待定 ${s.decisions.pending} · 未审 ${s.decisions.unreviewed}` : '暂无逐篇交付';
    const ref=s.files.map((file,i)=>`<a href="${esc(data.repository + file.split('/').map(encodeURIComponent).join('/'))}" target="_blank" rel="noopener">交付文件 ${i+1}</a>`).join('');
    const evidence=s.evidence_urls.map(safeUrl).filter(Boolean).map((url,i)=>`<a href="${esc(url)}" target="_blank" rel="noopener">核验依据 ${i+1}</a>`).join('');
    return `<details><summary><span class="source-name"><strong>${esc(s.title)}</strong><small>${esc(s.code)} · ${esc(s.venue_decision || '刊会结论未填写')}</small></span><span class="summary-owner">${esc(s.owner || '负责人未知')}</span><span class="tag ${s.issues.length?'':'ok'}">${s.issues.length ? `${s.issues.length} 项待关注` : '暂无自动提示'}</span></summary><div class="detail"><div><h3>采集与总量核验</h3><p>采集状态：${esc(s.state)}<br>采集 ${fmt(s.papers)} 篇 · 官网 ${fmt(s.official_total)} 篇${s.official_scope ? `（${esc(s.official_scope)}）` : ''}<br>${esc(s.coverage_note || '未提供同口径核验说明')}</p></div><div><h3>元信息与精筛</h3><p>AI4S候选缺摘要 ${fmt(s.missing_abstract)} 篇<br>当前候选文件 ${fmt(s.candidates)} 篇（快照候选 ${fmt(s.snapshot_candidates)} 篇）<br>${esc(decisions)}</p></div><div><h3>当前问题</h3><ul>${s.issues.length?s.issues.map(x=>`<li>${esc(x)}</li>`).join(''):'<li>暂无自动提示，请核对原始材料。</li>'}</ul></div><div><h3>下一步行动</h3><ul>${s.actions.length?s.actions.map(x=>`<li>${esc(x)}</li>`).join(''):'<li>查看原始材料并按需反馈。</li>'}</ul></div><div class="wide links">${ref}${evidence}</div></div></details>`;
  }).join('');
}
$('#download').addEventListener('click',()=>{const y=year.value; const text=`# ${y} 论文审核行动清单\n\n数据快照：${data.years.find(x=>String(x.year)===y)?.captured_at || '未知'}\n来源提交：${data.commit || '未知'}\n负责人筛选：${owner.value || '全部'}\n\n`+selected.map(s=>`## ${s.title}（${s.code}）\n负责人：${s.owner || '未知'}\n问题：${s.issues.join('；') || '暂无自动提示'}\n行动：${s.actions.join('；') || '查看原始材料'}\n证据：${s.files.map(f=>data.repository+f).join(' ; ')}\n`).join('\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));a.download=`ai4s-actions-${y}.md`;a.click();URL.revokeObjectURL(a.href)});
for(const el of [year,owner,search,status]) el.addEventListener(el===search?'input':'change',render);
async function refreshSnapshot() {
  try {
    const result = await loadMonitorSnapshot(fetch);
    if (!result.live && data?.generated_at && result.data.generated_at && result.data.generated_at < data.generated_at) {
      $('#error').textContent = '暂时无法读取最新仓库数据，正在显示上次成功读取的结果。';
      return;
    }
    const changed = !data || data.generated_at !== result.data.generated_at || data.commit !== result.data.commit;
    data = result.data;
    $('#error').textContent = result.live ? '' : '暂时无法读取仓库实时汇总，正在显示网站发布快照。';
    $('#provenance').textContent = `汇总生成：${data.generated_at || '未知'}\n仓库提交：${data.commit?.slice(0,12) || '未知'}\n数据来源：${result.live ? '仓库实时汇总' : '网站发布快照'}`;
    $('#provenance').style.whiteSpace = 'pre-line';
    if (!changed) return;
    const previousYear = year.value;
    options(year,data.years.map(y=>String(y.year)),'选择年份');
    year.value = data.years.some(y=>String(y.year)===previousYear) ? previousYear : String(data.years.find(y=>y.year===2024)?.year ?? data.years.at(-1).year);
    $('#content').hidden = false;
    render();
  } catch(e) {
    if (!data) $('#provenance').textContent = '数据加载失败';
    $('#error').textContent = `无法读取监控快照：${e.message}。请稍后重试。`;
  }
}
await refreshSnapshot();
setInterval(refreshSnapshot, 120000);
