# CodexFixer (.NET 8)

## Quickstart
```
dotnet build -c Release
dotnet run --project tools/CodexFixer -- --write
```

## Verify no conflicts remain
```
grep -R -nE '<<<<<<<|=======|>>>>>>>' content || true
```

## Strict mode
```
dotnet run --project tools/CodexFixer -- --strict
```
