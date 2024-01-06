FROM debian:bookworm
RUN apt-get update && apt-get -y --no-install-recommends install \
  python3 \
  python3-pyrss2gen \
  osmosis
