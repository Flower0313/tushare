import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = resolve(frontendRoot, '..')
const pythonCandidates = process.platform === 'win32'
  ? [join(repositoryRoot, 'backend', '.venv', 'Scripts', 'python.exe'), 'python']
  : [join(repositoryRoot, 'backend', '.venv', 'bin', 'python'), 'python3', 'python']
const python = pythonCandidates.find((candidate) => !candidate.includes(repositoryRoot) || existsSync(candidate))
if (!python) throw new Error('Python interpreter not found')

run(python, [join(repositoryRoot, 'backend', 'tools', 'export_openapi.py'), '--output', join(frontendRoot, 'openapi.json')])

const generator = join(frontendRoot, 'node_modules', 'openapi-typescript', 'bin', 'cli.js')
run(process.execPath, [generator, join(frontendRoot, 'openapi.json'), '-o', join(frontendRoot, 'src', 'generated', 'api-types.ts')])

function run(command, args) {
  const result = spawnSync(command, args, { cwd: frontendRoot, stdio: 'inherit' })
  if (result.status !== 0) process.exit(result.status ?? 1)
}
