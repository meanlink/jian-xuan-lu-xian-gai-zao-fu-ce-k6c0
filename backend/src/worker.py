import time, json, logging
from pathlib import Path
from sqlalchemy import select
from redis import Redis
from src.config.database import Session
from src.config.settings import REDIS_URL
from src.models import Job, Dataset, Report, User
from src.services.business import analyze
from src.services.reports import deliver
from src.services.access import covers, job_teams_of, scoped_records
from src.services.audit import record
logging.basicConfig(level=logging.INFO)
def execute(job_id):
    with Session() as db:
        j=db.get(Job,job_id)
        if not j or j.status!='queued':return
        creator=db.get(User,j.created_by)
        # 撤权生效为界：执行前校验，越权的排队任务暂停并说明原因
        if not covers(db,creator,job_teams_of(j)):
            j.status='paused';j.error='授权已变更：创建者不再覆盖任务涉及小组，执行被拦截，待负责人复核'
            record(db,'worker','job.paused',{'id':j.id,'reason':j.error});db.commit();return
        j.status='running'; db.commit()
        try:
            d=db.get(Dataset,j.dataset_id)
            scoped=scoped_records(db,creator,d.records)
            result=analyze(scoped,j.params)
            json.dumps(result,allow_nan=False)
            actual=sorted({str(r.get('team')) for r in scoped})
            # 写结果前再校验：计算期间撤权的，不产出新的越权结果
            if not covers(db,creator,actual):
                j.status='paused';j.error='计算期间授权变更，结果已按撤权生效拦截，待负责人复核'
                record(db,'worker','job.paused',{'id':j.id,'reason':j.error})
            else:
                j.result=result;j.teams=actual;j.status='completed';j.finished_at=time.time()
                record(db,'worker','job.completed',{'id':j.id})
        except Exception as e:
            logging.exception('Analysis failed')
            j.status='failed';j.error=str(e)[:990];j.finished_at=time.time()
            record(db,'worker','job.failed',{'id':j.id,'error':j.error})
        db.commit()
def tick():
    with Session() as db:
        queued=list(db.scalars(select(Job.id).where(Job.status=='queued').limit(3)))
    for job_id in queued:execute(job_id)
    with Session() as db:
        for r in db.scalars(select(Report).where(Report.enabled==True,Report.next_run<=time.time())):
            d=deliver(db,r)
            if d:record(db,'worker','report.delivered',{'id':r.id,'delivery':d.id})
        db.commit()
def main():
    r=Redis.from_url(REDIS_URL,socket_timeout=3)
    # This Compose stack has a single worker. A crash must not strand its jobs.
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.status=='running')):
            j.status='queued';record(db,'worker','job.recovered',{'id':j.id})
        db.commit()
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=r.blpop('analysis:queue',timeout=1)
            if item:execute(int(item[1]))
            tick()
        except Exception:
            logging.exception('Worker retry');time.sleep(2)
if __name__=='__main__':main()
