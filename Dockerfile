ARG APP_NAME=bowser
ARG MIX_ENV=prod

FROM elixir:1.9-alpine@sha256:9b8a2e4e8249926c1d45f9030bce25fd0e6f78d02c873ad4a31ae872913e507a as builder

ARG APP_NAME
ARG COOKIE
ARG MIX_ENV

RUN apk --no-cache add \
    git

RUN mix local.hex --force && \
    mix local.rebar --force && \
    mix hex.info

WORKDIR /app
COPY mix.* ./
RUN mix do deps.get --only prod, deps.compile
COPY lib lib
COPY config config
RUN mix release



FROM alpine:3.11@sha256:3983cc12fb9dc20a009340149e382a18de6a8261b0ac0e8f5fcdf11f8dd5937e as production

ARG APP_NAME
ARG MIX_ENV

RUN apk --no-cache add \
    bash \
    openssl-dev

WORKDIR /app
COPY --from=builder /app/_build/${MIX_ENV}/rel/${APP_NAME} .

CMD ["./bin/bowser", "start"]
