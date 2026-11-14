import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'}),resume:id=>api('/jobs/'+id+'/resume',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const grants={list:()=>api('/grants'),users:()=>api('/grants/users'),changes:()=>api('/grants/changes'),blocked:()=>api('/grants/blocked'),create:data=>api('/grants',{method:'POST',body:JSON.stringify(data)}),revoke:data=>api('/grants/revoke',{method:'POST',body:JSON.stringify(data)})};
