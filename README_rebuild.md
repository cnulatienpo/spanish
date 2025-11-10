# Codex Rebuilder (Deno TS)

## Quickstart
```
deno run -A tools/codex_rebuilder.ts --write
```

## Verify no conflicts remain
```
grep -R -nE '<<<<<<<|=======|>>>>>>>' content || true
```

## Strict mode
```
deno run -A tools/codex_rebuilder.ts --strict
```
