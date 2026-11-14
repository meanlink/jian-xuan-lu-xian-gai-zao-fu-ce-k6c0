import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from src.config.database import get_db
from src.config.settings import ARTIFACT_DIR
from src.models import Report, Delivery, User
from src.schemas.report import ReportInput
from src.middlewares.auth import current_user, admin_only
from src.services import reports
from src.services.access import is_admin, teams_for
from src.services.audit import record
from src.utils.serialization import report_dict, delivery_dict
router=APIRouter()
def _names(db):
    return {u.id:u.name for u in db.scalars(select(User))}
@router.get('/reports')
def listing(db=Depends(get_db),u=Depends(current_user)):
    names=_names(db); admin=is_admin(u); out=[]
    for r in db.scalars(select(Report).order_by(Report.id.desc())):
        if admin or r.recipient_id==u.id:
            out.append(report_dict(r,names.get(r.recipient_id)))
    return out
@router.post('/reports',status_code=201)
def create(data:ReportInput,db=Depends(get_db),u=Depends(admin_only)):
    r=reports.create(db,data); record(db,u.email,'report.schedule',{'id':r.id,'destination':r.destination,'recipient_id':r.recipient_id}); db.commit()
    return report_dict(r,_names(db).get(r.recipient_id))
@router.post('/reports/{id}/toggle')
def toggle(id:int,db=Depends(get_db),u=Depends(admin_only)):
    r=db.get(Report,id)
    if not r:raise HTTPException(404,'分发计划不存在')
    r.enabled=not r.enabled;record(db,u.email,'report.toggle',{'id':id,'enabled':r.enabled});db.commit()
    return report_dict(r,_names(db).get(r.recipient_id))
@router.get('/deliveries')
def deliveries(db=Depends(get_db),u=Depends(current_user)):
    admin=is_admin(u)
    return [delivery_dict(d) for d in db.scalars(select(Delivery).order_by(Delivery.id.desc()).limit(100)) if admin or d.recipient_id==u.id]
@router.get('/deliveries/{id}/download')
def download(id:int,format:str='csv',db=Depends(get_db),u=Depends(current_user)):
    d=db.get(Delivery,id)
    if not d:raise HTTPException(404,'归档不存在')
    if format not in ('csv','json'):raise HTTPException(422,'支持 CSV 或 JSON')
    if not is_admin(u):
        if d.recipient_id!=u.id: raise HTTPException(403,'该归档不属于当前账号的收件箱')
        if not set(d.teams or [])<=set(teams_for(db,u)): raise HTTPException(403,'授权已变更，该历史归档涉及的小组已超出当前授权范围')
    filename=d.filename+('.json' if format=='json' else '')
    p=os.path.join(ARTIFACT_DIR,filename)
    if not os.path.exists(p):raise HTTPException(404,'归档文件不存在，请重新安排分发')
    return FileResponse(p,filename=filename,media_type='application/json' if format=='json' else 'text/csv; charset=utf-8')
