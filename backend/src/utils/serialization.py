import hashlib, json
from src.services.access import job_teams_of
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j, full=True):
    data={k:getattr(j,k) for k in ['id','name','dataset_id','params','status','error','approved','created_by','created_at','finished_at']}
    data['teams']=job_teams_of(j)
    if full: data['result']=j.result
    return data
def report_dict(r, recipient=None):
    data={k:getattr(r,k) for k in ['id','name','job_id','destination','recipient_id','interval_seconds','next_run','enabled']}
    data['recipient_name']=recipient
    return data
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination','recipient_id','teams']}
def grant_dict(g):
    return {k:getattr(g,k) for k in ['id','user_id','team','granted_by','created_at']}
