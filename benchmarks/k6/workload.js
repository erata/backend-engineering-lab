import http from 'k6/http';
import {check} from 'k6';
const base=__ENV.BASE_URL || 'http://localhost:8080';
const path=__ENV.LAB_PATH || '/api/products/42';
const method=__ENV.METHOD || 'GET';
export const options={scenarios:{workload:{executor:'constant-arrival-rate',rate:Number(__ENV.RATE||50),timeUnit:'1s',duration:__ENV.DURATION||'60s',preAllocatedVUs:Number(__ENV.VUS||100),maxVUs:Number(__ENV.MAX_VUS||500)}}, thresholds:{http_req_failed:['rate<0.01'],checks:['rate>0.99']},summaryTrendStats:['avg','med','p(95)','p(99)','max']};
export default function(){const res=http.request(method,base+path,null,{timeout:'10s'});check(res,{'HTTP 200':r=>r.status===200,'JSON body':r=>{try{JSON.parse(r.body);return true;}catch{return false;}}});}
