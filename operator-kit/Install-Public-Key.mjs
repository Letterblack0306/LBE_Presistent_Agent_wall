#!/usr/bin/env node
import fs from 'node:fs'; import path from 'node:path'; import os from 'node:os';
const workspace=path.resolve(process.argv[2]||process.cwd());
const home=process.env.LB_GOV_OPERATOR_HOME||path.join(os.homedir(),'.letterblack-governance');
const src=path.join(home,'operator-public.pem'); const dest=path.join(workspace,'.governance','operator-public.pem');
if(!fs.existsSync(src)){console.error(`Missing operator public key: ${src}`);process.exit(1);} fs.mkdirSync(path.dirname(dest),{recursive:true}); fs.copyFileSync(src,dest); console.log(`Installed operator public key to ${dest}`);
