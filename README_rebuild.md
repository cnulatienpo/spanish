# Codex Rebuilder (Kotlin/JVM)

## Build
./gradlew shadowJar

## Run
java -jar build/libs/codex-rebuilder-all.jar --write

## Validate only
java -jar build/libs/codex-rebuilder-all.jar --check

## Strict mode
java -jar build/libs/codex-rebuilder-all.jar --strict

## Sanity
grep -R -nE '<<<<<<<|=======|>>>>>>>' content || true
