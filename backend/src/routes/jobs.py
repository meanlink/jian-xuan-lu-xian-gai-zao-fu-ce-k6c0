from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Job
from src.schemas.job import JobInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import jobs
from src.services.access import is_admin, covers, job_teams_of
from src.services.audit import record
from src.utils.serialization import job_dict
router=APIRouter(prefix='/jobs')
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    admin=is_admin(u); out=[]
    for j in db.scalars(select(Job).order_by(Job.id.desc()).limit(100)):
        if admin or covers(db,u,job_teams_of(j)) or (j.created_by==u.id and j.status=='paused'):
            out.append(job_dict(j,full=False))
    return out
@router.post('',status_code=201)
def create(data:JobInput,db=Depends(get_db),u=Depends(can_write)):
    j=jobs.create(db,data,u); record(db,u.email,'job.create',{'id':j.id,'params':j.params})
    db.commit(); jobs.enqueue(j.id); return job_dict(j,full=False)
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    if is_admin(u) or covers(db,u,job_teams_of(j)): return job_dict(j)
    if j.created_by==u.id and j.status=='paused': return job_dict(j,full=False)
    raise HTTPException(403,'该分析涉及未获授权小组，已拒绝访问')
@router.post('/{id}/approve')
def approve(id:int,db=Depends(get_db),u=Depends(admin_only)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    if j.status!='completed':raise HTTPException(409,'仅已完成结果可以批准')
    j.approved=True; record(db,u.email,'job.approve',{'id':id}); db.commit()
    return job_dict(j)
@router.post('/{id}/resume')
def resume(id:int,db=Depends(get_db),u=Depends(current_user)):
    j=db.get(Job,id)
    if not j: raise HTTPException(404,'分析任务不存在')
    if u.role!='admin' and j.created_by!=u.id: raise HTTPException(403,'仅负责人或任务创建者可以恢复')
    jobs.resume(db,j,u); record(db,u.email,'job.resumed',{'id':id})
    db.commit(); jobs.enqueue(j.id); return job_dict(j,full=False)
