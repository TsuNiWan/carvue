import { createWriteStream, createReadStream } from 'node:fs';
import { mkdir, writeFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const version = '4.5.14';
const filename = `blender-${version}-windows-x64.zip`;
const base = 'https://download.blender.org/release/Blender4.5/';
const destination = path.join(root, 'tools', filename);
await mkdir(path.dirname(destination), { recursive: true });
const checksumResponse = await fetch(`${base}blender-${version}.sha256`);
if (!checksumResponse.ok) throw new Error(`Checksum request: ${checksumResponse.status}`);
const checksums = await checksumResponse.text();
await writeFile(path.join(root, 'tools', `blender-${version}.sha256`), checksums);
const checksumLine = checksums.split(/\r?\n/).find(line => line.trim().endsWith(filename));
if (!checksumLine) throw new Error('Official checksum entry was not found');
const expected = checksumLine.trim().split(/\s+/)[0];
let existingSize = 0;
try { existingSize = (await stat(destination)).size; } catch {}
if (existingSize !== 398661046) {
  const response = await fetch(`${base}${filename}`);
  if (!response.ok) throw new Error(`Download request: ${response.status}`);
  console.log(`Downloading ${filename}: ${response.headers.get('content-length')} bytes`);
  await pipeline(Readable.fromWeb(response.body), createWriteStream(destination));
}
const hash = createHash('sha256');
for await (const chunk of createReadStream(destination)) hash.update(chunk);
const actual = hash.digest('hex');
if (actual !== expected) throw new Error(`SHA-256 mismatch: ${actual}`);
await writeFile(path.join(root, 'tools', 'blender-installation.json'), JSON.stringify({ version, filename, source: `${base}${filename}`, checksumSource: `${base}blender-${version}.sha256`, sha256: actual, verifiedAt: new Date().toISOString() }, null, 2));
console.log(`Verified SHA-256: ${actual}`);
