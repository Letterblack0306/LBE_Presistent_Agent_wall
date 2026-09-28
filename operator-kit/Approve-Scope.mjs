#!/usr/bin/env node
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os'; import crypto from 'node:crypto';
function stable(v){if(Array.isArray(v))return v.map(stable);if(v&&typeof v==='object')return Object.keys(v).sort().reduce((o,k)=>(o[k]=stable(v[k]),o),{});return v;}
const workspace=path.resolve(process.argv[2]||process.cwd());
const operator=process.argv[3]||process.env.USER||process.env.USERNAME||'operator';
const home=process.env.LB_GOV_OPERATOR_HOME||path.join(os.homedir(),'.letterblack-governance');
const privPath=path.join(home,'operator-private.pem');
const scopePath=path.join(workspace,'.governance','task-scope.json');
const sigPath=path.join(workspace,'.governance','task-scope.sig.json');
if(!fs.existsSync(privPath)){console.error(`Missing external operator private key: ${privPath}`);process.exit(1);}if(!fs.existsSync(scopePath)){console.error(`Missing scope: ${scopePath}`);process.exit(1);}
const scope=JSON.parse(fs.readFileSync(scopePath,'utf8'));
if(scope.active!==true){console.error('Refusing to sign: scope.active must be true.');process.exit(1);}
if(scope.scopeLocked!==true){console.error('Refusing to sign: scope.scopeLocked must be true.');process.exit(1);}
const canonical=JSON.stringify(stable(scope));
const digest=crypto.createHash('sha256').update(canonical).digest('hex');
const signature=crypto.sign(null,Buffer.from(canonical),fs.readFileSync(privPath,'utf8')).toString('base64');
fs.writeFileSync(sigPath,JSON.stringify({version:1,algorithm:'Ed25519',scopeSha256:digest,signatureBase64:signature,signedAt:new Date().toISOString(),operator},null,2)+'\n');
console.log(`AUTHORIZED scope=${scope.scopeId}\nsha256=${digest}\nsignature=${sigPath}`);
