# Build stage: compiles the server with the Maven wrapper.
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN ./mvnw -q -B dependency:go-offline
COPY src/ src/
RUN ./mvnw -q -B package -DskipTests

# Runtime stage: only the JRE and the jar.
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /src/target/ayna-server-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
