import time
from fastapi import HTTPException
from redis import Redis
from src.config.settings import REDIS_URL
from src.models import Dataset, Job, User
from src.services.business import metadata
from src.services.access import all_teams, is_admin, teams_for, job_teams_of
def create(db, data, user):
    if not db.get(Dataset,data.dataset_id): raise HTTPException(404,'数据批次不存在')
    allowed={p['key']:p for p in metadata().get('parameters',[])}
    if set(data.params)-set(allowed): raise HTTPException(422,'包含未知分析参数')
    params={k:p['default'] for k,p in allowed.items()}
    params.update(data.params)
    for key,p in allowed.items():
        v=params[key]
        if p['type']=='number':
            try:
                v=float(v)
                if not (p.get('min',-1e9)<=v<=p.get('max',1e9)): raise ValueError()
                params[key]=v
            except (ValueError,TypeError): raise HTTPException(422, f'{p["label"]} 超出范围或非数值')
        elif str(v) not in [str(o['value']) for o in p.get('options',[])]:
            raise HTTPException(422,f'{p["label"]} 不是有效选项')
    scope=all_teams() if is_admin(user) else teams_for(db,user)
    team=str(params.get('team','全部'))
    if not is_admin(user):
        if not scope: raise HTTPException(403,'当前账号未获任何小组授权，请联系负责人授权后再提交')
        if team!='全部' and team not in scope: raise HTTPException(403,f'小组 {team} 未获授权，无法按该口径计算')
    j=Job(name=data.name, dataset_id=data.dataset_id, params=params, teams=(scope if team=='全部' else [team]), created_by=user.id, created_at=time.time(), status='queued')
    db.add(j); db.flush()
    return j
def resume(db, job, user):
    if job.status!='paused': raise HTTPException(409,'仅暂停中的任务可以恢复')
    creator=db.get(User, job.created_by)
    scope=all_teams() if is_admin(creator) else teams_for(db,creator)
    needed=job_teams_of(job)
    missing=sorted(set(needed)-set(scope))
    if missing: raise HTTPException(409,'创建者当前授权仍不覆盖该任务口径（缺：'+'、'.join(missing)+'），请先由负责人重新授权')
    job.status='queued'; job.error=''
    db.flush()
    return job
def enqueue(job_id):
    try:
        r=Redis.from_url(REDIS_URL); r.rpush('analysis:queue',job_id); r.close()
    except Exception:
        pass # SQL queued status is the durable fallback
