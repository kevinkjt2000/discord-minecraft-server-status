ARG APP_NAME=bowser
ARG MIX_ENV=prod

FROM elixir:1.9-alpine@sha256:9a59d8610699c0e98096eaa8c7f4a6e92382e96ec355bd784cd575e37ad1b9c4 as builder

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



FROM alpine:3.11@sha256:18a918a714d1368847b67173d120ebd110fcfae208305412f3005a61cdc7c20e as production

ARG APP_NAME
ARG MIX_ENV

RUN apk --no-cache add \
    bash \
    openssl-dev

WORKDIR /app
COPY --from=builder /app/_build/${MIX_ENV}/rel/${APP_NAME} .

CMD ["./bin/bowser", "start"]
