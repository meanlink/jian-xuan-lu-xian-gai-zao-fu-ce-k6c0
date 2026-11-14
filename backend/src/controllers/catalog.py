from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from src.config.database import get_db
from src.middlewares.auth import current_user
from src.models import Dataset, Job, Report, Audit
from src.services.business import metadata
from src.services.access import is_admin, teams_for, filter_records, job_teams_of
router=APIRouter()
@router.get('/meta')
def meta():return metadata()
@router.get('/overview')
def overview(db=Depends(get_db),user=Depends(current_user)):
    admin=is_admin(user); teams=set(teams_for(db,user))
    datasets=list(db.scalars(select(Dataset)))
    jobs=[j for j in db.scalars(select(Job)) if admin or set(job_teams_of(j))<=teams]
    reports=[r for r in db.scalars(select(Report)) if admin or r.recipient_id==user.id]
    return {'datasets':len(datasets), 'records':sum(len(d.records) if admin else len(filter_records(d.records,teams)) for d in datasets), 'jobs':len(jobs), 'approved':sum(1 for j in jobs if j.approved), 'reports':len(reports)}
@router.get('/audits')
def audits(db=Depends(get_db),user=Depends(current_user)):
    return [{'id':a.id,'actor':a.actor,'action':a.action,'detail':a.detail,'at':a.at} for a in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(50))]
