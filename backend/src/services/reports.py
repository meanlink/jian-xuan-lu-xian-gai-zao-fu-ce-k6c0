import time, os, csv, io, hashlib, json
from fastapi import HTTPException
from src.models import Job, Report, Delivery, Dataset, User
from src.config.settings import ARTIFACT_DIR
from src.services.access import is_admin, teams_for, job_teams_of
from src.services.business import analyze
from src.services.audit import record
def create(db, data):
    j=db.get(Job,data.job_id)
    if not j or j.status!='completed' or not j.approved:
        raise HTTPException(409,'请先选择已完成且获批准的分析结果')
    recipient=db.get(User,data.recipient_id)
    if not recipient: raise HTTPException(404,'收件账号不存在')
    r=Report(name=data.name, job_id=j.id, destination=data.destination, recipient_id=recipient.id, interval_seconds=data.interval_seconds, next_run=time.time()+data.delay_seconds, enabled=True)
    db.add(r); db.flush()
    return r
def deliver(db, report):
    """按收件账号当前授权隔离生成快照；撤权生效后不再发布越权文件。"""
    j=db.get(Job,report.job_id)
    if not j or not j.approved: return None
    recipient=db.get(User,report.recipient_id) if report.recipient_id else None
    if recipient and not is_admin(recipient):
        scope=sorted(set(job_teams_of(j))&set(teams_for(db,recipient)))
        if not scope:
            report.next_run=time.time()+report.interval_seconds
            record(db,'worker','report.blocked',{'id':report.id,'recipient':recipient.email,'reason':'收件账号已无覆盖该简报的获授权小组，本次发布被拦截'})
            return None
    else:
        scope=job_teams_of(j)
    d=db.get(Dataset,j.dataset_id)
    rows=[r for r in d.records if str(r.get('team')) in set(scope)]
    try:
        result=analyze(rows,j.params)
        json.dumps(result,allow_nan=False)
    except Exception as e:
        report.next_run=time.time()+report.interval_seconds
        record(db,'worker','report.blocked',{'id':report.id,'reason':'授权范围内样本不足，本次发布被拦截：'+str(e)[:200]})
        return None
    out=io.StringIO()
    out.write('\ufeff')
    table=result.get('table',{})
    cols=table.get('columns',[])
    writer=csv.writer(out)
    def safe(v):
        if isinstance(v,(int,float)) and not isinstance(v,bool): return v
        text=str(v)
        return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
    writer.writerow([safe(c['label']) for c in cols])
    for row in table.get('rows',[]): writer.writerow([safe(row.get(c['key'],'')) for c in cols])
    data=out.getvalue().encode('utf-8')
    teams=sorted({str(r.get('team')) for r in rows})
    delivery=Delivery(report_id=report.id, created_at=time.time(), checksum=hashlib.sha256(data).hexdigest(), filename='', destination=report.destination, recipient_id=recipient.id if recipient else None, teams=teams)
    db.add(delivery); db.flush()
    delivery.filename=f'report-{report.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR,exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename),'wb') as f:f.write(data)
    with open(os.path.join(ARTIFACT_DIR,delivery.filename+'.json'),'w') as f: json.dump({'job':j.name,'params':j.params,'teams':teams,'result':result,'checksum':delivery.checksum},f,ensure_ascii=False,allow_nan=False)
    report.next_run=time.time()+report.interval_seconds
    return delivery
