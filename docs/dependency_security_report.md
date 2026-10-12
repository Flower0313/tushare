# Frontend dependency security report

Assessment date: 2026-10-08.

## Finding

`npm audit` reported `GHSA-68fv-2mgg-jv7q` against `source-map-js` versions `>=1.0.0 <1.2.2` (event-loop denial of service while processing indexed source-map section offsets).

Dependency chain before remediation:

```text
vite 7.3.6
└─ postcss 8.5.28
   └─ source-map-js 1.2.1
```

## Exposure assessment

- Exposure class: **build-time/development**, not browser runtime.
- `source-map-js` is consumed through Vite/PostCSS tooling and is not shipped as an application runtime module.
- Exploitation requires the toolchain to process a malicious indexed source map. Builds normally use trusted local sources, reducing practical exposure, but the high-severity advisory still warranted remediation.

## Remediation

The existing PostCSS range (`^1.2.1`) accepts patched `source-map-js 1.2.2`. `npm audit fix --dry-run` showed one patch-level transitive change, so the lockfile was updated without an override, force flag, or major upgrade.

Final chain: `vite 7.3.6 → postcss 8.5.28 → source-map-js 1.2.2`.

Final `npm audit`: **0 vulnerabilities**. Review again on every frontend dependency change and during routine security maintenance.
