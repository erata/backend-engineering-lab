ARG DOTNET_VERSION=10.0
FROM mcr.microsoft.com/dotnet/sdk:11.0 AS build
ARG DOTNET_VERSION
WORKDIR /src
COPY implementations/aspnet-core/Lab.Api/ ./
RUN dotnet publish -c Release -f net${DOTNET_VERSION} -o /out
FROM mcr.microsoft.com/dotnet/aspnet:${DOTNET_VERSION}
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet","Lab.Api.dll"]
