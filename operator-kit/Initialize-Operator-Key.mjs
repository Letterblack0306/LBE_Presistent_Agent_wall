#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
const home = process.env.LB_GOV_OPERATOR_HOME || path.join(os.homedir(), '.letterblack-governance');
fs.mkdirSync(home,{recursive:true});
const privPath=path.join(home,'operator-private.pem');
const pubPath=path.join(home,'operator-public.pem');
if (fs.existsSync(privPath) || fs.existsSync(pubPath)) { console.error(`Refusing to overwrite existing operator key at ${home}`); process.exit(1); }
const {privateKey,publicKey}=crypto.generateKeyPairSync('ed25519');
fs.writeFileSync(privPath,privateKey.export({type:'pkcs8',format:'pem'}),{mode:0o600});
fs.writeFileSync(pubPath,publicKey.export({type:'spki',format:'pem'}));
console.log(`Created operator keypair.\nPRIVATE: ${privPath}\nPUBLIC:  ${pubPath}\nKeep the private key outside governed workspaces and do not expose it to agents.`);
