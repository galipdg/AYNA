# Build context: the repository root (docker-compose.yml), because the server
# validates steps, snapshots and healing proposals against schemas/step.schema.json
# (#39), schemas/snapshot.schema.json (#15) and schemas/healing-proposal.schema.json (#74).
# Build stage: compiles the server with the Maven wrapper.
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src/server
COPY server/.mvn/ .mvn/
COPY server/mvnw server/pom.xml ./
RUN ./mvnw -q -B dependency:go-offline
COPY schemas/step.schema.json schemas/snapshot.schema.json schemas/healing-proposal.schema.json /src/schemas/
COPY server/src/ src/
RUN ./mvnw -q -B package -DskipTests

# Runtime stage: only the JRE and the jar.
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/server/target/ayna-server-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
