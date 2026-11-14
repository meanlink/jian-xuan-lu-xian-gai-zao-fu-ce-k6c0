"""按小组的账号授权与访问边界。负责人(admin)隐含全量；其余账号实时查询 grants 表，撤权即刻生效。"""
import time
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Grant, Job
from src.services.business import metadata
from src.services.audit import record


def all_teams():
    for p in metadata().get('parameters', []):
        if p['key'] == 'team':
            return [o['value'] for o in p.get('options', []) if o['value'] != '全部']
    return []


def is_admin(user):
    return user is not None and user.role == 'admin'


def teams_for(db, user):
    if user is None:
        return []
    if is_admin(user):
        return all_teams()
    return [g.team for g in db.scalars(select(Grant).where(Grant.user_id == user.id))]


def filter_records(records, teams):
    allowed = set(teams)
    return [r for r in records if str(r.get('team')) in allowed]


def scoped_records(db, user, records):
    if is_admin(user):
        return list(records)
    return filter_records(records, teams_for(db, user))


def job_teams_of(job):
    teams = list(job.teams or [])
    if teams:
        return teams
    team = str((job.params or {}).get('team', '全部'))
    return all_teams() if team == '全部' else [team]


def covers(db, user, teams):
    if is_admin(user):
        return True
    return set(teams) <= set(teams_for(db, user))


def require_teams(db, user, teams):
    if not covers(db, user, teams):
        raise HTTPException(403, '涉及未获授权的小组，已按授权边界拒绝访问')


def grant_team(db, actor, user, team):
    if team not in all_teams():
        raise HTTPException(422, '未知小组，无法授权')
    existing = db.scalar(select(Grant).where(Grant.user_id == user.id, Grant.team == team))
    if existing:
        return existing, False
    g = Grant(user_id=user.id, team=team, granted_by=actor, created_at=time.time())
    db.add(g)
    db.flush()
    return g, True


def revoke_team(db, user, team):
    g = db.scalar(select(Grant).where(Grant.user_id == user.id, Grant.team == team))
    if not g:
        return False
    db.delete(g)
    db.flush()
    return True


def pause_overreaching_jobs(db, user, actor):
    """撤权生效为界：该账号排队中且不再被授权覆盖的任务暂停并说明原因。"""
    allowed = set(teams_for(db, user))
    paused = []
    for j in db.scalars(select(Job).where(Job.created_by == user.id, Job.status == 'queued')):
        missing = sorted(set(job_teams_of(j)) - allowed)
        if missing:
            j.status = 'paused'
            j.error = '授权变更：小组 ' + '、'.join(missing) + ' 已超出创建者授权范围，任务暂停，待负责人复核'
            paused.append(j)
            record(db, actor, 'job.paused', {'id': j.id, 'reason': j.error})
    return paused
