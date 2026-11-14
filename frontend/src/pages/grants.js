import {grants,jobs} from '../api/entities.js';
import {workspace} from '../stores/workspace.js';
import {heading} from '../components/common/shell.js';
import {esc,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
function teamOptions(){
 const p=(workspace.meta.parameters||[]).find(p=>p.key==='team');
 return p?p.options.filter(o=>o.value!=='全部').map(o=>o.value):[];
}
export async function grantsPage(){
 const [list,users,changes,blocked]=await Promise.all([grants.list(),grants.users(),grants.changes(),grants.blocked()]);
 const teams=teamOptions();
 const account=u=>'<strong>'+esc(u?.name||'未知账号')+'</strong><span>'+esc(u?.email||'')+'</span>';
 return heading('06 / ACCESS','小组授权与访问边界','负责人按小组给账号授权。样本、分析与简报按授权实时隔离；撤权即刻生效，越权的排队任务与发布会被拦截。')+'<div class="grants-grid"><section class="panel"><div class="section-title"><h2>授予小组权限</h2></div><form id="grant-form"><label>账号<select name="user_id">'+users.filter(u=>u.role!=='admin').map(u=>'<option value="'+u.id+'">'+esc(u.name+' · '+u.email)+'</option>').join('')+'</select></label><label>试点小组<select name="team">'+teams.map(t=>'<option value="'+esc(t)+'">'+esc(t)+'</option>').join('')+'</select></label><button type="submit" class="primary">授权 ↗</button><p class="hint">负责人隐含全量权限，无需授权。重复授权同一小组会被忽略。</p></form><div class="section-title"><h2>当前授权</h2><span>'+list.length+' 条</span></div><div class="grant-list">'+list.map(g=>'<article><div>'+account(g.user)+'</div><div><strong>'+esc(g.team)+'</strong><small>'+esc(g.granted_by)+' · '+date(g.created_at)+'</small></div><button class="button small" data-revoke="'+g.user_id+'" data-team="'+esc(g.team)+'">撤权</button></article>').join('')+(!list.length?'<p class="empty">尚无授权记录。</p>':'')+'</div></section><section class="panel"><div class="section-title"><h2>受阻任务</h2><span>撤权生效拦截</span></div>'+(blocked.paused_jobs.length?blocked.paused_jobs.map(j=>'<article class="blocked-job"><div><strong>'+esc(j.name)+'</strong><p>'+esc(j.error||'授权变更暂停')+'</p><small>'+date(j.created_at)+'</small></div><button class="button small" data-resume="'+j.id+'">恢复排队</button></article>').join(''):'<p class="empty">暂无被暂停的计算任务。</p>')+(blocked.blocked_deliveries.length?'<div class="section-title"><h2>被拦截的发布</h2></div>'+blocked.blocked_deliveries.map(a=>'<article class="blocked-job"><div><strong>分发计划 #'+esc(a.detail.id)+'</strong><p>'+esc(a.detail.reason||'')+'</p><small>'+date(a.at)+'</small></div></article>').join(''):'')+'<div class="section-title"><h2>授权变更记录</h2><span>可追溯</span></div><ul class="timeline">'+changes.map(a=>'<li><strong>'+esc(a.action==='grant.grant'?'授权':'撤权')+' · '+esc(a.detail.team||'')+'</strong><span>'+esc(a.actor)+' → '+esc(a.detail.user||'')+' · '+date(a.at)+'</span></li>').join('')+(!changes.length?'<li><strong>暂无变更</strong><span>授权与撤权会记录在此</span></li>':'')+'</ul><p class="hint">负责人不受小组边界限制，可在各页面全量复核样本、分析与简报。</p></section></div>';
}
export function bindGrants(refresh){
 submit(document.querySelector('#grant-form'),async f=>{await grants.create({user_id:Number(f.get('user_id')),team:f.get('team')});notify('已授权');await refresh();});
 document.querySelectorAll('[data-revoke]').forEach(b=>b.onclick=async()=>{try{const r=await grants.revoke({user_id:Number(b.dataset.revoke),team:b.dataset.team});notify('已撤权'+(r.paused_jobs.length?'，'+r.paused_jobs.length+' 个排队任务已暂停':''));await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-resume]').forEach(b=>b.onclick=async()=>{try{await jobs.resume(b.dataset.resume);notify('任务已恢复排队');await refresh();}catch(e){notify(e.message,true);}});
}
