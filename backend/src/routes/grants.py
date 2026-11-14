from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import User, Grant, Job, Audit
from src.schemas.grant import GrantInput
from src.middlewares.auth import admin_only
from src.services import access
from src.services.access import teams_for
from src.services.audit import record
from src.utils.serialization import grant_dict, job_dict
router=APIRouter(prefix='/grants')
@router.get('')
def listing(db=Depends(get_db),u=Depends(admin_only)):
    users={x.id:x for x in db.scalars(select(User))}
    out=[]
    for g in db.scalars(select(Grant).order_by(Grant.id.desc())):
        row=grant_dict(g); owner=users.get(g.user_id)
        row['user']={'id':owner.id,'name':owner.name,'email':owner.email,'role':owner.role} if owner else None
        out.append(row)
    return out
@router.get('/users')
def users(db=Depends(get_db),u=Depends(admin_only)):
    return [{'id':x.id,'name':x.name,'email':x.email,'role':x.role,'teams':teams_for(db,x)} for x in db.scalars(select(User).order_by(User.id))]
@router.get('/changes')
def changes(db=Depends(get_db),u=Depends(admin_only)):
    return [{'id':a.id,'actor':a.actor,'action':a.action,'detail':a.detail,'at':a.at} for a in db.scalars(select(Audit).where(Audit.action.like('grant.%')).order_by(Audit.id.desc()).limit(100))]
@router.get('/blocked')
def blocked(db=Depends(get_db),u=Depends(admin_only)):
    paused=[job_dict(j,full=False) for j in db.scalars(select(Job).where(Job.status=='paused').order_by(Job.id.desc()))]
    deliveries=[{'id':a.id,'actor':a.actor,'detail':a.detail,'at':a.at} for a in db.scalars(select(Audit).where(Audit.action=='report.blocked').order_by(Audit.id.desc()).limit(50))]
    return {'paused_jobs':paused,'blocked_deliveries':deliveries}
@router.post('',status_code=201)
def create(data:GrantInput,db=Depends(get_db),u=Depends(admin_only)):
    user=db.get(User,data.user_id)
    if not user: raise HTTPException(404,'账号不存在')
    g,created=access.grant_team(db,u.email,user,data.team)
    if created: record(db,u.email,'grant.grant',{'user':user.email,'team':data.team})
    db.commit(); return grant_dict(g)
@router.post('/revoke')
def revoke(data:GrantInput,db=Depends(get_db),u=Depends(admin_only)):
    user=db.get(User,data.user_id)
    if not user: raise HTTPException(404,'账号不存在')
    if not access.revoke_team(db,user,data.team): raise HTTPException(404,'该授权不存在或已撤销')
    record(db,u.email,'grant.revoke',{'user':user.email,'team':data.team})
    paused=access.pause_overreaching_jobs(db,user,u.email)
    db.commit()
    return {'revoked':True,'paused_jobs':[j.id for j in paused]}
