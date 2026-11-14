/** @typedef {{id:number,name:string,source:string,rows:number,visible_rows:number,checksum:string}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,teams:string[],result:Object,approved:boolean,error:string}} AnalysisJob */
/** @typedef {{id:number,name:string,job_id:number,destination:string,recipient_id:number,recipient_name:string,next_run:number,enabled:boolean}} ReportSchedule */
/** @typedef {{id:number,report_id:number,filename:string,checksum:string,recipient_id:number,teams:string[]}} DeliveryArchive */
/** @typedef {{id:number,user_id:number,team:string,granted_by:string,created_at:number}} TeamGrant */
export {};
