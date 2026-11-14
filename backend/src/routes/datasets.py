from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Dataset
from src.schemas.dataset import DatasetInput
from src.middlewares.auth import current_user, can_write
from src.services import datasets
from src.services.access import is_admin, teams_for, filter_records
from src.services.audit import record
from src.utils.serialization import dataset_dict
router=APIRouter(prefix='/datasets')
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    admin=is_admin(u); teams=set(teams_for(db,u)); out=[]
    for d in db.scalars(select(Dataset).order_by(Dataset.id.desc())):
        row=dataset_dict(d)
        row['visible_rows']=row['rows'] if admin else len(filter_records(d.records,teams))
        out.append(row)
    return out
@router.post('',status_code=201)
def create(data:DatasetInput,db=Depends(get_db),u=Depends(can_write)):
    d=datasets.create(db,data); record(db,u.email,'dataset.create',{'id':d.id,'rows':len(d.records)})
    db.commit(); return dataset_dict(d)
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    d=db.get(Dataset,id)
    if not d:raise HTTPException(404,'数据批次不存在')
    records=d.records if is_admin(u) else filter_records(d.records,teams_for(db,u))
    return {**dataset_dict(d),'visible_rows':len(records),'records':records}
