import { copyFile } from 'node:fs/promises'

for (const name of ['LICENSE', 'ASSET_RIGHTS.md', 'THIRD_PARTY_NOTICES.md']) {
  await copyFile(name, `dist/${name}`)
}
